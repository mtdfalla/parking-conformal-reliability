#!/usr/bin/env python3
"""
EXP-013 — Rolling-origin evaluation, Belgrade (prior review, minor: 4-day test window is thin).

Three expanding-window folds over the 17-day Belgrade record, each with a distinct 3-day test window
(9 distinct test days total vs. the single 4-day window of EXP-010):
  F1: train Mar 4-9,  cal Mar 10-12, test Mar 13-15
  F2: train Mar 4-12, cal Mar 13-15, test Mar 16-18
  F3: train Mar 4-15, cal Mar 16-18, test Mar 19-21
Headline setting: t+15 min, 90% target, 22 dynamic facilities (same set as EXP-010 for comparability).
Methods: split-CP, ACI (delay-aware), CQR, ACQR (delay-aware). Seed 42.
Output: 05_results/tables/2026-08-04-rolling-origin-belgrade.csv (+ printed digest with paired tests
of the fold-pooled per-facility results).
"""
from __future__ import annotations
import math, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; DYN = 5.0; GAMMA = 0.05; HZ = "y_t+15min"; H = 3; LVL = 0.90; AL = 1-LVL
FOLDS = [("F1", "2017-03-04", "2017-03-10", "2017-03-13", "2017-03-16"),
         ("F2", "2017-03-04", "2017-03-13", "2017-03-16", "2017-03-19"),
         ("F3", "2017-03-04", "2017-03-16", "2017-03-19", "2017-03-22")]
OUT = TAB/"2026-08-04-rolling-origin-belgrade.csv"

def log(m): print(f"[roll] {m}", flush=True)
def cq_idx(n, a): return min(math.ceil((n+1)*(1-a)), n)

def split_cp(resid, yhat, a):
    q = np.sort(resid)[cq_idx(len(resid), a)-1]
    return np.maximum(yhat-q, 0.0), yhat+q

def aci_delayed(scores_cal, center_lo, center_hi, y, a, h, gamma=GAMMA, window=None):
    """Generic delayed ACI on given scores; interval = [center_lo - q, center_hi + q].
    For plain ACI pass center_lo = center_hi = yhat and absolute-residual scores;
    for ACQR pass the CQR band and CQR scores."""
    sc = list(scores_cal); al = a; window = window or len(scores_cal); n = len(y)
    lo = np.empty(n); hi = np.empty(n); rel = {}
    for i in range(n):
        for (r, err) in rel.pop(i, []):
            al = al + gamma*(a - err); sc.append(r)
        a_c = min(max(al, 1e-3), 1-1e-3)
        pool = np.asarray(sc[-window:]); m = len(pool)
        lv = min(1.0, cq_idx(m, a_c)/m)
        q = float(np.max(pool)) if lv >= 1 else float(np.quantile(pool, lv, method="higher"))
        lo_raw = center_lo[i]-q; hi[i] = center_hi[i]+q; lo[i] = max(lo_raw, 0.0)
        cov = (y[i] >= lo_raw) and (y[i] <= hi[i])
        s_i = max(center_lo[i]-y[i], y[i]-center_hi[i]) if center_lo[i] != center_hi[i] else abs(y[i]-center_lo[i])
        rel.setdefault(i+h, []).append((s_i, 0 if cov else 1))
    return lo, hi

def winkler(y, lo, hi, a):
    w = hi-lo; s = w.copy(); b = y < lo; u = y > hi
    s[b] += (2/a)*(lo[b]-y[b]); s[u] += (2/a)*(y[u]-hi[u]); return float(np.mean(s))

def mets(y, lo, hi, a):
    return float(np.mean((y >= lo) & (y <= hi))), float(np.mean(hi-lo)), winkler(y, lo, hi, a)

def main():
    df = pd.read_parquet(PROC/"belgrade_features.parquet")
    df["ts"] = pd.to_datetime(df.timestamp)
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    ds = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    dyn = sorted(ds[ds >= DYN].index)
    done = set()
    if OUT.exists():
        prev = pd.read_csv(OUT); done = set(zip(prev.fold, prev.facility_id))
    rows = []; t0 = time.time()
    for fold, tr0, ca0, te0, te1 in FOLDS:
        for fid in dyn:
            if (fold, fid) in done: continue
            if time.time()-t0 > 520: log("budget hit; save+exit"); goto_save = True; break
            g = df[df.facility_id == fid].sort_values("ts").dropna(subset=["occupancy"]+FEAT+[HZ])
            tr = g[(g.ts >= tr0) & (g.ts < ca0)]; ca = g[(g.ts >= ca0) & (g.ts < te0)]
            te = g[(g.ts >= te0) & (g.ts < te1)]
            if len(tr) < 500 or len(ca) < 200 or len(te) < 200: continue
            occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
            d_tr = tr[HZ].values-occ_tr; y_ca = ca[HZ].values; y_te = te[HZ].values
            rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
            rf.fit(tr[FEAT].values, d_tr)
            yhat_ca = occ_ca+rf.predict(ca[FEAT].values); resid = np.abs(y_ca-yhat_ca)
            yhat_te = occ_te+rf.predict(te[FEAT].values)
            glo = HistGradientBoostingRegressor(loss="quantile", quantile=AL/2, max_iter=100, random_state=SEED)
            ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1-AL/2, max_iter=100, random_state=SEED)
            glo.fit(tr[FEAT].values, d_tr); ghi.fit(tr[FEAT].values, d_tr)
            qlo_ca = occ_ca+glo.predict(ca[FEAT].values); qhi_ca = occ_ca+ghi.predict(ca[FEAT].values)
            E_cal = np.maximum(qlo_ca-y_ca, y_ca-qhi_ca)
            qlo_te = occ_te+glo.predict(te[FEAT].values); qhi_te = occ_te+ghi.predict(te[FEAT].values)
            # methods
            slo, shi = split_cp(resid, yhat_te, AL)
            alo, ahi = aci_delayed(resid, yhat_te, yhat_te, y_te, AL, H)
            qh = np.sort(E_cal)[cq_idx(len(E_cal), AL)-1]
            clo, chi = np.maximum(qlo_te-qh, 0.0), qhi_te+qh
            xlo, xhi = aci_delayed(E_cal, qlo_te, qhi_te, y_te, AL, H)
            for meth, (lo, hi) in {"split-CP": (slo, shi), "ACI": (alo, ahi),
                                   "CQR": (clo, chi), "ACQR": (xlo, xhi)}.items():
                p, m, w = mets(y_te, lo, hi, AL)
                rows.append(dict(fold=fold, facility_id=fid, method=meth,
                                 PICP=p, MPIW=m, Winkler=w, n_test=len(y_te)))
        else:
            log(f"{fold} complete"); continue
        break
    if rows:
        rd = pd.DataFrame(rows)
        if OUT.exists(): rd = pd.concat([pd.read_csv(OUT), rd], ignore_index=True)
        rd.to_csv(OUT, index=False)
    d = pd.read_csv(OUT)
    exp = 3*len(dyn)
    got = len(d.groupby(["fold", "facility_id"]))
    log(f"progress: {got} fold-facility pairs (expected <= {exp})")
    if got >= exp - 6:  # allow a few skipped-thin facilities
        print("\n=== Summary by fold and method (t+15, 90%) ===")
        s = d.groupby(["fold", "method"]).agg(mean_PICP=("PICP", "mean"), std_PICP=("PICP", "std"),
                                              frac_within_02=("PICP", lambda x: float(np.mean(np.abs(x-LVL) <= 0.02))),
                                              mean_MPIW=("MPIW", "mean"), mean_Winkler=("Winkler", "mean")).round(4)
        print(s.to_string())
        print("\n=== Pooled across folds (fold-facility as replicate) ===")
        s2 = d.groupby("method").agg(mean_PICP=("PICP", "mean"), std_PICP=("PICP", "std"),
                                     mean_Winkler=("Winkler", "mean")).round(4)
        print(s2.to_string())
        wide = d.pivot_table(index=["fold", "facility_id"], columns="method", values="PICP")
        gap = (wide-LVL).abs()
        print("\n=== Paired |coverage gap|, pooled fold-facility replicates ===")
        for m1, m2 in [("ACI", "split-CP"), ("ACI", "CQR"), ("ACQR", "CQR"), ("ACQR", "split-CP")]:
            diff = (gap[m1]-gap[m2]).dropna().values
            _, p = wilcoxon(diff)
            print(f"{m1:5} vs {m2:8} mean {diff.mean():+.4f}  p={p:.2e}  {m1}-better {np.mean(diff<0):.0%}  n={len(diff)}")

if __name__ == "__main__":
    main()
