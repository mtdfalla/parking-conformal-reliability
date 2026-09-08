#!/usr/bin/env python3
"""
EXP-029 — R-Phase 3b task 6: the risk-aware allocation vignette, rebuilt.
Belgrade, t+15 min, 90% ACQR intervals. Supersedes EXP-015 (`2026-08-04-allocation-vignette.py`).

Prespecified in `04_experiments/2026-09-04-task6-allocation-vignette-PRESPECIFICATION.md`, written
before this script was run. Read it before changing anything here.

WHAT IS DIFFERENT FROM THE SCRIPT IT REPLACES, AND WHY
------------------------------------------------------
* Reads `belgrade_features_v2.parquet` and filters with `use_15`, so no row carries an outcome
  observed in a later split.                                                          [S01/S02/X01]
* Intervals come from `core.adaptive_conformal_stream`, not from a local copy of ACQR written
  before the C01/C02 fixes. One definition of the method in this project.                 [C01, B9]
* gamma is selected per facility by `core.select_gamma_on_calibration` on the nested cal-A/cal-B
  split, never read off the test window.                                              [EXP-019]
* CAPACITY PROXY IS COMPUTED ON THE TRAINING SPLIT ONLY. The archived script took the max over the
  full record, test window included — it read a number off the window it was scoring. The worst
  case was facility 8, whose proxy came from the stuck value its dead sensor reports inside the
  test window (65 -> 109).                                                                   [D01]
* `core.low_information_facilities` is applied to EACH SCORED WINDOW, not to the whole frame.
  Returns {8} on both windows here.                                                         [D-018]
* 20 demand seeds, not one. The fit is done ONCE at seed 42 and the seeds vary the requests only,
  so the three policies are scored on IDENTICAL requests within a seed and the per-seed difference
  is a paired quantity.                                                                      [D03]
* The demand anchor is recomputed from TRAINING data (section 3.6 of the prespecification). The
  archived anchor {8, 9, 10, 23} does not survive: 8 is excluded by D-018 and 10 is not in the v2
  dynamic set, so leaving it hardcoded would define the stress case partly by a dead sensor.
* Weekday (Mar 20-21) and weekend (Mar 18-19) afternoons are run and reported SEPARATELY.
* "detour" is gone. The per-policy quantity is a STRAIGHT-LINE distance; the contrast between two
  policies is an ADDITIONAL STRAIGHT-LINE DISTANCE. No road-network routing was ever computed. [D02]
* A third policy, MARGIN, is the negative control: a constant safety margin matched to INTERVAL's
  mean conservativeness. Without it "calibrated intervals help" cannot be separated from "any
  conservatism helps".                                                                        [B3]

Requests remain independent — no queueing, no interaction, no rerouting. This is an illustrative
decision vignette, NOT a calibrated simulator (D-010 scope), and it must keep saying so.

Usage:  python 2026-09-04-allocation-vignette.py [--budget 150] [--seeds 20]
Resumable: units are (window, seed). Re-run until it prints ALL DONE.
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
import core                                                    # noqa: E402

PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"
CACHE = Path.home() / ".vign_cache_2026_09_04"                 # outside the mount; regenerable

SEED_FIT = 42          # archived                      [B6]
DYN = 5.0              # archived dynamic-facility threshold, on the TRAINING window   [I05]
HZ, HMIN, HSTEPS = "y_t+15min", 15, 3
ALPHA = 0.10
SAFETY = 1             # archived safety margin, in spaces
R_REQ = 600            # archived requests per seed
HOT = 0.65             # archived hot/uniform mixture
SIG = 0.0035           # archived ~350 m concentration
BBOX_MARGIN = 0.15     # archived
ANCHOR_K = 4           # archived anchor cardinality; the MEMBERS are recomputed, the COUNT is not
WINDOWS = {"weekday": (20, 21), "weekend": (18, 19)}           # March 2017 test split
HOURS = (12, 19)       # archived afternoon window, [12:00, 19:00)

OUT = TAB / "2026-09-04-vignette-seeds.csv"
OUT_ANCH = TAB / "2026-09-04-vignette-anchors.csv"
OUT_CAP = TAB / "2026-09-04-vignette-capacity-proxy.csv"


def log(*a):
    print(*a, flush=True)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------------------------------------------
# inputs
# ------------------------------------------------------------------------------------------------
def load():
    df = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    df["ts"] = pd.to_datetime(df.timestamp)
    df = df[df[f"use_{HMIN}"]]
    coords = pd.read_parquet(PROC / "facility_coords.parquet").set_index("facility_id")
    feat = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    tr = df[df.split == "train"]
    ds = tr.groupby("facility_id").occupancy.std()
    dyn = sorted(set(ds[ds >= DYN].index) & set(coords.index))
    return df, coords, feat, dyn


def window_rows(df, wname):
    days = WINDOWS[wname]
    te = df[df.split == "test"]
    return te[te.ts.dt.day.isin(days) & (te.ts.dt.hour >= HOURS[0]) & (te.ts.dt.hour < HOURS[1])]


# ------------------------------------------------------------------------------------------------
# phase A — fit each facility once, cache its test-window panel
# ------------------------------------------------------------------------------------------------
def fit_facility(df, feat, fid):
    g = df[df.facility_id == fid].sort_values("ts").dropna(subset=["occupancy"] + feat + [HZ])
    tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
    if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
        return None, None
    occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
    d_tr = tr[HZ].values - occ_tr
    y_ca, y_te = ca[HZ].values, te[HZ].values

    rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                               random_state=SEED_FIT).fit(tr[feat].values, d_tr)
    yhat_te = occ_te + rf.predict(te[feat].values)

    glo = HistGradientBoostingRegressor(loss="quantile", quantile=ALPHA / 2, max_iter=100,
                                        random_state=SEED_FIT).fit(tr[feat].values, d_tr)
    ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1 - ALPHA / 2, max_iter=100,
                                        random_state=SEED_FIT).fit(tr[feat].values, d_tr)
    qlo_ca = occ_ca + glo.predict(ca[feat].values); qhi_ca = occ_ca + ghi.predict(ca[feat].values)
    qlo_te = occ_te + glo.predict(te[feat].values); qhi_te = occ_te + ghi.predict(te[feat].values)
    qlo_ca, qhi_ca, _ = core.repair_quantile_crossing(qlo_ca, qhi_ca)
    qlo_te, qhi_te, _ = core.repair_quantile_crossing(qlo_te, qhi_te)
    E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)

    gam, _ = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, ALPHA, HSTEPS)
    lo, hi = core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, ALPHA, HSTEPS, gamma=gam)

    panel = pd.DataFrame({"ts": te.ts.values, "yhat": yhat_te, "U": hi, "y_true": y_te})
    meta = dict(facility_id=fid, gamma=float(gam),
                cap_train=float(tr.occupancy.max()),          # TRAINING WINDOW ONLY        [D01]
                cap_fullrecord=float(g.occupancy.max()),      # published for comparison
                n_train=len(tr), n_cal=len(ca), n_test=len(te))
    return panel, meta


def phase_a(df, feat, dyn, budget, t0):
    CACHE.mkdir(exist_ok=True)
    metas = []
    for fid in dyn:
        pf, mf = CACHE / f"panel_{fid}.parquet", CACHE / f"meta_{fid}.csv"
        if pf.exists() and mf.exists():
            metas.append(pd.read_csv(mf)); continue
        if time.time() - t0 > budget:
            log("[A] budget hit; re-run to continue"); return None
        panel, meta = fit_facility(df, feat, fid)
        if panel is None:
            pd.DataFrame([dict(facility_id=fid, gamma=np.nan, cap_train=np.nan,
                               cap_fullrecord=np.nan, n_train=0, n_cal=0, n_test=0)]).to_csv(mf, index=False)
            pd.DataFrame(columns=["ts", "yhat", "U", "y_true"]).to_parquet(pf)
            log(f"[A] fac {fid}: too few rows — SKIPPED marker written")
            metas.append(pd.read_csv(mf)); continue
        panel.to_parquet(pf); pd.DataFrame([meta]).to_csv(mf, index=False)
        metas.append(pd.DataFrame([meta]))
        log(f"[A] fac {fid} fitted  gamma={meta['gamma']:.3f}  cap_train={meta['cap_train']:.1f}"
            f"  cap_full={meta['cap_fullrecord']:.1f}  ({time.time()-t0:.0f}s)")
    return pd.concat(metas, ignore_index=True)


# ------------------------------------------------------------------------------------------------
# phase B — the three policies, per window, per demand seed
# ------------------------------------------------------------------------------------------------
def anchors_for(df, base, cap, wname):
    """Top-K facilities by training-window afternoon mean occupancy / training capacity proxy,
    on training days of the SAME DAY TYPE as the window being scored. Training inputs only."""
    tr = df[df.split == "train"]
    want_weekend = 1 if wname == "weekend" else 0
    sub = tr[(tr.is_weekend.astype(int) == want_weekend) &
             (tr.ts.dt.hour >= HOURS[0]) & (tr.ts.dt.hour < HOURS[1]) &
             (tr.facility_id.isin(base))]
    r = (sub.groupby("facility_id").occupancy.mean() / pd.Series(cap)).dropna().sort_values(ascending=False)
    return list(r.index[:ANCHOR_K]), r


def build_matrices(base, wname):
    panels = {f: pd.read_parquet(CACHE / f"panel_{f}.parquet").set_index("ts") for f in base}
    days = WINDOWS[wname]
    common = None
    for f in base:
        idx = panels[f].index
        sel = idx[(idx.day.isin(days)) & (idx.hour >= HOURS[0]) & (idx.hour < HOURS[1])]
        common = sel if common is None else common.intersection(sel)
    slots = common.sort_values()
    YH = np.column_stack([panels[f].loc[slots, "yhat"].values for f in base])
    UU = np.column_stack([panels[f].loc[slots, "U"].values for f in base])
    YT = np.column_stack([panels[f].loc[slots, "y_true"].values for f in base])
    return slots, YH, UU, YT


def run_seed(seed, base, coords, cap, slots, YH, UU, YT, anchor, margin_m):
    rng = np.random.default_rng(seed)
    lat = coords.loc[base].latitude.values; lon = coords.loc[base].longitude.values
    lat0, lat1 = lat.min(), lat.max(); lon0, lon1 = lon.min(), lon.max()
    mlat, mlon = BBOX_MARGIN * (lat1 - lat0), BBOX_MARGIN * (lon1 - lon0)

    si = rng.choice(len(slots), size=R_REQ, replace=True)
    hot = rng.random(R_REQ) < HOT
    anc = rng.choice(anchor, size=R_REQ)
    alat = coords.loc[anc].latitude.values; alon = coords.loc[anc].longitude.values
    rlat = np.where(hot, alat + rng.normal(0, SIG, R_REQ), rng.uniform(lat0 - mlat, lat1 + mlat, R_REQ))
    rlon = np.where(hot, alon + rng.normal(0, SIG, R_REQ), rng.uniform(lon0 - mlon, lon1 + mlon, R_REQ))

    D = haversine(rlat[:, None], rlon[:, None], lat[None, :], lon[None, :])   # (R, F)
    order = np.argsort(D, axis=1, kind="stable")
    capv = np.array([cap[f] for f in base], dtype=float)
    free_true = capv[None, :] - YT

    out = []
    for pol, pred_free in (("POINT",    capv[None, :] - YH),
                           ("INTERVAL", capv[None, :] - UU),
                           ("MARGIN",   capv[None, :] - (YH + margin_m))):
        ok = pred_free >= SAFETY                        # (S, F)
        ok_req = ok[si]                                 # (R, F)
        ok_ord = np.take_along_axis(ok_req, order, axis=1)
        any_ok = ok_ord.any(axis=1)
        pos = np.argmax(ok_ord, axis=1)
        fidx = order[np.arange(R_REQ), pos]
        dist = D[np.arange(R_REQ), fidx]
        overflow = free_true[si, fidx] < SAFETY

        a = any_ok
        n_a = int(a.sum())
        out.append(dict(
            policy=pol, seed=seed, n_requests=R_REQ, n_assigned=n_a,
            assigned_rate=float(a.mean()),
            overflow_rate=float(overflow[a].mean()) if n_a else np.nan,
            unserved_or_overflow_rate=float(((~a) | (a & overflow)).mean()),
            mean_straight_line_km=float(dist[a].mean()) if n_a else np.nan,
            p90_straight_line_km=float(np.percentile(dist[a], 90)) if n_a else np.nan,
        ))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--seeds", type=int, default=20)
    args = ap.parse_args()
    t0 = time.time()

    df, coords, feat, dyn = load()
    log(f"[in] dynamic & coord-matched facilities: {dyn} (n={len(dyn)})")

    metas = phase_a(df, feat, dyn, args.budget, t0)
    if metas is None:
        log("REMAINING (phase A)"); return
    metas = metas.dropna(subset=["cap_train"])
    cap = dict(zip(metas.facility_id.astype(int), metas.cap_train))
    metas.to_csv(OUT_CAP, index=False)
    log(f"[A] ALL FITTED — {len(cap)} facilities, capacity proxy written to {OUT_CAP.name}")

    done = set()
    if OUT.exists():
        prev = pd.read_csv(OUT)
        done = set(zip(prev.window, prev.seed))
    rows = []
    anch_rows = []

    for wname in WINDOWS:
        w = window_rows(df, wname)
        excl = core.low_information_facilities(w[w.facility_id.isin(dyn)])
        base = [f for f in dyn if f not in excl and f in cap]
        nd = w[w.facility_id.isin(dyn)].groupby("facility_id").occupancy.nunique().sort_values()
        anchor, ratios = anchors_for(df, base, cap, wname)
        slots, YH, UU, YT = build_matrices(base, wname)
        margin_m = float(np.mean(UU - YH))
        log(f"[B] {wname}: base={base} (n={len(base)}, excluded={excl}) slots={len(slots)} "
            f"anchor={anchor} margin_m={margin_m:.2f}")
        for f, r in ratios.items():
            anch_rows.append(dict(window=wname, facility_id=int(f), occ_over_cap_train=float(r),
                                  selected=int(f in anchor)))
        for seed in range(1, args.seeds + 1):
            if (wname, seed) in done:
                continue
            if time.time() - t0 > args.budget:
                log("[B] budget hit; saving and exiting")
                if rows: flush(rows)
                log("REMAINING"); return
            for rec in run_seed(seed, base, coords, cap, slots, YH, UU, YT, anchor, margin_m):
                rec.update(window=wname, n_base=len(base), n_slots=len(slots),
                           excluded=";".join(map(str, excl)), margin_m=margin_m,
                           anchor=";".join(map(str, anchor)),
                           distinct_min=int(nd.iloc[0]), distinct_next=int(nd.iloc[1]))
                rows.append(rec)
            flush(rows); rows = []
            log(f"[B] {wname} seed {seed} done ({time.time()-t0:.0f}s)")

    pd.DataFrame(anch_rows).to_csv(OUT_ANCH, index=False)
    log("ALL DONE")


def flush(rows):
    if not rows:
        return
    d = pd.DataFrame(rows)
    d.to_csv(OUT, mode="a", header=not OUT.exists(), index=False)


if __name__ == "__main__":
    main()
