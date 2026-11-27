#!/usr/bin/env python3
"""EXP-045 arm A2 successor (findings T009, T010, T011, T053), built 2026-11-25 from
`2026-09-05-relative-threshold-allocation.py` by exact replacement (`tools/make_alloc_a2_ladder.py`).

What changed and why.
* Imports `2026-11-25-allocation-vignette.py` (same fits, plus three cached upper bounds).
* T009: three policies are scored on the identical panel and the identical seeded requests, after the
  shipped three: CQR-RAW (repaired HGB 95% upper quantile, no conformalization), SPLIT-CQR (that bound
  plus the split calibration quantile of E_cal) and RF-SPLITCP (RF point forecast plus the split-CP
  quantile). `run_seed_rel(..., extra=None)` scores exactly the shipped three, so the old call is unchanged.
* T011: each per-seed row carries `upper_miss_assigned`, P(Y > policy bound) over the assigned requests.
  Section 0 also carries, per policy, the withdrawal rate, P(Y > bound) on all facility-slots and on
  offered facility-slots, and the event rate on offered facility-slots.
* T053: the weekend window is also run on each of its two days separately (column `day`, "all" for the
  full window). MARGIN keeps the full-window margin on the day subsets.
* T010: `--phase cap` perturbs each facility's capacity by an independent factor U(1 - s, 1 + s),
  s in {0.05, 0.10}, 40 draws, seed 20261125, weekend, theta 0.90. The same perturbed capacity sets
  the offer bar and the outcome bar. Anchors, margin and requests stay those of the proxy. Draw -1 with
  every factor 1 is the unperturbed control.
* Outputs carry 2026-11-25 names. No shipped table is read for writing or overwritten.

Original header follows.

EXP-034 — D-019 option (C): the RELATIVE-threshold allocation demonstration. Authorised by D-023.

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
_spec = importlib.util.spec_from_file_location("vign", CONF / "2026-11-25-allocation-vignette.py")
V = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V)

TAB = ROOT / "05_results" / "tables"
THETAS = (0.85, 0.90, 0.925, 0.95)      # 0.90 primary; band [0.90, 0.95]; 0.85 outside endpoint
OUT = TAB / "2026-11-25-exp045-allocation-seeds.csv"
OUT_S0 = TAB / "2026-11-25-exp045-rel-alloc-section0.csv"


def log(*a): print(*a, flush=True)


def base_for(df, dyn, cap, wname):
    w = V.window_rows(df, wname)
    excl = core.low_information_facilities(w[w.facility_id.isin(dyn)])
    return [f for f in dyn if f not in excl and f in cap], excl


def run_seed_rel(seed, base, coords, cap, slots, YH, UU, YT, anchor, margin_m, theta, extra=None):
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
    pols = [("POINT", YH), ("INTERVAL", UU), ("MARGIN", YH + margin_m)]
    if extra is not None:                                   # EXP-045 A2: the T009 ladder
        pols += [(k, extra[k]) for k in EXTRA_POLICIES]
    for pol, pred_occ in pols:
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
            p90_straight_line_km=float(np.percentile(dist[a], 90)) if n_a else np.nan,
            upper_miss_assigned=float((YT[si, fidx] > pred_occ[si, fidx])[a].mean())
            if n_a else np.nan))                            # EXP-045 A2: T011
    return out


def phase_s0(df, coords, cap, dyn):
    """INPUTS ONLY. No policy is scored here; this measures whether the experiment can say anything."""
    rows = []
    for wname in V.WINDOWS:
        base, excl = base_for(df, dyn, cap, wname)
        slots, YH, UU, YT = V.build_matrices(base, wname)
        capv = np.array([cap[f] for f in base], float)
        margin_m = float(np.mean(UU - YH))
        B = policy_bounds(YH, UU, margin_m, extra_mats(base, slots))   # EXP-045 A2: T011
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
                margin_m=margin_m, excluded=";".join(map(str, excl)),
                **slot_diag(B, YT, bar, full_true)))
    d = pd.DataFrame(rows)
    d.to_csv(OUT_S0, index=False)
    log(d.to_string(index=False))
    log(f"\nwrote {OUT_S0.name}")
    log("\nB23 CHECK -- the contrast is zero BY CONSTRUCTION wherever interval_only_withdrawn_slots = 0.")
    log("B20 CHECK -- the outcome event must occur on the population that will be scored.")
    log("ALL DONE")


# ------------------------------------------------------------------------------------------------
# EXP-045 arm A2 additions (T009, T010, T011, T053)
# ------------------------------------------------------------------------------------------------
EXTRA_POLICIES = {"CQR-RAW": "QHI_RAW", "SPLIT-CQR": "QHI_SCQR", "RF-SPLITCP": "YH_SPLITCP"}
POLICIES = ("POINT", "INTERVAL", "MARGIN") + tuple(EXTRA_POLICIES)
SHIPPED_POLICIES = ("POINT", "INTERVAL", "MARGIN")
DAY_SPLIT_WINDOWS = ("weekend",)            # T053: the two weekend days separately
OUT_CAPX = TAB / "2026-11-25-exp045-allocation-capacity.csv"
CAP_THETA, CAP_SPREADS, CAP_DRAWS, CAP_SEED = 0.90, (0.05, 0.10), 40, 20261125
CAP_WINDOW = "weekend"


def colname(p):
    return p.replace("-", "_")


def extra_mats(base, slots):
    mats = V.build_extra(base, slots, list(EXTRA_POLICIES.values()))
    return dict(zip(EXTRA_POLICIES, mats))


def policy_bounds(YH, UU, margin_m, X):
    """The occupancy each policy commits on, in POLICIES order."""
    B = {"POINT": YH, "INTERVAL": UU, "MARGIN": YH + margin_m}
    B.update({k: X[k] for k in EXTRA_POLICIES})
    return B


def day_scopes(wname, slots):
    """("all", every slot) first, then one scope per calendar day for the day-split windows."""
    out = [("all", np.ones(len(slots), dtype=bool))]
    if wname in DAY_SPLIT_WINDOWS:
        days = np.asarray(slots.strftime("%Y-%m-%d"))
        out += [(d, days == d) for d in sorted(set(days))]
    return out


def slot_diag(B, YT, bar, full_true):
    """T011 at the facility-slot level: no requests involved."""
    r = {}
    for p, U in B.items():
        ok = U <= bar
        c = colname(p)
        r[f"withdraw_rate_{c}"] = float((~ok).mean())
        r[f"upper_miss_all_{c}"] = float((YT > U).mean())
        r[f"upper_miss_offered_{c}"] = float((YT[ok] > U[ok]).mean()) if ok.any() else np.nan
        r[f"event_rate_offered_{c}"] = float(full_true[ok].mean()) if ok.any() else np.nan
        r[f"offered_slots_{c}"] = int(ok.sum())
    return r


def cell_metrics(g, n_req=None):
    """Long metric rows for one cell from its per-seed rows (all policies, one row per policy x seed).

    Single-policy rows have comparator "". Paired rows compare `policy` with `comparator` on the same
    requests: d = comparator minus policy, per 600 requests, so d > 0 means `policy` makes fewer bad
    assignments; `extra_m` is policy minus comparator straight-line distance in metres.
    """
    n_req = V.R_REQ if n_req is None else n_req
    P = g.pivot(index="seed", columns="policy")
    bad = P["bad_assignments_per_request"] * n_req
    km, ab, um = P["mean_straight_line_km"], P["abstention_rate"], P["upper_miss_assigned"]
    n = len(bad)
    pols = [p for p in POLICIES if p in bad.columns]
    out = []

    def put(p, c, m, v, unit):
        out.append(dict(policy=p, comparator=c, metric=m, value=float(v), n_seeds=n, unit=unit))

    for p in pols:
        put(p, "", "bad_per600_mean", bad[p].mean(), "per 600 requests")
        put(p, "", "bad_per600_sd", bad[p].std(ddof=1), "per 600 requests")
        put(p, "", "abstention_mean", ab[p].mean(), "share of requests")
        put(p, "", "km_mean", km[p].mean(), "km")
        put(p, "", "upper_miss_assigned_mean", um[p].mean(), "share of assigned requests")
    d_ref = (bad["POINT"] - bad["INTERVAL"]).mean()
    pairs = [(p, "POINT") for p in pols if p != "POINT"] + \
            [("INTERVAL", p) for p in pols if p not in ("POINT", "INTERVAL")] + \
            [("SPLIT-CQR", "CQR-RAW")]
    for p, c in pairs:
        if p not in pols or c not in pols:
            continue
        d = bad[c] - bad[p]
        put(p, c, "d_bad_per600_mean", d.mean(), "per 600 requests, comparator minus policy")
        put(p, c, "d_bad_per600_sd", d.std(ddof=1), "per 600 requests")
        put(p, c, "d_bad_per600_se", d.std(ddof=1) / np.sqrt(n), "per 600 requests, paired Monte Carlo SE")
        put(p, c, "d_bad_per600_seed_min", d.min(), "per 600 requests")
        put(p, c, "d_bad_per600_seed_max", d.max(), "per 600 requests")
        put(p, c, "seeds_policy_better", int((d > 0).sum()), "seeds")
        put(p, c, "seeds_tied", int((d == 0).sum()), "seeds")
        cm = bad[c].mean()
        put(p, c, "rel_reduction", d.mean() / cm if cm else np.nan, "share of comparator")
        put(p, c, "extra_m", (1000 * (km[p] - km[c])).mean(), "metres, policy minus comparator")
        if c == "POINT" and p != "INTERVAL":
            put(p, c, "share_of_point_to_interval_reduction", d.mean() / d_ref if d_ref else np.nan,
                "share of POINT minus INTERVAL")
    return out


def frames_identical(ref, new, label):
    """Cell-by-cell comparison of two frames read with float_precision="round_trip".

    Returns (n_exact_mismatch, n_last_ulp_only, n_cells). Strings and integers must be equal.
    A float pair that differs by at most one spacing of the larger magnitude is counted separately
    as a CSV storage-precision difference, not as a mismatch.
    """
    if list(ref.columns) != list(new.columns) or len(ref) != len(new):
        print(f"[{label}] SHAPE OR COLUMNS DIFFER: {ref.shape} {new.shape}")
        return 10 ** 9, 0, 0
    bad = ulp = cells = 0
    for c in ref.columns:
        a, b = ref[c].to_numpy(), new[c].to_numpy()
        cells += len(a)
        if np.issubdtype(a.dtype, np.floating) or np.issubdtype(b.dtype, np.floating):
            a = a.astype(float); b = b.astype(float)
            same = (a == b) | (np.isnan(a) & np.isnan(b))
            near = ~same & (np.abs(a - b) <= np.spacing(np.maximum(np.abs(a), np.abs(b))))
            nb = int((~same & ~near).sum()); nu = int(near.sum())
        else:
            nb = int((a.astype(str) != b.astype(str)).sum()); nu = 0
        if nb or nu:
            print(f"[{label}] column {c}: {nb} mismatches, {nu} last-ulp differences")
        bad += nb; ulp += nu
    return bad, ulp, cells


def phase_cap(df, coords, cap0, dyn, n_seeds):
    """T010: facility-specific capacity perturbation, weekend, theta 0.90."""
    w, th = CAP_WINDOW, CAP_THETA
    base, excl = base_for(df, dyn, cap0, w)
    anchor, _ = V.anchors_for(df, base, cap0, w)
    slots, YH, UU, YT = V.build_matrices(base, w)
    X = extra_mats(base, slots)
    margin_m = float(np.mean(UU - YH))
    plan = [(0.0, -1, np.ones(len(base)))]
    for s in CAP_SPREADS:
        rng = np.random.default_rng(CAP_SEED)
        for d in range(CAP_DRAWS):
            plan.append((s, d, rng.uniform(1 - s, 1 + s, len(base))))
    rows = []
    for s, d, f in plan:
        cap = {fid: cap0[fid] * fi for fid, fi in zip(base, f)}
        recs = []
        for seed in range(1, n_seeds + 1):
            recs += run_seed_rel(seed, base, coords, cap, slots, YH, UU, YT, anchor, margin_m, th, extra=X)
        for r in cell_metrics(pd.DataFrame(recs)):
            r.update(window=w, theta=th, spread=s, draw=d, factor_min=float(f.min()),
                     factor_max=float(f.max()), n_base=len(base), n_slots=len(slots))
            rows.append(r)
    cols = ["window", "theta", "spread", "draw", "factor_min", "factor_max", "policy", "comparator",
            "metric", "value", "n_seeds", "unit", "n_base", "n_slots"]
    out = pd.DataFrame(rows)[cols]
    if OUT_CAPX.exists() and "--overwrite" not in sys.argv[1:]:
        raise SystemExit(f"{OUT_CAPX.name} exists, refusing to overwrite")
    out.to_csv(OUT_CAPX, index=False)
    log(f"wrote {OUT_CAPX.name} ({len(out)} rows)")
    log("ALL DONE")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["a", "s0", "run", "cap"])
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--overwrite", action="store_true", help="phase cap: replace an existing table (run_all.sh)")
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

    if a.phase == "cap":
        phase_cap(df, coords, cap, dyn, a.seeds); return

    done = set()
    if OUT.exists():
        prev = pd.read_csv(OUT)
        done = set(zip(prev.window, prev.day, prev.theta.round(4), prev.seed))
    rows = []
    for wname in V.WINDOWS:
        base, excl = base_for(df, dyn, cap, wname)
        anchor, _ = V.anchors_for(df, base, cap, wname)
        slots, YH, UU, YT = V.build_matrices(base, wname)
        X = extra_mats(base, slots)
        margin_m = float(np.mean(UU - YH))
        log(f"[B] {wname}: base n={len(base)} excluded={excl} slots={len(slots)} anchor={anchor} "
            f"margin_m={margin_m:.2f}")
        for day, keep in day_scopes(wname, slots):
            sl = slots[keep]
            Xd = {k: v[keep] for k, v in X.items()}
            for th in THETAS:
                for seed in range(1, a.seeds + 1):
                    if (wname, day, round(th, 4), seed) in done:
                        continue
                    if time.time() - t0 > a.budget:
                        if rows: flush(rows)
                        log("REMAINING"); return
                    for rec in run_seed_rel(seed, base, coords, cap, sl, YH[keep], UU[keep], YT[keep],
                                            anchor, margin_m, th, extra=Xd):
                        rec.update(window=wname, n_base=len(base), n_slots=len(sl),
                                   excluded=";".join(map(str, excl)), margin_m=margin_m,
                                   anchor=";".join(map(str, anchor)), day=day)
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
