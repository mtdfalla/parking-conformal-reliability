#!/usr/bin/env python3
"""
Canonical per-facility conformal run — split-CP, CQR, ACI, ACQR — on the v2 causal feature tables.
R-Phase 2/3 (D-014, EXP-017). Supersedes `run_corrected.py` and `2026-08-04-adaptive-cqr.py`.

WHAT IS DIFFERENT FROM THE SCRIPTS IT REPLACES
----------------------------------------------
* Reads `*_features_v2.parquet` and filters each horizon with `use_{H}` (same-split + embargo), so no
  training or calibration row carries an outcome observed in a later split.                      [S01]
* Birmingham rows come from session-safe features: no lag, anchor or target crosses a night.  [S02/X01]
* Every conformal primitive comes from `core.py`: the k-th order statistic is indexed directly [C01],
  the adaptive state is projected [C02], and the only feedback path is the release queue [C06/C07].
* Bootstrap CIs use B = 10,000 and a cadence-derived block (3 h in both cities) rather than 500
  resamples and a fixed 20 rows that meant 100 min in one city and 600 in the other.            [I06]
* ALL facilities are evaluated and tagged `dynamic` (train-period sd > 5) rather than filtered up front,
  so the exclusion-threshold sensitivity can be produced without another rerun.                 [D05]
* Quantile crossings between the separately fitted CQR models are repaired and COUNTED.

Usage:  python 2026-09-02-run-core-methods.py --dataset belgrade|birmingham [--budget 150]
Resumable: re-run until it prints ALL DONE.
Output:  05_results/tables/2026-09-02-core-{dataset}-per-facility.csv
         05_results/tables/2026-09-02-core-{dataset}-basemodel.csv
"""
from __future__ import annotations
import argparse, sys, time, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; N_TREES = 100; DYN = 5.0; GAMMA = 0.05
LEVELS_ALL = [0.80, 0.85, 0.90, 0.95]      # split-CP and ACI
LEVELS_Q   = [0.90, 0.95]                  # CQR and ACQR (quantile models are level-specific)
BOOT_B = 10_000; BOOT_HOURS = 3.0

# Two feature generations are runnable on purpose. R-Phase 3 compares three points so the number delta
# is ATTRIBUTABLE rather than a single unexplained jump:
#   archived baseline  = old code on v1 features   (00_admin/2026-09-02-preaudit-freeze/)
#   --features v1      = new code on v1 features   -> isolates the code fixes (C01/C02/C06) + library drift
#   --features v2      = new code on v2 features   -> adds the data fixes (S01, S02/X01)
FEATS = {"v1": {"belgrade": "belgrade_features.parquet", "birmingham": "birmingham_features.parquet"},
         "v2": {"belgrade": "belgrade_features_v2.parquet", "birmingham": "birmingham_features_v2.parquet"}}

CFG = {
 "belgrade":   dict(feat="belgrade_features_v2.parquet", cadence_min=5,
                    H=[("y_t+5min", 5, 1), ("y_t+15min", 15, 3), ("y_t+30min", 30, 6)]),
 "birmingham": dict(feat="birmingham_features_v2.parquet", cadence_min=30,
                    H=[("y_t+30min", 30, 1), ("y_t+60min", 60, 2), ("y_t+90min", 90, 3)]),
}

def log(m): print(f"[core-run] {m}", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(CFG))
    ap.add_argument("--budget", type=float, default=150.0, help="seconds before saving and exiting")
    ap.add_argument("--features", choices=["v1", "v2"], default="v2",
                    help="v2 = causally corrected tables (default); v1 = legacy, for attribution only")
    ap.add_argument("--gamma-mode", choices=["fixed", "calibrated"], default="calibrated",
                    help="calibrated = select gamma per facility/horizon on a nested calibration split "
                         "(EXP-018); fixed = the retired project-wide gamma = 0.05")
    args = ap.parse_args()
    cfg = dict(CFG[args.dataset]); cfg["feat"] = FEATS[args.features][args.dataset]
    tag = f"{args.dataset}" if args.features == "v2" else f"{args.dataset}-onV1"
    if args.gamma_mode == "calibrated": tag += "-gcal"
    block = core.block_length_for_cadence(cfg["cadence_min"], BOOT_HOURS)

    df = pd.read_parquet(PROC/cfg["feat"])
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    all_fac = sorted(sd.index)
    dyn_flag = {f: bool(sd[f] >= DYN) for f in all_fac}

    PER = TAB/f"2026-09-02-core-{tag}-per-facility.csv"
    MAE = TAB/f"2026-09-02-core-{tag}-basemodel.csv"
    done = set(pd.read_csv(PER).facility_id.unique()) if PER.exists() else set()
    todo = [f for f in all_fac if f not in done]
    log(f"{tag} [{args.features} features]: block={block} rows ({BOOT_HOURS} h); {len(done)} done, {len(todo)} to do "
        f"({sum(dyn_flag.values())} of {len(all_fac)} dynamic)")

    rows = []; mrows = []; t0 = time.time()
    for fid in todo:
        produced_any = False
        if time.time() - t0 > args.budget:
            log("budget hit; saving and exiting"); break
        g_all = df[df.facility_id == fid].sort_values("timestamp")
        for hz, hmin, hsteps in cfg["H"]:
            g = g_all[g_all[f"use_{hmin}"]] if f"use_{hmin}" in g_all.columns else g_all
            g = g.dropna(subset=["occupancy"] + FEAT + [hz])
            tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
            # Thin-facility guard. Deliberately permissive: the retired scripts had no guard at all, so a
            # strict one here would silently shrink the reported facility count. n_test is recorded on
            # every row instead, letting the analysis filter thin facilities rather than the runner.
            if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
                log(f"  fac {fid} {hz}: too few rows (tr{len(tr)}/ca{len(ca)}/te{len(te)}) — skipped")
                rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], horizon=hz, level=np.nan,
                                 method="SKIPPED-thin", PICP=np.nan, MPIW=np.nan, Winkler=np.nan,
                                 n_test=len(te), n_cal=len(ca)))
                produced_any = True
                continue
            occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
            d_tr = tr[hz].values - occ_tr; y_ca = ca[hz].values; y_te = te[hz].values

            rf = RandomForestRegressor(n_estimators=N_TREES, min_samples_leaf=2, n_jobs=-1,
                                       random_state=SEED).fit(tr[FEAT].values, d_tr)
            yhat_ca = occ_ca + rf.predict(ca[FEAT].values)
            yhat_te = occ_te + rf.predict(te[FEAT].values)
            resid = np.abs(y_ca - yhat_ca)

            rfa = RandomForestRegressor(n_estimators=N_TREES, min_samples_leaf=2, n_jobs=-1,
                                        random_state=SEED).fit(tr[FEAT].values, tr[hz].values)
            for nm, pred in [("RF-delta", yhat_te), ("persistence", occ_te),
                             ("RF-absolute", rfa.predict(te[FEAT].values))]:
                e = y_te - pred
                mrows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], horizon=hz, model=nm,
                                  MAE=float(np.mean(np.abs(e))), RMSE=float(np.sqrt(np.mean(e**2))),
                                  n_test=len(y_te)))

            def record(method, lo, hi, lvl, extra=None):
                al = 1 - lvl
                p, m, w = core.interval_metrics(y_te, lo, hi, al)
                rec = dict(facility_id=fid, dynamic=dyn_flag[fid], horizon=hz, level=lvl, method=method,
                           PICP=p, MPIW=m, Winkler=w, n_test=len(y_te), n_cal=len(y_ca))
                if abs(lvl - 0.90) < 1e-9:
                    cov = ((y_te >= lo) & (y_te <= hi)).astype(float)
                    c_lo, c_hi = core.moving_block_bootstrap_ci(cov, B=BOOT_B, block=block, seed=SEED)
                    rec["picp_ci_lo"], rec["picp_ci_hi"] = c_lo, c_hi
                if extra: rec.update(extra)
                rows.append(rec)

            produced_any = True
            for lvl in LEVELS_ALL:
                al = 1 - lvl
                record("split-CP", *core.split_conformal_interval(resid, yhat_te, al), lvl)
                if args.gamma_mode == "calibrated":
                    g_aci, dg = core.select_gamma_on_calibration(
                        resid, yhat_ca, yhat_ca, y_ca, al, hsteps)
                else:
                    g_aci, dg = GAMMA, {}
                record("ACI", *core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, al,
                                                              hsteps, gamma=g_aci), lvl,
                       dict(gamma=g_aci, gamma_calB_picp=dg.get("calB_picp"),
                            n_cal_b=dg.get("n_cal_b")))
            for lvl in LEVELS_Q:
                al = 1 - lvl
                glo = HistGradientBoostingRegressor(loss="quantile", quantile=al/2, max_iter=100,
                                                    random_state=SEED).fit(tr[FEAT].values, d_tr)
                ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1-al/2, max_iter=100,
                                                    random_state=SEED).fit(tr[FEAT].values, d_tr)
                qlo_ca = occ_ca + glo.predict(ca[FEAT].values); qhi_ca = occ_ca + ghi.predict(ca[FEAT].values)
                qlo_te = occ_te + glo.predict(te[FEAT].values); qhi_te = occ_te + ghi.predict(te[FEAT].values)
                qlo_ca, qhi_ca, nx_ca = core.repair_quantile_crossing(qlo_ca, qhi_ca)
                qlo_te, qhi_te, nx_te = core.repair_quantile_crossing(qlo_te, qhi_te)
                E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)
                xtra = dict(n_crossings_cal=nx_ca, n_crossings_test=nx_te)
                record("CQR", *core.cqr_interval(E_cal, qlo_te, qhi_te, al), lvl, xtra)
                if args.gamma_mode == "calibrated":
                    g_acqr, dg2 = core.select_gamma_on_calibration(
                        E_cal, qlo_ca, qhi_ca, y_ca, al, hsteps)
                else:
                    g_acqr, dg2 = GAMMA, {}
                record("ACQR", *core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, al,
                                                               hsteps, gamma=g_acqr), lvl,
                       dict(xtra, gamma=g_acqr, gamma_calB_picp=dg2.get("calB_picp"),
                            n_cal_b=dg2.get("n_cal_b")))
        if not produced_any:   # never leave a facility unrecorded: the resume loop would not terminate
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], horizon="(none)", level=np.nan,
                             method="SKIPPED-no-usable-horizon", PICP=np.nan, MPIW=np.nan,
                             Winkler=np.nan, n_test=0, n_cal=0))
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    if rows:
        rd = pd.DataFrame(rows); md = pd.DataFrame(mrows)
        if PER.exists(): rd = pd.concat([pd.read_csv(PER), rd], ignore_index=True)
        if MAE.exists(): md = pd.concat([pd.read_csv(MAE), md], ignore_index=True)
        rd.to_csv(PER, index=False); md.to_csv(MAE, index=False)
    per = pd.read_csv(PER)
    remaining = [f for f in all_fac if f not in set(per.facility_id.unique())]
    log(f"REMAINING {tag}: {len(remaining)}" if remaining
        else f"ALL DONE {tag}: {per.facility_id.nunique()} facilities")

if __name__ == "__main__":
    main()
