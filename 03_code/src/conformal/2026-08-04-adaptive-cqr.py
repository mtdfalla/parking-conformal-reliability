#!/usr/bin/env python3
"""
EXP-011 — Adaptive CQR (ACQR): ACI layered on CQR nonconformity scores, delay-aware (no lookahead).

Motivation (prior peer review): ACI wins per-facility coverage consistency but loses to CQR on
Winkler in 5/6 rows; CQR wins efficiency but is per-facility unreliable. ACQR composes the two:
CQR's heteroscedastic quantile band supplies the shape; ACI's online alpha update supplies per-facility
long-run coverage tracking. Nonconformity is the CQR score E_i = max(qlo_i - y_i, y_i - qhi_i); the
adaptive quantile q_t of recent scores is added symmetrically to the band. Feedback (score + coverage
indicator) for the forecast issued at step i is released only at step i+h (delay-aware), per facility
and horizon. Lower bound clipped at 0. Seed 42 throughout — identical protocol to EXP-010.

Usage: python 2026-08-04-adaptive-cqr.py --dataset belgrade|birmingham
Resumable per facility. Outputs 05_results/tables/2026-08-04-acqr-<dataset>-per-facility.csv
"""
from __future__ import annotations
import argparse, math, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

HERE = Path(__file__).resolve(); ROOT = HERE.parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; DYN = 5.0; GAMMA = 0.05
LEVELS = [0.90, 0.95]
CFG = {"belgrade":  {"feat": "belgrade_features.parquet",
                     "H": [("y_t+5min", 1), ("y_t+15min", 3), ("y_t+30min", 6)]},
       "birmingham": {"feat": "birmingham_features.parquet",
                      "H": [("y_t+30min", 1), ("y_t+60min", 2), ("y_t+90min", 3)]}}

def log(m): print(f"[acqr] {m}", flush=True)
def cq_idx(n, a): return min(math.ceil((n+1)*(1-a)), n)

def acqr_delayed(E_cal, qlo_te, qhi_te, y_te, a, h, gamma=GAMMA, window=None):
    """ACI on CQR scores with h-step delayed feedback. Returns (lo, hi)."""
    sc = list(E_cal); al = a; window = window or len(E_cal); n = len(y_te)
    lo = np.empty(n); hi = np.empty(n); rel = {}
    for i in range(n):
        for (r, err) in rel.pop(i, []):            # delayed feedback becomes available now
            al = al + gamma*(a - err); sc.append(r)
        a_c = min(max(al, 1e-3), 1-1e-3)
        pool = np.asarray(sc[-window:]); m = len(pool)
        lv = min(1.0, cq_idx(m, a_c)/m)
        q = float(np.max(pool)) if lv >= 1 else float(np.quantile(pool, lv, method="higher"))
        lo_raw = qlo_te[i] - q; hi[i] = qhi_te[i] + q
        lo[i] = max(lo_raw, 0.0)
        cov = (y_te[i] >= lo_raw) and (y_te[i] <= hi[i])   # coverage vs unclipped bound (as EXP-010)
        E_i = max(qlo_te[i] - y_te[i], y_te[i] - qhi_te[i])
        rel.setdefault(i+h, []).append((E_i, 0 if cov else 1))
    return lo, hi

def winkler(y, lo, hi, a):
    w = hi - lo; s = w.copy(); b = y < lo; u = y > hi
    s[b] += (2/a)*(lo[b]-y[b]); s[u] += (2/a)*(y[u]-hi[u]); return float(np.mean(s))

def mets(y, lo, hi, a):
    return float(np.mean((y >= lo) & (y <= hi))), float(np.mean(hi-lo)), winkler(y, lo, hi, a)

def boot_ci(cov, B=500, block=20, seed=SEED):
    rng = np.random.default_rng(seed); n = len(cov); nb = max(1, n//block); picp = []
    for _ in range(B):
        starts = rng.integers(0, n-block+1, size=nb)
        idx = np.concatenate([np.arange(s, s+block) for s in starts])
        picp.append(cov[idx].mean())
    return float(np.percentile(picp, 5)), float(np.percentile(picp, 95))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dataset", required=True, choices=list(CFG))
    ap.add_argument("--budget", type=float, default=500.0)
    a = ap.parse_args(); cfg = CFG[a.dataset]
    df = pd.read_parquet(PROC/cfg["feat"])
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    ds = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    dyn = sorted(ds[ds >= DYN].index)
    PER = TAB/f"2026-08-04-acqr-{a.dataset}-per-facility.csv"
    done = set(pd.read_csv(PER).facility_id.unique()) if PER.exists() else set()
    todo = [f for f in dyn if f not in done]
    log(f"{a.dataset}: {len(done)} done, {len(todo)} to do")
    t0 = time.time(); rows = []
    for fid in todo:
        if time.time()-t0 > a.budget: log("budget hit; save+exit"); break
        g = df[df.facility_id == fid].sort_values("timestamp")
        g = g.dropna(subset=["occupancy"]+FEAT+[h for h, _ in cfg["H"]])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        for hz, hsteps in cfg["H"]:
            occ_tr = tr["occupancy"].values; occ_ca = ca["occupancy"].values; occ_te = te["occupancy"].values
            d_tr = tr[hz].values - occ_tr
            y_ca = ca[hz].values; y_te = te[hz].values
            for lvl in LEVELS:
                al = 1 - lvl
                glo = HistGradientBoostingRegressor(loss="quantile", quantile=al/2, max_iter=100, random_state=SEED)
                ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1-al/2, max_iter=100, random_state=SEED)
                glo.fit(tr[FEAT].values, d_tr); ghi.fit(tr[FEAT].values, d_tr)
                qlo_ca = occ_ca + glo.predict(ca[FEAT].values); qhi_ca = occ_ca + ghi.predict(ca[FEAT].values)
                E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)
                qlo_te = occ_te + glo.predict(te[FEAT].values); qhi_te = occ_te + ghi.predict(te[FEAT].values)
                lo, hi = acqr_delayed(E_cal, qlo_te, qhi_te, y_te, al, hsteps)
                p, m, w = mets(y_te, lo, hi, al)
                rec = dict(facility_id=fid, horizon=hz, level=lvl, method="ACQR", PICP=p, MPIW=m, Winkler=w)
                if abs(lvl-0.90) < 1e-9:
                    clo, chi = boot_ci(((y_te >= lo) & (y_te <= hi)).astype(float))
                    rec["picp_lo"] = clo; rec["picp_hi"] = chi
                rows.append(rec)
        log(f"fac {fid} done")
    if rows:
        rd = pd.DataFrame(rows)
        if PER.exists(): rd = pd.concat([pd.read_csv(PER), rd], ignore_index=True)
        rd.to_csv(PER, index=False)
    per = pd.read_csv(PER) if PER.exists() else pd.DataFrame(columns=["facility_id"])
    remaining = [f for f in dyn if f not in set(per.facility_id.unique())]
    if remaining: log(f"REMAINING {a.dataset}: {len(remaining)}")
    else:
        log(f"ALL DONE {a.dataset}: {per.facility_id.nunique()} facilities")
        s = per.groupby(["horizon", "level"]).agg(mean_PICP=("PICP", "mean"), std_PICP=("PICP", "std"),
                                                  mean_MPIW=("MPIW", "mean"), mean_Winkler=("Winkler", "mean")).round(4)
        print(s.to_string())
        at = per[per.level == 0.90].groupby("horizon").apply(
            lambda x: float(np.mean((x.picp_lo <= 0.90) & (0.90 <= x.picp_hi))), include_groups=False)
        print("frac facilities with 90% bootstrap CI containing target:"); print(at.round(3).to_string())

if __name__ == "__main__":
    main()
