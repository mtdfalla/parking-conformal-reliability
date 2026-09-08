#!/usr/bin/env python3
"""EXP-028 — R-Phase 3b task 5b: the deferred EXP-022 orthogonal check on the rolling-origin folds
and on Birmingham. Closes D-016 #5.

Design, arms, exclusions and decision rules are fixed in
`04_experiments/2026-09-04-task5b-orthogonal-PRESPECIFICATION.md`, written before this ran. Read it
first; this file implements it and takes no design decisions of its own.

Three arms:
  A  folds        Belgrade, the three EXP-013 fold windows, 5 ToD buckets      (replication)
  B  bham-coarse  Birmingham t+60, 5 ToD buckets -- ToD is DEGENERATE here     (primary D-016 #5)
  C  bham-hour    Birmingham t+60, hour-of-day (6 levels), prespecified        (secondary)

Resumable (A1): unit = (arm, fold, facility); the CSV is flushed after EVERY unit, so an interrupted
call loses at most one unit. SKIPPED-thin markers for units that yield nothing (A2). Re-run until it
prints ALL DONE.
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
CELLS = TAB/"2026-09-04-orthogonal-5b-cells.csv"
SUM = TAB/"2026-09-04-orthogonal-5b-summary.csv"

SEED = 42; DYN = 5.0; MIN_GROUP = 50; MIN_CELL = 30
BUCKETS = [("night", 0, 5), ("am_rush", 6, 9), ("midday", 10, 15),
           ("pm_rush", 16, 19), ("evening", 20, 23)]
ORDER = [b[0] for b in BUCKETS]
METHODS = ["split-CP", "Mondrian-split-CP", "ACI", "ToD-ACI"]
DAYS = np.array(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])

# EXP-013 fold geometry, held fixed (name, train_start, cal_start, test_start, test_end), half-open.
FOLDS = [("F1", "2017-03-04", "2017-03-10", "2017-03-13", "2017-03-16"),
         ("F2", "2017-03-04", "2017-03-13", "2017-03-16", "2017-03-19"),
         ("F3", "2017-03-04", "2017-03-16", "2017-03-19", "2017-03-22")]

ARMS = {
    "A_folds":     dict(city="belgrade",   hz="y_t+15min", hmin=15, hsteps=3, axis="tod",  nrand=5),
    "B_bham_coarse": dict(city="birmingham", hz="y_t+60min", hmin=60, hsteps=2, axis="tod",  nrand=5),
    "C_bham_hour": dict(city="birmingham", hz="y_t+60min", hmin=60, hsteps=2, axis="hour", nrand=6),
}


def log(m): print(f"[5b] {m}", flush=True)


def bucket_of(h):
    for nm, a, b in BUCKETS:
        if a <= h <= b:
            return nm
    return "night"


def cramers_v(x, y) -> float:
    ct = pd.crosstab(pd.Series(x), pd.Series(y)).values.astype(float)
    n = ct.sum()
    if n == 0 or min(ct.shape) < 2:
        return np.nan
    exp = np.outer(ct.sum(1), ct.sum(0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(exp > 0, (ct - exp) ** 2 / exp, 0.0))
    return float(np.sqrt((chi2 / n) / (min(ct.shape) - 1)))


def load(city):
    df = pd.read_parquet(PROC/f"{city}_features_v2.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    feat = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    return df, [c for c in feat if c in df.columns]


def windows(arm, cfg, df, fold):
    """(train, cal, test) for one unit. Folds slice by date; Birmingham uses the main split."""
    if arm == "A_folds":
        _, tr0, ca0, te0, te1 = fold
        t = pd.Timestamp
        return (df[(df.timestamp >= t(tr0)) & (df.timestamp < t(ca0))],
                df[(df.timestamp >= t(ca0)) & (df.timestamp < t(te0))],
                df[(df.timestamp >= t(te0)) & (df.timestamp < t(te1))])
    return (df[df.split == "train"], df[df.split == "calibration"], df[df.split == "test"])


def units_for(arm):
    return [f[0] for f in FOLDS] if arm == "A_folds" else ["main"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--arm", default=None, choices=list(ARMS))
    args = ap.parse_args()

    prev = pd.read_csv(CELLS) if CELLS.exists() else None
    done = set(zip(prev.arm, prev.fold, prev.facility_id)) if prev is not None else set()

    cache = {}
    todo = []
    for arm, cfg in ARMS.items():
        if args.arm and arm != args.arm:
            continue
        if cfg["city"] not in cache:
            cache[cfg["city"]] = load(cfg["city"])
        df, _ = cache[cfg["city"]]
        for u in units_for(arm):
            for fid in sorted(df.facility_id.unique()):
                if (arm, u, fid) not in done:
                    todo.append((arm, u, fid))
    log(f"{len(done)} units done, {len(todo)} to do")

    fold_by = {f[0]: f for f in FOLDS}
    t0 = time.time()
    for arm, u, fid in todo:
        if time.time() - t0 > args.budget:
            log("budget hit; exiting cleanly"); break
        cfg = ARMS[arm]
        df, FEAT = cache[cfg["city"]]
        hz, hsteps = cfg["hz"], cfg["hsteps"]
        alpha = 0.10

        g = df[df.facility_id == fid].sort_values("timestamp")
        g = g[g[f"use_{cfg['hmin']}"]] if f"use_{cfg['hmin']}" in g.columns else g
        g = g.dropna(subset=["occupancy", hz] + FEAT)
        tr, ca, te = windows(arm, cfg, g, fold_by.get(u))

        rows = []
        if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
            rows.append(dict(arm=arm, fold=u, facility_id=fid, dynamic=False, low_info=np.nan,
                             partition="(none)", cell="(none)", method="SKIPPED-thin",
                             PICP=np.nan, MPIW=np.nan, n_cell=0, cramers_v=np.nan, degenerate=np.nan))
            log(f"  {arm}/{u} fac {fid}: thin (tr={len(tr)} ca={len(ca)} te={len(te)}) — SKIPPED")
        else:
            std_tr = float(np.std(tr.occupancy.values))
            dyn = bool(std_tr >= DYN)
            low_info = bool(core.is_low_information(te.occupancy.values))   # D-018, scored window

            occ_ca, occ_te = ca.occupancy.values, te.occupancy.values
            rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                                       random_state=SEED).fit(
                tr[FEAT].values, tr[hz].values - tr.occupancy.values)
            yhat_ca = occ_ca + rf.predict(ca[FEAT].values)
            yhat_te = occ_te + rf.predict(te[FEAT].values)
            y_ca, y_te = ca[hz].values, te[hz].values
            resid = np.abs(y_ca - yhat_ca)
            degenerate = bool(np.max(resid) < 1e-9)

            hr_ca = pd.to_datetime(ca.timestamp.values).hour
            hr_te = pd.to_datetime(te.timestamp.values).hour
            if cfg["axis"] == "tod":
                g_ca = np.array([bucket_of(h) for h in hr_ca])
                g_te = np.array([bucket_of(h) for h in hr_te])
            else:
                g_ca = np.array([f"h{h:02d}" for h in hr_ca])
                g_te = np.array([f"h{h:02d}" for h in hr_te])
            levels = list(pd.unique(np.concatenate([g_ca, g_te])))
            cal_by_group = {k: resid[g_ca == k] for k in levels}

            gam, _ = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca, alpha, hsteps)

            s_lo, s_hi = core.split_conformal_interval(resid, yhat_te, alpha)
            q_glob = core.conformal_quantile(resid, alpha)
            q_g = {}
            for k in levels:
                own = cal_by_group[k]
                q_g[k] = (core.conformal_quantile(own, alpha) if len(own) >= MIN_GROUP
                          else core.conformal_quantile(np.concatenate([own, resid]), alpha)
                          if len(own) else q_glob)
            qm = np.array([q_g[k] for k in g_te])
            m_lo, m_hi = np.maximum(yhat_te - qm, 0.0), yhat_te + qm
            a_lo, a_hi = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, alpha,
                                                        hsteps, gamma=gam)
            t_lo, t_hi = core.grouped_adaptive_conformal_stream(
                cal_by_group, g_te, yhat_te, yhat_te, y_te, alpha, hsteps, gamma=gam,
                global_pool=resid, min_group=MIN_GROUP)

            ts = pd.to_datetime(te.timestamp.values)
            dow = DAYS[ts.dayofweek]
            q33, q67 = np.percentile(tr.occupancy.values, [33.3, 66.7])   # TRAINING window only
            terc = np.where(occ_te <= q33, "low", np.where(occ_te <= q67, "mid", "high"))
            k = cfg["nrand"]
            rnd = np.array([f"r{i}" for i in range(k)])[
                np.random.default_rng(SEED).integers(0, k, len(y_te))]

            parts = {"day_of_week": dow, "occupancy_tercile": terc, f"random_{k}": rnd}
            parts["time_of_day" if cfg["axis"] == "tod" else "hour_of_day"] = g_te

            for pname, labels in parts.items():
                v = cramers_v(labels, g_te)
                for meth, lo, hi in [("split-CP", s_lo, s_hi), ("Mondrian-split-CP", m_lo, m_hi),
                                     ("ACI", a_lo, a_hi), ("ToD-ACI", t_lo, t_hi)]:
                    for cl in pd.unique(labels):
                        sel = (labels == cl)
                        if not sel.any():
                            continue
                        rows.append(dict(
                            arm=arm, fold=u, facility_id=fid, dynamic=dyn, low_info=low_info,
                            partition=pname, cell=str(cl), method=meth,
                            PICP=float(((y_te[sel] >= lo[sel]) & (y_te[sel] <= hi[sel])).mean()),
                            MPIW=float(np.mean(hi[sel] - lo[sel])), n_cell=int(sel.sum()),
                            cramers_v=v, degenerate=degenerate))
            # positive control on P14: with one conditioning level, ToD-ACI must equal ACI exactly
            if len(levels) == 1:
                same = bool(np.array_equal(a_lo, t_lo) and np.array_equal(a_hi, t_hi))
                log(f"  {arm}/{u} fac {fid}: single conditioning level -> "
                    f"ToD-ACI == ACI bit-identical: {same}")
                rows.append(dict(arm=arm, fold=u, facility_id=fid, dynamic=dyn, low_info=low_info,
                                 partition="(P14 control)", cell="one_group", method="ToD-ACI==ACI",
                                 PICP=float(same), MPIW=np.nan, n_cell=0, cramers_v=np.nan,
                                 degenerate=degenerate))
            log(f"  {arm}/{u} fac {fid} done ({time.time()-t0:.0f}s, {len(levels)} levels)")

        rd = pd.DataFrame(rows)                                   # FLUSH AFTER EVERY UNIT
        if CELLS.exists():
            rd = pd.concat([pd.read_csv(CELLS), rd], ignore_index=True)
        rd.to_csv(CELLS, index=False)

    c = pd.read_csv(CELLS)
    have = set(zip(c.arm, c.fold, c.facility_id))
    want = []
    for arm, cfg in ARMS.items():
        # 2026-09-05 (revision 44, EXP-035): HONOUR --arm HERE TOO. Without this guard the completion
        # check ranged over ALL arms while the processing loop above ranged over the selected one, so
        # an invocation with --arm printed REMAINING forever once its own arm was complete. `run_all.sh`
        # resumes a step until it prints ALL DONE, so a replicator's run spun this step for its full
        # MAX_ITERS (200 iterations) and then failed. Found by the from-scratch clean-room run, not by
        # reading the code (C12); it changes no number, only the marker the runner reads.
        if args.arm and arm != args.arm:
            continue
        if cfg["city"] not in cache:
            cache[cfg["city"]] = load(cfg["city"])
        df, _ = cache[cfg["city"]]
        want += [(arm, u, fid) for u in units_for(arm) for fid in sorted(df.facility_id.unique())]
    remaining = [w for w in want if w not in have]
    if remaining:
        log(f"REMAINING: {len(remaining)}")
    else:
        log(f"ALL DONE: {len(have)} units")


if __name__ == "__main__":
    main()
