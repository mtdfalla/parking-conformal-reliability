#!/usr/bin/env python3
"""
Time-of-day conditional coverage on the shared conformal core — Belgrade, t+15 min, 90%.
R-Phase 3b task 2 (D-014). Closes audit issues C05 and I03. Logged as EXP-021.

WHY THIS SCRIPT EXISTS
----------------------
Table 4 of the manuscript came from `run_cond_trust_corrected.py`, which has two defects:

* **C05** — line 29, `st = {nm: {"a": a, "sc": list(resid)} for nm,_,_ in BUCK}`: every time-of-day
  bucket was initialised from the SAME global residual pool. The adaptive *state* was per bucket but the
  score *pool* was not, so describing the method as "group-conditional (Mondrian-style)" overstated what
  was implemented. Here each facility x bucket state starts from THAT BUCKET'S OWN calibration scores,
  with a shrinkage fallback (own scores UNION the global pool) for buckets holding fewer than
  `--min-group` own scores. Every fallback is counted and reported.
* **I03** — line 65 aggregates over all facilities before reporting bucket coverage; the per-facility
  record does not even retain `fid`. The paper's own thesis is that pooling hides facility-level failure,
  so the pooled Table 4 contradicted the argument it was supporting. This script reports the full
  **facility x bucket** distribution and the worst facility-bucket, and keeps the pooled view only as a
  secondary row so the before/after delta is directly readable.

Also corrected in passing: the retired ToD-ACI let each bucket's pool grow without bound
(`pool = np.asarray(s["sc"])`, no window) while global ACI applied a window -- an inconsistency between
two methods being compared in the same table. `core.grouped_adaptive_conformal_stream` applies a
per-group window, defaulting to that group's own initial pool size.

PROTOCOL
--------
* `belgrade_features_v2.parquet` filtered by `use_15` [S01]; every primitive from `core.py`
  (direct k-th order statistic [C01], projected state [C02], delayed release queue [C06]).
* gamma is selected per facility by `core.select_gamma_on_calibration` on the nested cal-A/cal-B split
  and shared by global ACI and ToD-ACI. gamma is deliberately NOT selected per bucket: cal-B holds ~380
  rows per facility, so a per-bucket selection would run on ~76 rows and resolve differences far smaller
  than its own sampling noise (see the EXP-020 addendum on selection noise). The step size is a control
  loop gain, not a per-bucket calibration quantity; the bucket-specific part is the pool and the state.
* Buckets are the prespecified ones: night 0-5, am_rush 6-9, midday 10-15, pm_rush 16-19, evening 20-23.
* Cells are FLAGGED on a minimum sample rule (`--min-cell`), never silently dropped.

Usage:  python 2026-09-03-tod-conditional.py [--budget 150] [--min-group 50] [--min-cell 30]
Resumable: re-run until it prints ALL DONE. Facilities yielding nothing get a SKIPPED-* marker row.
Output: 05_results/tables/2026-09-03-tod-facility-bucket.csv   (the I03 deliverable; resumable unit)
        05_results/tables/2026-09-03-tod-summary.csv           (written when ALL DONE)
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; DYN = 5.0
HZ = "y_t+15min"; HMIN = 15; HSTEPS = 3; LEVEL = 0.90; ALPHA = 1 - LEVEL
BUCKETS = [("night", 0, 5), ("am_rush", 6, 9), ("midday", 10, 15),
           ("pm_rush", 16, 19), ("evening", 20, 23)]
ORDER = [b[0] for b in BUCKETS]

FB = TAB/"2026-09-03-tod-facility-bucket.csv"
SUM = TAB/"2026-09-03-tod-summary.csv"


def log(m): print(f"[tod] {m}", flush=True)


def bucket_of(hour: int) -> str:
    for nm, a, b in BUCKETS:
        if a <= hour <= b:
            return nm
    return "night"


def write_summary(fb: pd.DataFrame, min_cell: int) -> None:
    d = fb[fb.dynamic & (fb.method != "SKIPPED-thin")].dropna(subset=["PICP"]).copy()
    rep = d[d.n_cell >= min_cell]
    out = []
    for meth in ["split-CP", "Mondrian-split-CP", "ACI", "ToD-ACI"]:
        m = rep[rep.method == meth]
        if m.empty:
            continue
        # pooled-by-bucket (the retired Table 4 view), weighted by cell size
        for bk in ORDER:
            b = m[m.bucket == bk]
            if b.empty:
                continue
            out.append(dict(method=meth, scope="bucket(pooled over facilities)", bucket=bk,
                            PICP=round(float(np.average(b.PICP, weights=b.n_cell)), 4),
                            MPIW=round(float(np.average(b.MPIW, weights=b.n_cell)), 2),
                            n_cells=len(b), n_obs=int(b.n_cell.sum()),
                            worst_facility=np.nan, worst_bucket=np.nan))
        # the I03 deliverable: the facility x bucket distribution and its worst cell
        w = m.loc[m.PICP.idxmin()]
        out.append(dict(method=meth, scope="facility x bucket", bucket="(all)",
                        PICP=round(float(m.PICP.mean()), 4), MPIW=round(float(m.MPIW.mean()), 2),
                        n_cells=len(m), n_obs=int(m.n_cell.sum()),
                        worst_facility=int(w.facility_id), worst_bucket=w.bucket))
        out.append(dict(method=meth, scope="facility x bucket WORST cell", bucket=w.bucket,
                        PICP=round(float(w.PICP), 4), MPIW=round(float(w.MPIW), 2),
                        n_cells=1, n_obs=int(w.n_cell),
                        worst_facility=int(w.facility_id), worst_bucket=w.bucket))
        out.append(dict(method=meth, scope="facility x bucket SPREAD", bucket="(all)",
                        PICP=round(float(m.PICP.std(ddof=0)), 4),
                        MPIW=round(float(m.PICP.max() - m.PICP.min()), 4),
                        n_cells=len(m), n_obs=int(m.n_cell.sum()),
                        worst_facility=np.nan, worst_bucket=np.nan))
    s = pd.DataFrame(out)
    s.to_csv(SUM, index=False)
    log(f"wrote {SUM.name}  (PICP column on the SPREAD rows is the sd; MPIW column is the range)")
    nfb = fb[fb.fell_back == True]
    log(f"sparse-bucket fallbacks: {len(nfb.groupby(['facility_id','bucket']))} facility-bucket cells "
        f"of {len(fb.groupby(['facility_id','bucket']))}")
    below = d[d.n_cell < min_cell]
    log(f"cells below the min-cell rule ({min_cell}): {len(below)} — flagged, not dropped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--min-group", type=int, default=50,
                    help="own calibration scores below which a bucket uses the shrinkage fallback")
    ap.add_argument("--min-cell", type=int, default=30,
                    help="test rows below which a facility-bucket cell is flagged as thin")
    args = ap.parse_args()

    df = pd.read_parquet(PROC/"belgrade_features_v2.parquet")
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    all_fac = sorted(sd.index)
    dyn_flag = {f: bool(sd[f] >= DYN) for f in all_fac}

    done = set(pd.read_csv(FB).facility_id.unique()) if FB.exists() else set()
    todo = [f for f in all_fac if f not in done]
    log(f"Belgrade {HZ} @{LEVEL:.0%} (h={HSTEPS}), min_group={args.min_group}: "
        f"{len(done)} done, {len(todo)} to do ({sum(dyn_flag.values())} of {len(all_fac)} dynamic)")

    rows = []; t0 = time.time()
    for fid in todo:
        if time.time() - t0 > args.budget:
            log("budget hit; saving and exiting"); break
        g = df[df.facility_id == fid].sort_values("timestamp")
        if f"use_{HMIN}" in g.columns:
            g = g[g[f"use_{HMIN}"]]
        g = g.dropna(subset=["occupancy"] + FEAT + [HZ])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
            log(f"  fac {fid}: too few rows — skipped")
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], bucket="(none)",
                             method="SKIPPED-thin", PICP=np.nan, MPIW=np.nan, n_cell=0,
                             n_own=np.nan, n_init=np.nan, fell_back=np.nan, gamma=np.nan,
                             degenerate=np.nan))
            continue

        occ_ca, occ_te = ca.occupancy.values, te.occupancy.values
        rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                                   random_state=SEED).fit(tr[FEAT].values,
                                                          tr[HZ].values - tr.occupancy.values)
        yhat_ca = occ_ca + rf.predict(ca[FEAT].values)
        yhat_te = occ_te + rf.predict(te[FEAT].values)
        y_ca, y_te = ca[HZ].values, te[HZ].values
        resid = np.abs(y_ca - yhat_ca)
        degenerate = bool(np.max(resid) < 1e-9)

        b_ca = np.array([bucket_of(h) for h in pd.to_datetime(ca.timestamp.values).hour])
        b_te = np.array([bucket_of(h) for h in pd.to_datetime(te.timestamp.values).hour])
        cal_by_bucket = {bk: resid[b_ca == bk] for bk in ORDER}

        gam, _ = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca, ALPHA, HSTEPS)

        # --- the four methods ------------------------------------------------------------------
        s_lo, s_hi = core.split_conformal_interval(resid, yhat_te, ALPHA)

        q_glob = core.conformal_quantile(resid, ALPHA)
        q_bk = {}
        for bk in ORDER:
            own = cal_by_bucket[bk]
            q_bk[bk] = (core.conformal_quantile(own, ALPHA) if len(own) >= args.min_group
                        else core.conformal_quantile(np.concatenate([own, resid]), ALPHA)
                        if len(own) else q_glob)
        qm = np.array([q_bk[b] for b in b_te])
        m_lo, m_hi = np.maximum(yhat_te - qm, 0.0), yhat_te + qm

        a_lo, a_hi = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, ALPHA,
                                                    HSTEPS, gamma=gam)
        t_lo, t_hi, tdiag = core.grouped_adaptive_conformal_stream(
            cal_by_bucket, b_te, yhat_te, yhat_te, y_te, ALPHA, HSTEPS, gamma=gam,
            global_pool=resid, min_group=args.min_group, return_state=True)
        ginfo = tdiag["group_init"]

        for meth, lo, hi in [("split-CP", s_lo, s_hi), ("Mondrian-split-CP", m_lo, m_hi),
                             ("ACI", a_lo, a_hi), ("ToD-ACI", t_lo, t_hi)]:
            for bk in ORDER:
                sel = (b_te == bk)
                if not sel.any():
                    continue
                cov = ((y_te[sel] >= lo[sel]) & (y_te[sel] <= hi[sel])).mean()
                gi = ginfo.get(bk, {})
                rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], bucket=bk, method=meth,
                                 PICP=float(cov), MPIW=float(np.mean(hi[sel] - lo[sel])),
                                 n_cell=int(sel.sum()),
                                 n_own=gi.get("n_own"), n_init=gi.get("n_init"),
                                 fell_back=gi.get("fell_back"), gamma=gam, degenerate=degenerate))
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    if rows:
        rd = pd.DataFrame(rows)
        if FB.exists():
            rd = pd.concat([pd.read_csv(FB), rd], ignore_index=True)
        rd.to_csv(FB, index=False)

    fb = pd.read_csv(FB)
    remaining = [f for f in all_fac if f not in set(fb.facility_id.unique())]
    if remaining:
        log(f"REMAINING: {len(remaining)}")
    else:
        write_summary(fb[fb.degenerate != True], args.min_cell)
        log(f"ALL DONE: {fb.facility_id.nunique()} facilities")


if __name__ == "__main__":
    main()
