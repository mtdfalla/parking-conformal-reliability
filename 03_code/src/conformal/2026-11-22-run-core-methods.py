#!/usr/bin/env python3
"""
Canonical per-facility conformal run — split-CP, CQR, ACI, ACQR.
Successor of `2026-09-02-run-core-methods.py` (EXP-042). The changes, and no others:
  * `--features v3` reads the availability-safe Birmingham table (no interpolation, observed targets);
    Belgrade has one table and reads it under v2 and v3 alike. **v3 is the default** (it was v2).
  * every row records `n_inverted` (final bands that are empty under core.finalize_band) and, for the
    adaptive methods, `n_alpha_clipped` (steps at which the adaptive level sat on a projection bound)
    and `n_q_saturated` (steps at which the quantile sat at the pool maximum, review finding 6);
  * `--feat-dir`, `--out-dir` and `--horizon` let a bounded check run outside the repository.
  * Revision 56 (review findings 1 and 2). Output names carry this script's date and the feature
    version, `2026-11-22-core-{dataset}-{features}[-S1][-gcal]-...`, so no v3 run can find a v2 file
    and resume from it. Every row records `features`, `feature_sha256` and `row_filter`. Resume is
    keyed on (facility, horizon), and the run REFUSES to resume from a file written under another
    feature table, another row filter, or without the counter columns. A `--horizon` that matches no
    horizon of the dataset exits with an error instead of writing skipped rows.
  * Revision 56 (EXP-042 addendum, D-038). `--row-filter v2-rows --s1-keys V2_PARQUET` is sensitivity S1:
    only the v3 rows whose (facility, timestamp) were usable at the same horizon in the v2 table, which is
    v2's row filter applied to the v3 inputs (12,797 rows at t+60). The addendum's wording "all three
    targets observed" would keep 6,179 rows and fail the thin-facility guard at 27 of 28 facilities, and
    it is not v2's filter: v2's targets were present because they were interpolated. Birmingham v3 runs also write the per-row coverage at
    level 0.90 (`...-rows-L90.csv`, with `occ_carried`), from which sensitivity S2 is computed with no refit;
    Belgrade runs write the same file for y_t+15min, read by the block-bootstrap sensitivity (EXP-042 s. 8).
The text below describes the run it replaces and still holds.

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

Usage:  python 2026-11-22-run-core-methods.py --dataset belgrade|birmingham [--budget 150]
Resumable: re-run until it prints ALL DONE.
Output:  05_results/tables/2026-11-22-core-{dataset}-{features}[-S1][-gcal]-per-facility.csv
         05_results/tables/2026-11-22-core-{dataset}-{features}[-S1][-gcal]-basemodel.csv
         05_results/tables/2026-11-22-core-{dataset}-{features}[-S1][-gcal]-rows-L90.csv
             (per-row coverage at 0.90: every Birmingham horizon; Belgrade y_t+15min only; occ_carried = -1
              where the table has no such flag)
"""
from __future__ import annotations
import argparse, hashlib, sys, time, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

_p = Path(__file__).resolve()
while _p != _p.parent and not (_p / "01_data").is_dir():
    _p = _p.parent
ROOT = _p
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
         "v2": {"belgrade": "belgrade_features_v2.parquet", "birmingham": "birmingham_features_v2.parquet"},
         "v3": {"belgrade": "belgrade_features_v2.parquet", "birmingham": "birmingham_features_v3.parquet"}}

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
    ap.add_argument("--features", choices=["v1", "v2", "v3"], default="v3",
                    help="v3 = availability-safe tables (default); v2, v1 = superseded, for attribution only")
    ap.add_argument("--feat-dir", default=None, help="directory holding the feature table (default 01_data/processed)")
    ap.add_argument("--out-dir", default=None, help="directory for the output tables (default 05_results/tables)")
    ap.add_argument("--horizon", default=None, help="run one horizon only, e.g. y_t+60min")
    ap.add_argument("--row-filter", choices=["main", "v2-rows"], default="main",
                    help="v2-rows = sensitivity S1: only rows usable at the same horizon in the v2 table")
    ap.add_argument("--s1-keys", default=None, help="the v2 feature table whose use_H row sets define S1")
    ap.add_argument("--gamma-mode", choices=["fixed", "calibrated"], default="calibrated",
                    help="calibrated = select gamma per facility/horizon on a nested calibration split "
                         "(EXP-018); fixed = the retired project-wide gamma = 0.05")
    args = ap.parse_args()
    cfg = dict(CFG[args.dataset]); cfg["feat"] = FEATS[args.features][args.dataset]
    tag = f"{args.dataset}-{args.features}" + ("-S1" if args.row_filter == "v2-rows" else "")
    global PROC, TAB
    if args.feat_dir: PROC = Path(args.feat_dir)
    if args.out_dir: TAB = Path(args.out_dir); TAB.mkdir(parents=True, exist_ok=True)
    if args.horizon:
        known = [h[0] for h in cfg["H"]]
        cfg["H"] = [h for h in cfg["H"] if h[0] == args.horizon]
        if not cfg["H"]:
            sys.exit(f"[core-run] --horizon {args.horizon!r} matches none of {known}; nothing run")
    if args.gamma_mode == "calibrated": tag += "-gcal"
    block = core.block_length_for_cadence(cfg["cadence_min"], BOOT_HOURS)

    feat_path = PROC/cfg["feat"]
    feat_sha = hashlib.sha256(feat_path.read_bytes()).hexdigest()
    df = pd.read_parquet(feat_path)
    s1_keys = None; row_filter_stamp = args.row_filter
    if args.row_filter == "v2-rows":
        if not args.s1_keys: sys.exit("[core-run] --row-filter v2-rows needs --s1-keys (the v2 feature table)")
        kp = Path(args.s1_keys); v2 = pd.read_parquet(kp)
        s1_keys = {H: set(zip(v2.loc[v2[f"use_{H}"], "facility_id"], v2.loc[v2[f"use_{H}"], "timestamp"]))
                   for _, H, _ in cfg["H"]}
        row_filter_stamp = "v2-rows:" + hashlib.sha256(kp.read_bytes()).hexdigest()[:16]
    # Per-row coverage at level 0.90: every Birmingham horizon (sensitivity S2 reads occ_carried), and the
    # Belgrade primary horizon only (the block-bootstrap sensitivity of EXP-042 section 8 reads it).
    ROWS_H = {"birmingham": None, "belgrade": {"y_t+15min"}}[args.dataset]
    has_carried = "occ_carried" in df.columns
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    all_fac = sorted(sd.index)
    dyn_flag = {f: bool(sd[f] >= DYN) for f in all_fac}

    PER = TAB/f"2026-11-22-core-{tag}-per-facility.csv"
    MAE = TAB/f"2026-11-22-core-{tag}-basemodel.csv"
    ROWS = TAB/f"2026-11-22-core-{tag}-rows-L90.csv"
    stamp = dict(features=args.features, feature_sha256=feat_sha, row_filter=row_filter_stamp)
    hz_names = [h[0] for h in cfg["H"]]
    done_pairs = set()
    # Resume is checked on ALL THREE outputs (review of revision 56, finding 1). Each must carry the stamp of
    # this run. The basemodel and per-row files may not exist without the per-facility file, which is the
    # record of what is done. Rows they hold for an unfinished (facility, horizon) are orphans of a run that
    # died between saves; they are dropped at the next save, never appended to.
    need = {"features", "feature_sha256", "row_filter"}
    outs = [f for f in (PER, MAE, ROWS) if f.exists()]
    if outs and not PER.exists():
        sys.exit(f"[core-run] REFUSING to run: {[f.name for f in outs]} exist without {PER.name}. "
                 "Supersede them by moving them, then re-run.")
    for f in outs:
        prev = pd.read_csv(f)
        miss = (need | ({"n_inverted"} if f == PER else set())) - set(prev.columns)
        if miss:
            sys.exit(f"[core-run] REFUSING to resume from {f.name}: it lacks {sorted(miss)}. It was written by "
                     "another runner; supersede every output of this tag by moving it, then re-run.")
        bad = prev[(prev.features != args.features) | (prev.feature_sha256 != feat_sha) |
                   (prev.row_filter != row_filter_stamp)]
        if len(bad):
            sys.exit(f"[core-run] REFUSING to resume from {f.name}: {len(bad)} row(s) were written under another "
                     "feature table or row filter.")
        if f == PER:
            done_pairs = set(zip(prev.facility_id, prev.horizon))
    done_at_start = set(done_pairs)
    def keep_done(frame):   # drop orphan rows of (facility, horizon) pairs the per-facility file does not hold
        k = [(a, b) in done_at_start for a, b in zip(frame.facility_id, frame.horizon)]
        return frame[np.array(k, dtype=bool)] if len(frame) else frame
    def fac_done(f):
        return (f, "(none)") in done_pairs or all((f, h) in done_pairs for h in hz_names)
    todo = [f for f in all_fac if not fac_done(f)]
    log(f"{tag} [{args.features} features]: block={block} rows ({BOOT_HOURS} h); {len(all_fac) - len(todo)} done, {len(todo)} to do "
        f"({sum(dyn_flag.values())} of {len(all_fac)} dynamic)")

    rows = []; mrows = []; prow = []; t0 = time.time()
    for fid in todo:
        produced_any = False
        if time.time() - t0 > args.budget:
            log("budget hit; saving and exiting"); break
        g_all = df[df.facility_id == fid].sort_values("timestamp")
        for hz, hmin, hsteps in cfg["H"]:
            if (fid, hz) in done_pairs: continue
            g = g_all[g_all[f"use_{hmin}"]] if f"use_{hmin}" in g_all.columns else g_all
            if s1_keys is not None:
                g = g[np.fromiter(((f, t) in s1_keys[hmin] for f, t in zip(g.facility_id, g.timestamp)),
                                  bool, count=len(g))]
            g = g.dropna(subset=["occupancy"] + FEAT + [hz])
            tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
            # Thin-facility guard. Deliberately permissive: the retired scripts had no guard at all, so a
            # strict one here would silently shrink the reported facility count. n_test is recorded on
            # every row instead, letting the analysis filter thin facilities rather than the runner.
            if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
                log(f"  fac {fid} {hz}: too few rows (tr{len(tr)}/ca{len(ca)}/te{len(te)}) — skipped")
                rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], horizon=hz, level=np.nan,
                                 method="SKIPPED-thin", PICP=np.nan, MPIW=np.nan, Winkler=np.nan,
                                 n_test=len(te), n_cal=len(ca), **stamp))
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
                                  n_test=len(y_te), **stamp))

            def record(method, lo, hi, lvl, extra=None):
                al = 1 - lvl
                p, m, w = core.interval_metrics(y_te, lo, hi, al)
                rec = dict(facility_id=fid, dynamic=dyn_flag[fid], horizon=hz, level=lvl, method=method,
                           PICP=p, MPIW=m, Winkler=w, n_test=len(y_te), n_cal=len(y_ca),
                           n_inverted=core.count_inverted(lo, hi), **stamp)
                if abs(lvl - 0.90) < 1e-9:
                    cov = ((y_te >= lo) & (y_te <= hi) & (lo <= hi)).astype(float)   # an inverted band covers nothing
                    if ROWS_H is None or hz in ROWS_H:
                        prow.append(pd.DataFrame(dict(facility_id=fid, horizon=hz, method=method,
                                                      timestamp=te.timestamp.values, covered=cov.astype(int),
                                                      occ_carried=(te.occ_carried.values.astype(int) if has_carried
                                                                   else np.full(len(te), -1)), **stamp)))
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
                a_lo, a_hi, a_dg = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, al,
                                                                  hsteps, gamma=g_aci, return_state=True)
                record("ACI", a_lo, a_hi, lvl,
                       dict(gamma=g_aci, gamma_calB_picp=dg.get("calB_picp"),
                            n_cal_b=dg.get("n_cal_b"),
                            n_alpha_clipped=core.count_alpha_clipped(a_dg["alpha"]),
                            n_q_saturated=core.count_q_saturated(a_dg["alpha"], a_dg["pool_size"])))
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
                q_lo, q_hi, q_dg = core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, al,
                                                                  hsteps, gamma=g_acqr, return_state=True)
                record("ACQR", q_lo, q_hi, lvl,
                       dict(xtra, gamma=g_acqr, gamma_calB_picp=dg2.get("calB_picp"),
                            n_cal_b=dg2.get("n_cal_b"),
                            n_alpha_clipped=core.count_alpha_clipped(q_dg["alpha"]),
                            n_q_saturated=core.count_q_saturated(q_dg["alpha"], q_dg["pool_size"])))
        if not produced_any:   # never leave a facility unrecorded: the resume loop would not terminate
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], horizon="(none)", level=np.nan,
                             method="SKIPPED-no-usable-horizon", PICP=np.nan, MPIW=np.nan,
                             Winkler=np.nan, n_test=0, n_cal=0, **stamp))
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    if rows:
        rd = pd.DataFrame(rows); md = pd.DataFrame(mrows)
        if PER.exists(): rd = pd.concat([pd.read_csv(PER), rd], ignore_index=True)
        if MAE.exists(): md = pd.concat([keep_done(pd.read_csv(MAE)), md], ignore_index=True)
        if prow:   # written BEFORE the per-facility file, so a facility marked done always has its rows
            pr = pd.concat(prow, ignore_index=True)
            if ROWS.exists(): pr = pd.concat([keep_done(pd.read_csv(ROWS)), pr], ignore_index=True)
            pr.to_csv(ROWS, index=False)
        rd.to_csv(PER, index=False); md.to_csv(MAE, index=False)
    per = pd.read_csv(PER)
    done_pairs = set(zip(per.facility_id, per.horizon))
    remaining = [f for f in all_fac if not fac_done(f)]
    log(f"REMAINING {tag}: {len(remaining)}" if remaining
        else f"ALL DONE {tag}: {per.facility_id.nunique()} facilities")

if __name__ == "__main__":
    main()
