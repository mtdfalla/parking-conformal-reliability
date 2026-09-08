#!/usr/bin/env python3
"""
Does ToD-ACI's conditional advantage survive on partitions it does NOT condition on?
R-Phase 3b task 2b (D-014). Adversarial self-check on EXP-021. Logged as EXP-022.

THE QUESTION
------------
EXP-021 showed ToD-ACI dominating on facility x time-of-day coverage (worst cell 0.842 vs split-CP's
0.516, zero cells below 0.80 vs 14). But ToD-ACI CONDITIONS on time-of-day and was then EVALUATED by
time-of-day, so part of that margin is definitional. A referee will say so. This script asks whether the
advantage is a property of the method or an artifact of the evaluation axis.

DESIGN
------
Identical runs to EXP-021 (same seed, same features, same per-facility gamma, same ToD conditioning), and
the SAME intervals are then scored on four partitions of the test rows:

  A. time_of_day        5 cells  — the conditioning axis (control; reproduces EXP-021)
  B. day_of_week        7 cells  — orthogonal by construction on a regular grid
  C. occupancy_tercile  3 cells  — cut at the facility's TRAINING-window 33/67 percentiles (never test
                                   data). NOT orthogonal to ToD -- occupancy is driven by time of day --
                                   so its association is MEASURED below rather than assumed.
  D. random_5           5 cells  — seeded random labels, matched to A in cell count and hence cell size.
                                   This is the NOISE FLOOR: any method's dispersion here is sampling
                                   noise, because the labels carry no information. A dispersion figure on
                                   B or C only means something relative to D.

Association between each partition and the ToD buckets is reported as Cramer's V, so "orthogonal" is a
measurement, not a claim.

READING THE RESULT
------------------
* If ToD-ACI's dispersion advantage persists on B (and on C beyond its noise floor), the method genuinely
  equalises conditional coverage and the manuscript claim generalises.
* If ToD-ACI collapses to the other methods on B, the EXP-021 result is largely definitional and the
  claim must be narrowed to "condition on the axis you care about" -- still publishable, but a different
  and much weaker sentence.

Usage:  python 2026-09-03-orthogonal-partition-check.py [--budget 150]
Resumable: re-run until it prints ALL DONE. SKIPPED markers for facilities that yield nothing.
Output: 05_results/tables/2026-09-03-orthogonal-partition-cells.csv   (per facility x partition x cell)
        05_results/tables/2026-09-03-orthogonal-partition-summary.csv (written when ALL DONE)
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
MIN_GROUP = 50; MIN_CELL = 30
CELLS = TAB/"2026-09-03-orthogonal-partition-cells.csv"
SUM = TAB/"2026-09-03-orthogonal-partition-summary.csv"
METHODS = ["split-CP", "Mondrian-split-CP", "ACI", "ToD-ACI"]


def log(m): print(f"[orth] {m}", flush=True)


def bucket_of(h):
    for nm, a, b in BUCKETS:
        if a <= h <= b:
            return nm
    return "night"


def cramers_v(x, y) -> float:
    """Association between two categorical labellings. 0 = independent, 1 = perfectly determined."""
    ct = pd.crosstab(pd.Series(x), pd.Series(y)).values.astype(float)
    n = ct.sum()
    if n == 0 or min(ct.shape) < 2:
        return np.nan
    exp = np.outer(ct.sum(1), ct.sum(0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(exp > 0, (ct - exp) ** 2 / exp, 0.0))
    return float(np.sqrt((chi2 / n) / (min(ct.shape) - 1)))


def write_summary(cells: pd.DataFrame) -> None:
    d = cells[(cells.dynamic) & (cells.method != "SKIPPED-thin")].dropna(subset=["PICP"])
    d = d[d.n_cell >= MIN_CELL]
    out = []
    for part in ["time_of_day", "day_of_week", "occupancy_tercile", "random_5"]:
        pp = d[d.partition == part]
        if pp.empty:
            continue
        v = float(pp.cramers_v_vs_tod.dropna().mean())
        base = pp[pp.method == "split-CP"].PICP.std(ddof=0)
        for m in METHODS:
            s = pp[pp.method == m]
            if s.empty:
                continue
            sdv = float(s.PICP.std(ddof=0))
            out.append(dict(partition=part, cramers_v_vs_tod=round(v, 3), method=m,
                            n_cells=len(s), mean_PICP=round(float(s.PICP.mean()), 4),
                            sd_PICP=round(sdv, 4), min_PICP=round(float(s.PICP.min()), 4),
                            range_PICP=round(float(s.PICP.max() - s.PICP.min()), 4),
                            cells_below_080=int((s.PICP < 0.80).sum()),
                            cells_below_085=int((s.PICP < 0.85).sum()),
                            MPIW=round(float(s.MPIW.mean()), 2),
                            dispersion_ratio_vs_splitCP=round(base / sdv, 2) if sdv > 0 else np.nan))
    pd.DataFrame(out).to_csv(SUM, index=False)
    log(f"wrote {SUM.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args()

    df = pd.read_parquet(PROC/"belgrade_features_v2.parquet")
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    all_fac = sorted(sd.index)
    dyn_flag = {f: bool(sd[f] >= DYN) for f in all_fac}

    done = set(pd.read_csv(CELLS).facility_id.unique()) if CELLS.exists() else set()
    todo = [f for f in all_fac if f not in done]
    log(f"{len(done)} done, {len(todo)} to do ({sum(dyn_flag.values())} of {len(all_fac)} dynamic)")

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
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], partition="(none)", cell="(none)",
                             method="SKIPPED-thin", PICP=np.nan, MPIW=np.nan, n_cell=0,
                             cramers_v_vs_tod=np.nan, degenerate=np.nan))
            log(f"  fac {fid}: too few rows — skipped"); continue

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

        # --- identical intervals to EXP-021 ------------------------------------------------------
        s_lo, s_hi = core.split_conformal_interval(resid, yhat_te, ALPHA)
        q_glob = core.conformal_quantile(resid, ALPHA)
        q_bk = {}
        for bk in ORDER:
            own = cal_by_bucket[bk]
            q_bk[bk] = (core.conformal_quantile(own, ALPHA) if len(own) >= MIN_GROUP
                        else core.conformal_quantile(np.concatenate([own, resid]), ALPHA)
                        if len(own) else q_glob)
        qm = np.array([q_bk[b] for b in b_te])
        m_lo, m_hi = np.maximum(yhat_te - qm, 0.0), yhat_te + qm
        a_lo, a_hi = core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, ALPHA,
                                                    HSTEPS, gamma=gam)
        t_lo, t_hi = core.grouped_adaptive_conformal_stream(
            cal_by_bucket, b_te, yhat_te, yhat_te, y_te, ALPHA, HSTEPS, gamma=gam,
            global_pool=resid, min_group=MIN_GROUP)

        # --- four partitions of the SAME test rows -----------------------------------------------
        ts = pd.to_datetime(te.timestamp.values)
        dow = np.array(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])[ts.dayofweek]
        q33, q67 = np.percentile(tr.occupancy.values, [33.3, 66.7])   # TRAINING window only
        terc = np.where(occ_te <= q33, "low", np.where(occ_te <= q67, "mid", "high"))
        rnd = np.array([f"r{i}" for i in range(5)])[
            np.random.default_rng(SEED).integers(0, 5, len(y_te))]
        parts = {"time_of_day": b_te, "day_of_week": dow,
                 "occupancy_tercile": terc, "random_5": rnd}

        for pname, labels in parts.items():
            v = cramers_v(labels, b_te)
            for meth, lo, hi in [("split-CP", s_lo, s_hi), ("Mondrian-split-CP", m_lo, m_hi),
                                 ("ACI", a_lo, a_hi), ("ToD-ACI", t_lo, t_hi)]:
                for cl in pd.unique(labels):
                    sel = (labels == cl)
                    if not sel.any():
                        continue
                    rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], partition=pname,
                                     cell=str(cl), method=meth,
                                     PICP=float(((y_te[sel] >= lo[sel]) & (y_te[sel] <= hi[sel])).mean()),
                                     MPIW=float(np.mean(hi[sel] - lo[sel])), n_cell=int(sel.sum()),
                                     cramers_v_vs_tod=v, degenerate=degenerate))
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    if rows:
        rd = pd.DataFrame(rows)
        if CELLS.exists():
            rd = pd.concat([pd.read_csv(CELLS), rd], ignore_index=True)
        rd.to_csv(CELLS, index=False)

    c = pd.read_csv(CELLS)
    remaining = [f for f in all_fac if f not in set(c.facility_id.unique())]
    if remaining:
        log(f"REMAINING: {len(remaining)}")
    else:
        write_summary(c[c.degenerate != True])
        log(f"ALL DONE: {c.facility_id.nunique()} facilities")


if __name__ == "__main__":
    main()
