#!/usr/bin/env python3
"""
Base-learner robustness on the shared conformal core — Belgrade, t+15 min.
R-Phase 3b task 1 (D-014). Closes audit issue C06. Logged as EXP-020.

WHY THIS SCRIPT EXISTS
----------------------
The manuscript's Section 5.4 robustness sentence ("ACI std <= 0.002 across base learners";
"split-CP Ridge std 0.103") traces to `05_results/tables/2026-06-21-model-agnostic.csv`, produced by
`model_agnostic.py` -- the ONE script in the project that updated the ACI state immediately within the
same iteration, violating our own delay-aware (no-lookahead) protocol.  That script is retired
(`_retired/model_agnostic.py`); `_ma_delay.py` had the correct delayed feedback but printed to stdout and
persisted nothing.  This script is the canonical, CSV-writing replacement built on `core.py`.        [C06]

WHAT IS DIFFERENT FROM THE SCRIPT IT REPLACES
---------------------------------------------
* Feedback is delayed by h = 3 steps through `core.ReleaseQueue`: the outcome of the interval issued at
  step i enters the score pool and moves the adaptive state at step i + h, never sooner.       [C06]
* The k-th order statistic is indexed directly by `core.conformal_quantile`; the retired script used
  `np.quantile(..., method="higher")` on a converted level, which returns the (k+1)-th.         [C01]
* The adaptive state itself is projected, not just the evaluated level.                         [C02]
* Reads `belgrade_features_v2.parquet` and filters with `use_15` (same-split + h-step embargo), so no
  calibration row carries an outcome observed in a later split.                                 [S01]
* gamma is selected per facility and level by `core.select_gamma_on_calibration` on a nested cal-A/cal-B
  temporal split.  The test set is never touched, and the retired project-wide gamma = 0.05 -- shown in
  EXP-018 to cost 1.3 coverage points at h = 3 -- is no longer assumed.                    [EXP-018/019]
* ALL facilities are evaluated and tagged `dynamic` (train-period sd > 5) rather than filtered up front,
  so the exclusion-threshold sensitivity is available without another rerun.                    [D05]
* Facilities whose calibration scores are identically zero are flagged `degenerate`: their PICP is
  vacuously 1.0 at zero width, which would otherwise inflate both the mean and the dispersion of any
  all-facility sensitivity run later under D05. Flagged and excluded from the summary, never dropped
  from the per-facility table.

CONTROLLED-COMPARISON NOTE
--------------------------
Learner hyperparameters are held at the ARCHIVED values (RF n_estimators=100 min_samples_leaf=2;
HistGBR max_iter=200; Ridge alpha=1.0), NOT the `_ma_delay.py` values (which used max_iter=150), so the
delta against `2026-06-21-model-agnostic.csv` is attributable to the protocol and quantile fixes rather
than to a hyperparameter change.  Two differences remain and are deliberate: intervals are clipped at 0
(occupancy cannot be negative; the retired script did not clip), and the features are v2 rather than v1.
EXP-016 measured the v2 cost on Belgrade at <= 0.6% of rows, so it cannot carry the delta.

Usage:  python 2026-09-03-base-learner-robustness.py [--budget 150]
Resumable: re-run until it prints ALL DONE.  A facility that yields nothing gets a SKIPPED-* marker row,
so the resume loop always terminates (audit issue R02 in miniature).
Output: 05_results/tables/2026-09-03-base-learner-robustness-per-facility.csv   (resumable unit)
        05_results/tables/2026-09-03-base-learner-robustness.csv                (written when ALL DONE,
                                                in the archived schema, for a direct before/after delta)
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; DYN = 5.0
HZ = "y_t+15min"; HMIN = 15; HSTEPS = 3          # Belgrade 5-min cadence -> t+15 is h = 3 steps
LEVELS = [0.90, 0.95]                            # matches the archived baseline
LEARNERS = ["RandomForest", "GradBoost", "Ridge(linear)"]

PER = TAB/"2026-09-03-base-learner-robustness-per-facility.csv"
SUM = TAB/"2026-09-03-base-learner-robustness.csv"


def log(m): print(f"[base-learner] {m}", flush=True)


def learner(name):
    if name == "RandomForest":
        return RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
    if name == "GradBoost":
        return HistGradientBoostingRegressor(max_iter=200, random_state=SEED)
    if name == "Ridge(linear)":
        return Ridge(alpha=1.0)
    raise ValueError(name)


def write_summary(per: pd.DataFrame) -> None:
    """Aggregate to the archived schema: dynamic facilities only, mean/std across facilities."""
    d = per[(per.dynamic) & (per.method.isin(["split-CP", "ACI"]))].copy()
    d = d.dropna(subset=["PICP"])
    if "degenerate" in d.columns:
        n_deg = d[d.degenerate == True].facility_id.nunique()
        if n_deg:
            log(f"excluding {n_deg} degenerate facility(ies) from the summary (zero-width intervals)")
        d = d[d.degenerate != True]
    out = []
    for base in LEARNERS:
        b = d[d.base == base]
        if b.empty:
            continue
        mae = float(b.drop_duplicates(subset=["facility_id"]).MAE.mean())
        for lvl in LEVELS:
            for meth in ["split-CP", "ACI"]:
                s = b[(b.level == lvl) & (b.method == meth)]
                if s.empty:
                    continue
                out.append(dict(base=base, MAE=round(mae, 2), level=lvl, method=meth,
                                meanPICP=round(float(s.PICP.mean()), 4),
                                stdPICP=round(float(s.PICP.std(ddof=0)), 4),
                                MPIW=round(float(s.MPIW.mean()), 2),
                                Winkler=round(float(s.Winkler.mean()), 2),
                                n_facilities=int(s.facility_id.nunique()),
                                median_gamma=(round(float(s.gamma.median()), 4)
                                              if meth == "ACI" else np.nan)))
    pd.DataFrame(out).to_csv(SUM, index=False)
    log(f"wrote {SUM.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0, help="seconds before saving and exiting")
    args = ap.parse_args()

    df = pd.read_parquet(PROC/"belgrade_features_v2.parquet")
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    all_fac = sorted(sd.index)
    dyn_flag = {f: bool(sd[f] >= DYN) for f in all_fac}

    done = set(pd.read_csv(PER).facility_id.unique()) if PER.exists() else set()
    todo = [f for f in all_fac if f not in done]
    log(f"Belgrade {HZ} (h={HSTEPS}): {len(done)} done, {len(todo)} to do "
        f"({sum(dyn_flag.values())} of {len(all_fac)} dynamic)")

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
            log(f"  fac {fid}: too few rows (tr{len(tr)}/ca{len(ca)}/te{len(te)}) — skipped")
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], base="(none)", level=np.nan,
                             method="SKIPPED-thin", PICP=np.nan, MPIW=np.nan, Winkler=np.nan,
                             MAE=np.nan, gamma=np.nan, gamma_calB_picp=np.nan, n_cal_b=np.nan,
                             degenerate=np.nan, cal_score_max=np.nan,
                             n_test=len(te), n_cal=len(ca)))
            log(f"  fac {fid} done ({time.time()-t0:.0f}s)")
            continue

        occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
        d_tr = tr[HZ].values - occ_tr
        y_ca, y_te = ca[HZ].values, te[HZ].values

        for L in LEARNERS:
            m = learner(L).fit(tr[FEAT].values, d_tr)
            yhat_ca = occ_ca + m.predict(ca[FEAT].values)
            yhat_te = occ_te + m.predict(te[FEAT].values)
            resid = np.abs(y_ca - yhat_ca)
            mae = float(np.mean(np.abs(y_te - yhat_te)))
            # A facility whose calibration scores are all ~0 cannot produce a non-zero interval, so its
            # PICP is vacuously 1.0 at zero width. It must not silently enter the D05 all-facility
            # sensitivity as if it were evidence. Flagged, not dropped -- the caller decides.
            cal_score_max = float(np.max(resid))
            degenerate = bool(cal_score_max < 1e-9)

            for lvl in LEVELS:
                al = 1 - lvl

                lo, hi = core.split_conformal_interval(resid, yhat_te, al)
                p, w_, wk = core.interval_metrics(y_te, lo, hi, al)
                rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], base=L, level=lvl,
                                 method="split-CP", PICP=p, MPIW=w_, Winkler=wk, MAE=mae,
                                 gamma=np.nan, gamma_calB_picp=np.nan, n_cal_b=np.nan,
                                 degenerate=degenerate, cal_score_max=cal_score_max,
                                 n_test=len(y_te), n_cal=len(y_ca)))

                gam, dg = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca,
                                                           al, HSTEPS)
                lo, hi = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, al,
                                                        HSTEPS, gamma=gam)
                p, w_, wk = core.interval_metrics(y_te, lo, hi, al)
                rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], base=L, level=lvl,
                                 method="ACI", PICP=p, MPIW=w_, Winkler=wk, MAE=mae,
                                 gamma=gam, gamma_calB_picp=dg.get("calB_picp"),
                                 n_cal_b=dg.get("n_cal_b"),
                                 degenerate=degenerate, cal_score_max=cal_score_max,
                                 n_test=len(y_te), n_cal=len(y_ca)))
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    if rows:
        rd = pd.DataFrame(rows)
        if PER.exists():
            rd = pd.concat([pd.read_csv(PER), rd], ignore_index=True)
        rd.to_csv(PER, index=False)

    per = pd.read_csv(PER)
    remaining = [f for f in all_fac if f not in set(per.facility_id.unique())]
    if remaining:
        log(f"REMAINING: {len(remaining)}")
    else:
        write_summary(per)
        log(f"ALL DONE: {per.facility_id.nunique()} facilities")


if __name__ == "__main__":
    main()
