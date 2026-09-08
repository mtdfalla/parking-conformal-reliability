#!/usr/bin/env python3
"""
EXP-014 — Lean E3 baselines (prior review: compare with SOTA of the same method characteristic).

Adds three baselines at the HEADLINE settings (Belgrade t+15 min, Birmingham t+60 min, 90% target,
delta target, seed 42, same splits/features as EXP-010/011):

  1. EnbPI      — reference implementation: MAPIE TimeSeriesRegressor(method="enbpi",
                  cv=BlockBootstrap). Residuals updated once per test day with matured observations
                  only (predictions for day k are issued before any day-k observation is used -> causal).
  2. AgACI-style— online EWA aggregation of delay-aware ACI experts over a gamma grid
                  {0.001,0.005,0.01,0.02,0.05,0.1,0.2}; weights from cumulative pinball loss of each
                  expert's bounds, using matured feedback only (same h-step delay as ACI). Labeled
                  "AgACI-style" in the paper (EWA, not the exact BOA of Zaffran et al. 2022).
  3. NGBoost    — parametric probabilistic baseline (Gaussian predictive distribution, no finite-sample
                  guarantee); central 90% interval from the predictive Normal. Stands in for the
                  Bayesian/parametric-UQ family (cf. Sensors-2025 BNN, DeepAR).

SPCI is cited but not run (adapting author code to the delay-aware multi-step protocol risks a
misimplemented-baseline strawman).

Output: 05_results/tables/2026-08-04-e3-{belgrade,birmingham}-per-facility.csv (+ digest).
Resumable per facility. Usage: python 2026-08-04-e3-baselines.py --dataset belgrade|birmingham
"""
from __future__ import annotations
import argparse, math, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from mapie.regression import TimeSeriesRegressor
from mapie.subsample import BlockBootstrap
from ngboost import NGBRegressor
from ngboost.distns import Normal
from scipy.stats import norm
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve(); ROOT = HERE.parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; DYN = 5.0; LVL = 0.90; AL = 1-LVL
GAMMAS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]
CFG = {"belgrade":  {"feat": "belgrade_features.parquet",  "hz": "y_t+15min", "h": 3, "steps_day": 288},
       "birmingham": {"feat": "birmingham_features.parquet", "hz": "y_t+60min", "h": 2, "steps_day": 20}}

def log(m): print(f"[e3] {m}", flush=True)
def cq_idx(n, a): return min(math.ceil((n+1)*(1-a)), n)

def aci_delayed_bounds(resid_cal, yhat, y, a, h, gamma, window=None):
    sc = list(resid_cal); al = a; window = window or len(resid_cal); n = len(y)
    lo = np.empty(n); hi = np.empty(n); rel = {}
    for i in range(n):
        for (r, err) in rel.pop(i, []):
            al = al + gamma*(a - err); sc.append(r)
        a_c = min(max(al, 1e-3), 1-1e-3)
        pool = np.asarray(sc[-window:]); m = len(pool)
        lv = min(1.0, cq_idx(m, a_c)/m)
        q = float(np.max(pool)) if lv >= 1 else float(np.quantile(pool, lv, method="higher"))
        lo[i] = yhat[i]-q; hi[i] = yhat[i]+q
        cov = (y[i] >= lo[i]) and (y[i] <= hi[i])
        rel.setdefault(i+h, []).append((abs(y[i]-yhat[i]), 0 if cov else 1))
    return lo, hi   # unclipped; clip at the end

def pinball(y, b, tau):
    d = y - b; return np.maximum(tau*d, (tau-1)*d)

def agaci_ewa(resid_cal, yhat, y, a, h, eta=0.01):
    """EWA over gamma grid, separate weights for lower (tau=a/2) and upper (tau=1-a/2) bounds.
    Weights at step i use only pinball losses of forecasts matured by step i (issued <= i-h)."""
    K = len(GAMMAS); n = len(y)
    LOs = np.empty((K, n)); HIs = np.empty((K, n))
    for k, g in enumerate(GAMMAS):
        LOs[k], HIs[k] = aci_delayed_bounds(resid_cal, yhat, y, a, h, g)
    lo = np.empty(n); hi = np.empty(n)
    Llo = np.zeros(K); Lhi = np.zeros(K)
    for i in range(n):
        wlo = np.exp(-eta*(Llo-Llo.min())); wlo /= wlo.sum()
        whi = np.exp(-eta*(Lhi-Lhi.min())); whi /= whi.sum()
        lo[i] = float(wlo@LOs[:, i]); hi[i] = float(whi@HIs[:, i])
        j = i-h+1                      # forecast at j matures at step j+h-1 < i+1 -> usable now
        if j >= 0:
            Llo += pinball(y[j], LOs[:, j], AL/2)
            Lhi += pinball(y[j], HIs[:, j], 1-AL/2)
    return lo, hi

def enbpi_mapie(X_tr, d_tr, X_te, occ_te, y_te, steps_day):
    est = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
    cv = BlockBootstrap(n_resamplings=30, n_blocks=10, overlapping=False, random_state=SEED)
    m = TimeSeriesRegressor(estimator=est, method="enbpi", cv=cv, agg_function="mean",
                            n_jobs=-1, random_state=SEED)
    m.fit(X_tr, d_tr)
    n = len(y_te); lo = np.empty(n); hi = np.empty(n)
    for s in range(0, n, steps_day):                     # day-chunked, causal updates
        e = min(s+steps_day, n)
        _, ps = m.predict(X_te[s:e], ensemble=True, confidence_level=LVL)
        lo[s:e] = occ_te[s:e] + ps[:, 0, 0]; hi[s:e] = occ_te[s:e] + ps[:, 1, 0]
        m.update(X_te[s:e], y_te[s:e] - occ_te[s:e], ensemble=True, confidence_level=LVL)
    return lo, hi

def ngboost_normal(X_tr, d_tr, X_te, occ_te):
    ng = NGBRegressor(Dist=Normal, n_estimators=300, learning_rate=0.03,
                      random_state=SEED, verbose=False)
    ng.fit(X_tr, d_tr)
    dist = ng.pred_dist(X_te)
    z = norm.ppf(1-AL/2)
    mu = dist.params["loc"]; sd = dist.params["scale"]
    return occ_te+mu-z*sd, occ_te+mu+z*sd

def winkler(y, lo, hi, a):
    w = hi-lo; s = w.copy(); b = y < lo; u = y > hi
    s[b] += (2/a)*(lo[b]-y[b]); s[u] += (2/a)*(y[u]-hi[u]); return float(np.mean(s))

def boot_ci(cov, B=500, block=20, seed=SEED):
    rng = np.random.default_rng(seed); n = len(cov); nb = max(1, n//block); picp = []
    for _ in range(B):
        st = rng.integers(0, n-block+1, size=nb)
        idx = np.concatenate([np.arange(s, s+block) for s in st])
        picp.append(cov[idx].mean())
    return float(np.percentile(picp, 5)), float(np.percentile(picp, 95))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True, choices=list(CFG))
    ap.add_argument("--budget", type=float, default=520.0)
    a = ap.parse_args(); cfg = CFG[a.dataset]
    df = pd.read_parquet(PROC/cfg["feat"])
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    HZ, H = cfg["hz"], cfg["h"]
    ds = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    dyn = sorted(ds[ds >= DYN].index)
    OUT = TAB/f"2026-08-04-e3-{a.dataset}-per-facility.csv"
    done = set(pd.read_csv(OUT).facility_id.unique()) if OUT.exists() else set()
    todo = [f for f in dyn if f not in done]
    log(f"{a.dataset} ({HZ}): {len(done)} done, {len(todo)} to do")
    t0 = time.time(); rows = []
    for fid in todo:
        if time.time()-t0 > a.budget: log("budget hit; save+exit"); break
        g = df[df.facility_id == fid].sort_values("timestamp").dropna(subset=["occupancy"]+FEAT+[HZ])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
        d_tr = tr[HZ].values-occ_tr; y_te = te[HZ].values
        X_tr = tr[FEAT].values; X_ca = ca[FEAT].values; X_te = te[FEAT].values
        rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
        rf.fit(X_tr, d_tr)
        yhat_te = occ_te+rf.predict(X_te)
        resid = np.abs(ca[HZ].values-(occ_ca+rf.predict(X_ca)))
        results = {}
        results["EnbPI"] = enbpi_mapie(X_tr, d_tr, X_te, occ_te, y_te, cfg["steps_day"])
        results["AgACI-style"] = agaci_ewa(resid, yhat_te, y_te, AL, H)
        results["NGBoost"] = ngboost_normal(X_tr, d_tr, X_te, occ_te)
        for meth, (lo, hi) in results.items():
            lo = np.maximum(lo, 0.0)
            p = float(np.mean((y_te >= lo) & (y_te <= hi)))
            clo, chi = boot_ci(((y_te >= lo) & (y_te <= hi)).astype(float))
            rows.append(dict(facility_id=fid, horizon=HZ, level=LVL, method=meth, PICP=p,
                             MPIW=float(np.mean(hi-lo)), Winkler=winkler(y_te, lo, hi, AL),
                             picp_lo=clo, picp_hi=chi))
        log(f"fac {fid} done ({time.time()-t0:.0f}s)")
    if rows:
        rd = pd.DataFrame(rows)
        if OUT.exists(): rd = pd.concat([pd.read_csv(OUT), rd], ignore_index=True)
        rd.to_csv(OUT, index=False)
    d = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["facility_id"])
    rem = [f for f in dyn if f not in set(d.facility_id.unique())]
    if rem: log(f"REMAINING {a.dataset}: {len(rem)}")
    else:
        log(f"ALL DONE {a.dataset}: {d.facility_id.nunique()} facilities")
        s = d.groupby("method").agg(mean_PICP=("PICP", "mean"), std_PICP=("PICP", "std"),
                                    mean_MPIW=("MPIW", "mean"), mean_Winkler=("Winkler", "mean"),
                                    frac_CI_target=("picp_lo", lambda x: np.nan)).round(4)
        at = d.groupby("method").apply(lambda x: float(np.mean((x.picp_lo <= LVL) & (LVL <= x.picp_hi))),
                                       include_groups=False).round(3)
        s["frac_CI_target"] = at
        print(s.to_string())

if __name__ == "__main__":
    main()
