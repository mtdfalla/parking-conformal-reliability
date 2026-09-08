#!/usr/bin/env python3
"""EXP-034 — D-019 option (C): the RELATIVE-threshold allocation demonstration. Authorised by D-023.

Prespecified in `04_experiments/2026-09-05-rphase-C-PRESPECIFICATION.md`; theta's provenance is in
`04_experiments/2026-09-05-theta-LITERATURE-ANCHOR.md`, written BEFORE this file existed.

WHAT CHANGES FROM EXP-029, AND WHAT DELIBERATELY DOES NOT
---------------------------------------------------------
The dead vignette declared a facility unavailable when `capacity - occupancy < 1 SPACE`, an ABSOLUTE bar
applied across facilities of 53 to 1,549 spaces. On the healthy base that event occurred 0 times in 3,340
weekday and 0 in 2,940 weekend facility-slots (EXP-029, lesson B20). Here a facility is unavailable when
predicted occupancy reaches **theta x its own training-window capacity proxy** -- a RELATIVE rule, which
is the standard operational construct in parking guidance systems and is what makes the event occur.

**theta does NOT come from EXP-031's level sweep.** It comes from the parking-management literature:
Caicedo (2009, TR-C) records deployed PARC systems displaying "no free spaces" above **90% and 95%**
occupancy; Levy et al. (2013, Transportmetrica A) put the breakdown at **92-93%**; Millard-Ball et al.
(2014, TR-A) measure it at **85-90%**. Primary **theta = 0.90**, insensitivity band **[0.90, 0.95]**,
with 0.85 as an outside endpoint. The sweep is corroboration and is never the source.

EVERYTHING ELSE IS IMPORTED, NOT REWRITTEN (B9). The panel machinery, the RF/HistGBR fits, the gamma
selection, the ACQR stream, the TRAINING-ONLY capacity proxy, the demand model, the anchor rule, the
20 seeds and the MARGIN negative control all come from `2026-09-04-allocation-vignette.py` by import.
This file adds exactly one thing: the availability rule and the outcome definition that goes with it.

Usage:
    python 2026-09-05-relative-threshold-allocation.py --phase a   [--budget 150]
    python 2026-09-05-relative-threshold-allocation.py --phase s0
    python 2026-09-05-relative-threshold-allocation.py --phase run [--budget 150] [--seeds 20]
Resumable: units are (window, theta, seed). Re-run until it prints ALL DONE.
"""
from __future__ import annotations
import argparse, importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CONF = ROOT / "03_code" / "src" / "conformal"
sys.path.insert(0, str(CONF))
import core  # noqa: E402
_spec = importlib.util.spec_from_file_location("vign", CONF / "2026-09-04-allocation-vignette.py")
V = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V)

TAB = ROOT / "05_results" / "tables"
THETAS = (0.85, 0.90, 0.925, 0.95)      # 0.90 primary; band [0.90, 0.95]; 0.85 outside endpoint
OUT = TAB / "2026-09-05-rel-alloc-seeds.csv"
OUT_S0 = TAB / "2026-09-05-rel-alloc-section0.csv"


def log(*a): print(*a, flush=True)


def base_for(df, dyn, cap, wname):
    w = V.window_rows(df, wname)
    excl = core.low_information_facilities(w[w.facility_id.isin(dyn)])
    return [f for f in dyn if f not in excl and f in cap], excl


def run_seed_rel(seed, base, coords, cap, slots, YH, UU, YT, anchor, margin_m, theta):
    """EXP-029's demand model exactly (same rng, same requests), with a RELATIVE availability rule.

    A facility is offered iff its PREDICTED occupancy is at or below theta x its own capacity proxy.
    A BAD ASSIGNMENT is a request sent to a facility whose TRUE occupancy at that slot is at or above
    the same bar -- i.e. the driver was routed to a practically full car park.
    """
    rng = np.random.default_rng(seed)
    lat = coords.loc[base].latitude.values; lon = coords.loc[base].longitude.values
    lat0, lat1 = lat.min(), lat.max(); lon0, lon1 = lon.min(), lon.max()
    mlat, mlon = V.BBOX_MARGIN * (lat1 - lat0), V.BBOX_MARGIN * (lon1 - lon0)
    R = V.R_REQ
    si = rng.choice(len(slots), size=R, replace=True)
    hot = rng.random(R) < V.HOT
    anc = rng.choice(anchor, size=R)
    alat = coords.loc[anc].latitude.values; alon = coords.loc[anc].longitude.values
    rlat = np.where(hot, alat + rng.normal(0, V.SIG, R), rng.uniform(lat0 - mlat, lat1 + mlat, R))
    rlon = np.where(hot, alon + rng.normal(0, V.SIG, R), rng.uniform(lon0 - mlon, lon1 + mlon, R))
    D = V.haversine(rlat[:, None], rlon[:, None], lat[None, :], lon[None, :])
    order = np.argsort(D, axis=1, kind="stable")
    capv = np.array([cap[f] for f in base], dtype=float)
    bar = theta * capv[None, :]
    full_true = YT >= bar                                   # (S, F) the outcome event, on TRUTH

    out = []
    for pol, pred_occ in (("POINT", YH), ("INTERVAL", UU), ("MARGIN", YH + margin_m)):
        ok = pred_occ <= bar
        ok_req = ok[si]
        ok_ord = np.take_along_axis(ok_req, order, axis=1)
        any_ok = ok_ord.any(axis=1)
        pos = np.argmax(ok_ord, axis=1)
        fidx = order[np.arange(R), pos]
        dist = D[np.arange(R), fidx]
        bad = full_true[si, fidx]
        a = any_ok
        n_a = int(a.sum())
        out.append(dict(
            policy=pol, theta=theta, seed=seed, n_requests=R, n_assigned=n_a,
            assigned_rate=float(a.mean()), abstention_rate=float(1.0 - a.mean()),
            bad_assignment_rate_of_assigned=float(bad[a].mean()) if n_a else np.nan,
            bad_assignments_per_request=float((a & bad).mean()),
            unserved_or_bad_rate=float(((~a) | (a & bad)).mean()),
            mean_straight_line_km=float(dist[a].mean()) if n_a else np.nan,
            p90_straight_line_km=float(np.percentile(dist[a], 90)) if n_a else np.nan))
    return out


def phase_s0(df, coords, cap, dyn):
    """INPUTS ONLY. No policy is scored here; this measures whether the experiment can say anything."""
    rows = []
    for wname in V.WINDOWS:
        base, excl = base_for(df, dyn, cap, wname)
        slots, YH, UU, YT = V.build_matrices(base, wname)
        capv = np.array([cap[f] for f in base], float)
        margin_m = float(np.mean(UU - YH))
        for th in THETAS:
            bar = th * capv[None, :]
            full_true = YT >= bar
            ok_pt, ok_iv = YH <= bar, UU <= bar
            iv_only = int(((~ok_iv) & ok_pt).sum())          # withdrawn by INTERVAL, offered by POINT
            pt_only = int(((~ok_pt) & ok_iv).sum())          # must be 0: U >= yhat by construction
            rows.append(dict(
                window=wname, theta=th, n_base=len(base), n_slots=len(slots),
                n_facility_slots=int(full_true.size),
                event_slots=int(full_true.sum()),
                event_rate=float(full_true.mean()),
                facilities_with_event=int((full_true.any(axis=0)).sum()),
                point_withdraw_rate=float((~ok_pt).mean()),
                interval_withdraw_rate=float((~ok_iv).mean()),
                interval_only_withdrawn_slots=iv_only,
                point_only_withdrawn_slots=pt_only,
                margin_m=margin_m, excluded=";".join(map(str, excl))))
    d = pd.DataFrame(rows)
    d.to_csv(OUT_S0, index=False)
    log(d.to_string(index=False))
    log(f"\nwrote {OUT_S0.name}")
    log("\nB23 CHECK -- the contrast is zero BY CONSTRUCTION wherever interval_only_withdrawn_slots = 0.")
    log("B20 CHECK -- the outcome event must occur on the population that will be scored.")
    log("ALL DONE")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["a", "s0", "run"])
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--seeds", type=int, default=20)
    a = ap.parse_args()
    t0 = time.time()
    df, coords, feat, dyn = V.load()

    if a.phase == "a":
        metas = V.phase_a(df, feat, dyn, a.budget, t0)
        if metas is None:
            log("REMAINING (phase A)"); return
        log(f"[A] ALL DONE — {len(metas.dropna(subset=['cap_train']))} facilities cached")
        return

    metas = V.phase_a(df, feat, dyn, 1e9, t0)
    metas = metas.dropna(subset=["cap_train"])
    cap = dict(zip(metas.facility_id.astype(int), metas.cap_train))

    if a.phase == "s0":
        phase_s0(df, coords, cap, dyn); return

    done = set()
    if OUT.exists():
        prev = pd.read_csv(OUT)
        done = set(zip(prev.window, prev.theta.round(4), prev.seed))
    rows = []
    for wname in V.WINDOWS:
        base, excl = base_for(df, dyn, cap, wname)
        anchor, _ = V.anchors_for(df, base, cap, wname)
        slots, YH, UU, YT = V.build_matrices(base, wname)
        margin_m = float(np.mean(UU - YH))
        log(f"[B] {wname}: base n={len(base)} excluded={excl} slots={len(slots)} anchor={anchor} "
            f"margin_m={margin_m:.2f}")
        for th in THETAS:
            for seed in range(1, a.seeds + 1):
                if (wname, round(th, 4), seed) in done:
                    continue
                if time.time() - t0 > a.budget:
                    if rows: flush(rows)
                    log("REMAINING"); return
                for rec in run_seed_rel(seed, base, coords, cap, slots, YH, UU, YT,
                                        anchor, margin_m, th):
                    rec.update(window=wname, n_base=len(base), n_slots=len(slots),
                               excluded=";".join(map(str, excl)), margin_m=margin_m,
                               anchor=";".join(map(str, anchor)))
                    rows.append(rec)
                flush(rows); rows = []
    flush(rows)
    log("ALL DONE")


def flush(rows):
    if not rows:
        return
    pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)


if __name__ == "__main__":
    main()
