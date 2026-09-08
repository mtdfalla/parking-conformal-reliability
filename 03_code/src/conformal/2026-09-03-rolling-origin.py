#!/usr/bin/env python3
"""
R-Phase 3b task 5 — rolling-origin evaluation, Belgrade. Logged as EXP-026.
SUPERSEDES `2026-08-04-rolling-origin.py` (EXP-013), which carries audit issues I04 and I05.

WHAT THIS FIXES relative to the archived script
-----------------------------------------------
I05  The archived script selected the dynamic facility set ONCE, from the main train window
     (`df[df.split=="train"]`, through Mar 13), and applied it to all three folds — so fold F1's
     inclusion rule saw data from after F1's own training window. Here the set is recomputed inside
     EACH fold's own training window (`dynamic_fold`). Every facility is run in every fold regardless,
     with both the per-fold and the archived flag recorded, so the all-facility sensitivity arm and the
     I05 delta both come out of one run.

I04  is a REPORTING defect and is fixed in the companion analysis script, not here: this script emits
     per-fold-per-facility rows and takes no inferential position at all. See
     `2026-09-03-rolling-origin-inference.py`.

Not audit issues, but three further defects of the archived script, fixed by construction:
  * it read v1 features (pre-S01/S02/X01) and did not filter on `use_{H}`;
  * it carried a PRIVATE copy of the ACI recursion containing the C01 off-by-one (it computed a LEVEL
    k/m and called np.quantile(..., method="higher"), returning the (k+1)-th order statistic). Every
    primitive here comes from `core.py`, which is under the 39-check property gate;
  * it used a fixed gamma = 0.05. The R-Phase 3b definition of done requires
    `core.select_gamma_on_calibration`. Both arms are run here, PAIRED on one fitted model per
    fold-facility, so the change from the archived numbers can be split between "the fixes" and "the
    gamma protocol" rather than being confounded (the D-017 pairing principle).

The analysis plan was fixed in advance:
`04_experiments/2026-09-03-rolling-origin-PRESPECIFICATION.md`. Read it before changing anything here.

Usage:  python 2026-09-03-rolling-origin.py [--budget 150]
Resumable: unit = (fold, facility). The CSV is flushed after EVERY unit, so an interrupted call loses at
most one facility. Re-run until it prints ALL DONE.
Output: 05_results/tables/2026-09-03-rolling-origin-belgrade.csv
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"
OUT = TAB / "2026-09-03-rolling-origin-belgrade.csv"

SEED = 42
DYN = 5.0                      # occupancy-std threshold for the "dynamic" set
HZ = "y_t+15min"; HMIN = 15; HSTEPS = 3
LEVEL = 0.90; ALPHA = 1 - LEVEL
GAMMA_ARCHIVED = 0.05
MIN_TR, MIN_CA, MIN_TE = 500, 200, 200

# EXP-013 fold geometry, held fixed. (name, train_start, cal_start, test_start, test_end) half-open.
FOLDS = [("F1", "2017-03-04", "2017-03-10", "2017-03-13", "2017-03-16"),
         ("F2", "2017-03-04", "2017-03-13", "2017-03-16", "2017-03-19"),
         ("F3", "2017-03-04", "2017-03-16", "2017-03-19", "2017-03-22")]


def log(m): print(f"[roll] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args()

    df = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    df["ts"] = pd.to_datetime(df.timestamp)
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]

    # the ARCHIVED inclusion rule, recorded per row only so the I05 delta is measurable
    sd_main = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    dyn_archived = {f: bool(sd_main.get(f, np.nan) >= DYN) for f in sorted(df.facility_id.unique())}
    all_fac = sorted(df.facility_id.unique())

    done = set()
    if OUT.exists():
        prev = pd.read_csv(OUT)
        done = set(zip(prev.fold, prev.facility_id))
    units = [(f[0], fid) for f in FOLDS for fid in all_fac if (f[0], fid) not in done]
    log(f"{len(done)} units done, {len(units)} to do ({len(all_fac)} facilities x {len(FOLDS)} folds)")

    fold_by_name = {f[0]: f for f in FOLDS}
    t0 = time.time()
    n_this_call = 0

    for fold_name, fid in units:
        if time.time() - t0 > args.budget:
            log("budget hit; exiting cleanly"); break
        _, tr0, ca0, te0, te1 = fold_by_name[fold_name]
        rows = []

        g = df[df.facility_id == fid].sort_values("ts")
        if f"use_{HMIN}" in g.columns:
            g = g[g[f"use_{HMIN}"]]
        g = g.dropna(subset=["occupancy"] + FEAT + [HZ])
        tr = g[(g.ts >= tr0) & (g.ts < ca0)]
        ca = g[(g.ts >= ca0) & (g.ts < te0)]
        te = g[(g.ts >= te0) & (g.ts < te1)]

        std_tr = float(tr.occupancy.std()) if len(tr) > 1 else np.nan
        dyn_fold = bool(std_tr >= DYN) if np.isfinite(std_tr) else False

        if len(tr) < MIN_TR or len(ca) < MIN_CA or len(te) < MIN_TE:
            # A2: a unit that yields nothing MUST still be written, or the resume loop never terminates
            rows.append(dict(fold=fold_name, facility_id=fid, method="SKIPPED-thin", gamma_mode="n/a",
                             gamma=np.nan, PICP=np.nan, MPIW=np.nan, Winkler=np.nan,
                             n_train=len(tr), n_cal=len(ca), n_test=len(te), n_test_dates=0,
                             std_train=std_tr, dynamic_fold=dyn_fold,
                             dynamic_archived=dyn_archived.get(fid, False), degenerate=False,
                             n_qcross_cal=0, n_qcross_test=0))
            log(f"  {fold_name} fac {fid}: thin (tr={len(tr)} ca={len(ca)} te={len(te)}) — SKIPPED")
        else:
            occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
            d_tr = tr[HZ].values - occ_tr
            y_ca, y_te = ca[HZ].values, te[HZ].values
            Xtr, Xca, Xte = tr[FEAT].values, ca[FEAT].values, te[FEAT].values

            rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                                       random_state=SEED).fit(Xtr, d_tr)
            yhat_ca = occ_ca + rf.predict(Xca)
            yhat_te = occ_te + rf.predict(Xte)
            resid = np.abs(y_ca - yhat_ca)
            degenerate = bool(np.max(resid) < 1e-9)

            glo = HistGradientBoostingRegressor(loss="quantile", quantile=ALPHA / 2,
                                                max_iter=100, random_state=SEED).fit(Xtr, d_tr)
            ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1 - ALPHA / 2,
                                                max_iter=100, random_state=SEED).fit(Xtr, d_tr)
            # NB repair_quantile_crossing returns (qlo, qhi, n_crossings) — the count is reported,
            # not silently swallowed, because the audit asked for its frequency.
            qlo_ca, qhi_ca, ncr_ca = core.repair_quantile_crossing(occ_ca + glo.predict(Xca),
                                                                   occ_ca + ghi.predict(Xca))
            qlo_te, qhi_te, ncr_te = core.repair_quantile_crossing(occ_te + glo.predict(Xte),
                                                                   occ_te + ghi.predict(Xte))
            E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)

            # gamma chosen on CALIBRATION ONLY, separately for the two score types
            g_aci, _ = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca, ALPHA, HSTEPS)
            g_acqr, _ = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, ALPHA, HSTEPS)

            # --- non-adaptive methods (gamma-free) --------------------------------------------
            s_lo, s_hi = core.split_conformal_interval(resid, yhat_te, ALPHA)
            c_lo, c_hi = core.cqr_interval(E_cal, qlo_te, qhi_te, ALPHA)
            fixed = {"split-CP": (s_lo, s_hi), "CQR": (c_lo, c_hi)}

            # --- adaptive methods, both gamma arms on the SAME fits (paired) -------------------
            adaptive = {}
            for mode, ga, gx in (("calibrated", g_aci, g_acqr),
                                 ("fixed05", GAMMA_ARCHIVED, GAMMA_ARCHIVED)):
                a_lo, a_hi = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te,
                                                           ALPHA, HSTEPS, gamma=ga)
                x_lo, x_hi = core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te,
                                                           ALPHA, HSTEPS, gamma=gx)
                adaptive[(mode, "ACI")] = (a_lo, a_hi, ga)
                adaptive[(mode, "ACQR")] = (x_lo, x_hi, gx)

            base = dict(fold=fold_name, facility_id=fid, n_train=len(tr), n_cal=len(ca),
                        n_test=len(te), n_test_dates=int(te.ts.dt.date.nunique()),
                        std_train=std_tr, dynamic_fold=dyn_fold,
                        dynamic_archived=dyn_archived.get(fid, False), degenerate=degenerate,
                        n_qcross_cal=ncr_ca, n_qcross_test=ncr_te)
            for meth, (lo, hi) in fixed.items():
                p, m, w = core.interval_metrics(y_te, lo, hi, ALPHA)
                rows.append(dict(base, method=meth, gamma_mode="n/a", gamma=np.nan,
                                 PICP=p, MPIW=m, Winkler=w))
            for (mode, meth), (lo, hi, gam) in adaptive.items():
                p, m, w = core.interval_metrics(y_te, lo, hi, ALPHA)
                rows.append(dict(base, method=meth, gamma_mode=mode, gamma=gam,
                                 PICP=p, MPIW=m, Winkler=w))
            log(f"  {fold_name} fac {fid}: n_te={len(te)} g_aci={g_aci} g_acqr={g_acqr}"
                f"{' DEGENERATE' if degenerate else ''}")

        # ---- FLUSH AFTER EVERY UNIT (A1) ---------------------------------------------------
        rd = pd.DataFrame(rows)
        if OUT.exists():
            rd = pd.concat([pd.read_csv(OUT), rd], ignore_index=True)
        rd.to_csv(OUT, index=False)
        n_this_call += 1

    d = pd.read_csv(OUT)
    have = set(zip(d.fold, d.facility_id))
    remaining = [(f[0], fid) for f in FOLDS for fid in all_fac if (f[0], fid) not in have]
    log(f"this call: {n_this_call} units")
    if remaining:
        log(f"REMAINING: {len(remaining)}")
    else:
        log(f"ALL DONE: {len(have)} fold-facility units, {len(d)} rows")


if __name__ == "__main__":
    main()
