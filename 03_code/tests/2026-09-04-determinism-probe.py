#!/usr/bin/env python3
"""
R-PHASE 6, SECTION 0 — ENVIRONMENT DETERMINISM PROBE. Measures nothing about the paper.

WHY THIS EXISTS
---------------
R-Phase 6's gate is stated as "a from-scratch run reproduces every manifest hash within tolerance".
A hash has no tolerance, so the gate needs a TOLERANCE TABLE, and a tolerance table invented after
seeing the clean-room output would be the packaging analogue of changing the evaluation criterion
after seeing the result (the forbidden repair). This probe measures the reproducibility floor of the
ACTUAL pipeline BEFORE that table is written, so its numbers are measured rather than assumed.

WHAT IT MEASURES
----------------
LESSONS_LOG A8 records that `n_jobs=-1` RandomForest is nondeterministic at ~1e-14 because the thread
reduction order varies. That is a WITHIN-machine observation; the clean-room gate is a CROSS-machine
claim, where the thread count itself differs. The mechanism is the same, so varying the thread count
bounds the cross-machine component directly:

  arm A : n_jobs=-1, first pass    (exactly what the shipped runner does)
  arm B : n_jobs=-1, second pass   -> within-process repeatability at the same thread count
  arm C : n_jobs=1                 -> single-thread reference; A-vs-C bounds the reduction-order term

Everything else is held identical to `2026-09-02-run-core-methods.py`: same v2 features, same splits,
same SEED, same hyperparameters, same `core.py` primitives, same metric function (B6).

WHAT IT DOES NOT DO
-------------------
It contributes to no reported number, writes to no logged CSV, and touches neither `core.py` nor the
test suite. Its output file is new and dated. Facility 8 and facility 1 are excluded through
`core.low_information_facilities` on the test split, so no second definition is written (B9/D-018).

Usage:  python 2026-09-04-determinism-probe.py [--n-facilities 3] [--budget 150]
Output: 05_results/tables/2026-09-04-determinism-probe.csv   (resumable per facility, A1/A2)
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

p = Path(__file__).resolve()
while p != p.parent and not (p / "01_data").is_dir():
    p = p.parent
ROOT = p
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
import core  # noqa: E402

PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"
OUT = TAB / "2026-09-04-determinism-probe.csv"

SEED = 42
N_TREES = 100
HZ, HMIN, HSTEPS = "y_t+15min", 15, 3
LEVEL = 0.90


def log(m):
    print(f"[probe] {m}", flush=True)


def fit_and_score(tr, ca, te, FEAT, n_jobs):
    """One complete per-facility computation at a given thread count. Mirrors the canonical runner."""
    occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
    d_tr = tr[HZ].values - occ_tr
    y_ca, y_te = ca[HZ].values, te[HZ].values
    al = 1 - LEVEL

    rf = RandomForestRegressor(n_estimators=N_TREES, min_samples_leaf=2, n_jobs=n_jobs,
                               random_state=SEED).fit(tr[FEAT].values, d_tr)
    yhat_ca = occ_ca + rf.predict(ca[FEAT].values)
    yhat_te = occ_te + rf.predict(te[FEAT].values)
    resid = np.abs(y_ca - yhat_ca)

    out = {}
    lo, hi = core.split_conformal_interval(resid, yhat_te, al)
    out["split-CP"] = core.interval_metrics(y_te, lo, hi, al)

    g_aci, _ = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca, al, HSTEPS)
    lo, hi = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, al, HSTEPS, gamma=g_aci)
    out["ACI"] = core.interval_metrics(y_te, lo, hi, al)

    glo = HistGradientBoostingRegressor(loss="quantile", quantile=al / 2, max_iter=100,
                                        random_state=SEED).fit(tr[FEAT].values, d_tr)
    ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1 - al / 2, max_iter=100,
                                        random_state=SEED).fit(tr[FEAT].values, d_tr)
    qlo_ca = occ_ca + glo.predict(ca[FEAT].values); qhi_ca = occ_ca + ghi.predict(ca[FEAT].values)
    qlo_te = occ_te + glo.predict(te[FEAT].values); qhi_te = occ_te + ghi.predict(te[FEAT].values)
    qlo_ca, qhi_ca, _ = core.repair_quantile_crossing(qlo_ca, qhi_ca)
    qlo_te, qhi_te, _ = core.repair_quantile_crossing(qlo_te, qhi_te)
    E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)

    lo, hi = core.cqr_interval(E_cal, qlo_te, qhi_te, al)
    out["CQR"] = core.interval_metrics(y_te, lo, hi, al)

    g_acqr, _ = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, al, HSTEPS)
    lo, hi = core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, al, HSTEPS, gamma=g_acqr)
    out["ACQR"] = core.interval_metrics(y_te, lo, hi, al)
    return out, (g_aci, g_acqr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-facilities", type=int, default=3)
    ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args()

    df = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    low = set(core.low_information_facilities(df[df.split == "test"]))
    cand = [f for f in sorted(sd.index) if sd[f] >= 5.0 and f not in low]
    todo = cand[:args.n_facilities]
    log(f"probing {todo} (of {len(cand)} dynamic; low-information excluded: {sorted(low)})")

    done = set(pd.read_csv(OUT).facility_id.unique()) if OUT.exists() else set()
    if done:
        log(f"resuming: {sorted(done)} already probed")

    rows = []
    t0 = time.time()
    for fid in todo:
        if fid in done:
            continue
        if time.time() - t0 > args.budget:
            log("budget hit; saving and exiting")
            break
        g = df[df.facility_id == fid].sort_values("timestamp")
        g = g[g[f"use_{HMIN}"]] if f"use_{HMIN}" in g.columns else g
        g = g.dropna(subset=["occupancy"] + FEAT + [HZ])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
            log(f"  fac {fid}: too few rows — skipped")
            rows.append(dict(facility_id=fid, method="SKIPPED-thin"))
            continue

        A, gA = fit_and_score(tr, ca, te, FEAT, n_jobs=-1)
        B, gB = fit_and_score(tr, ca, te, FEAT, n_jobs=-1)
        C, gC = fit_and_score(tr, ca, te, FEAT, n_jobs=1)

        for meth in ["split-CP", "ACI", "CQR", "ACQR"]:
            for qi, qn in enumerate(["PICP", "MPIW", "Winkler"]):
                a, b, c = A[meth][qi], B[meth][qi], C[meth][qi]
                rows.append(dict(
                    facility_id=fid, n_test=len(te), method=meth, quantity=qn,
                    armA_njobs_all=a, armB_njobs_all_repeat=b, armC_njobs_1=c,
                    abs_AB=abs(a - b), abs_AC=abs(a - c),
                    rel_AB=(abs(a - b) / abs(a)) if a else np.nan,
                    rel_AC=(abs(a - c) / abs(a)) if a else np.nan,
                    gamma_aci_A=gA[0], gamma_acqr_A=gA[1],
                    gamma_stable=bool(gA == gB == gC)))
        # flush after every unit (A1)
        out = pd.DataFrame(rows)
        if OUT.exists():
            out = pd.concat([pd.read_csv(OUT), out], ignore_index=True)
        out.to_csv(OUT, index=False)
        rows = []
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    have = set(pd.read_csv(OUT).facility_id.unique()) if OUT.exists() else set()
    rem = [f for f in todo if f not in have]
    log(f"REMAINING {len(rem)}" if rem else "ALL DONE")


if __name__ == "__main__":
    main()
