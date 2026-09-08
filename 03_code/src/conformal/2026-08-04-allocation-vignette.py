#!/usr/bin/env python3
"""
EXP-015 — Illustrative risk-aware allocation vignette (Belgrade, t+15 min, 90% ACQR intervals).

Purpose (answers a prior review note that allocation references carried more narrative
weight than the work supported): a contained, seeded, worked case showing that calibrated intervals
change an allocation decision — NOT a calibrated simulator (per D-010's scope pushback).

Setup
  * Facilities: 21 dynamic Belgrade facilities with coordinates; proxy capacity per facility =
    the maximum occupancy observed over the full record (an illustrative operational proxy;
    reliable posted capacities are unavailable for Belgrade).
  * Forecasts: change-anchored RF (seed 42, EXP-010 protocol) point forecast yhat(t+15) per facility;
    ACQR 90% intervals (delay-aware, EXP-011 protocol) give an upper occupancy bound U(t+15).
  * Demand: R=600 synthetic requests over the two weekday afternoons in the test window
    (Mar 20-21, 12:00-19:00), arrival times uniform, seed 42. Destinations follow a 65/35 mixture:
    65% concentrated (sigma ~350 m) around the tight downtown cluster (facilities 8/9/10/23, which
    run at >=90% of proxy capacity for much of these afternoons - demand concentrates exactly where
    parking is scarce), 35% uniform over the network bounding box. Each request is assigned at
    time t; the driver arrives at t+15.
  * Policies (both greedy, nearest-first over facilities ranked by haversine distance from the
    destination, safety margin s = 1 space):
      POINT:    assign the nearest facility with predicted free spaces cap - yhat >= s.
      INTERVAL: assign the nearest facility whose WORST-CASE free spaces cap - U >= s; facilities
                whose interval cannot guarantee s spaces are skipped (the trust/abstain rule
                acting inside allocation).
  * Outcome at arrival: overflow if actual free spaces cap - y_true(t+15) < s (driver reaches a
    full facility). Metrics: overflow rate, assignment rate, mean/p90 distance to assigned facility.
  * Requests are independent (no queueing/interaction/rerouting) - stated limitation; this is an
    illustrative decision vignette, not a calibrated simulator (per D-010 scope).

Output: 05_results/tables/2026-08-04-allocation-vignette.csv, figure
        05_results/figures/2026-08-04-allocation-vignette.png
"""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"; FIG = ROOT/"05_results"/"figures"
SEED = 42; DYN = 5.0; GAMMA = 0.05; HZ = "y_t+15min"; H = 3; AL = 0.10
R_REQ = 600; SAFETY = 1

def cq_idx(n, a): return min(math.ceil((n+1)*(1-a)), n)

def acqr_delayed(E_cal, qlo_te, qhi_te, y_te, a, h, gamma=GAMMA, window=None):
    sc = list(E_cal); al = a; window = window or len(E_cal); n = len(y_te)
    lo = np.empty(n); hi = np.empty(n); rel = {}
    for i in range(n):
        for (r, err) in rel.pop(i, []):
            al = al + gamma*(a-err); sc.append(r)
        a_c = min(max(al, 1e-3), 1-1e-3)
        pool = np.asarray(sc[-window:]); m = len(pool)
        lv = min(1.0, cq_idx(m, a_c)/m)
        q = float(np.max(pool)) if lv >= 1 else float(np.quantile(pool, lv, method="higher"))
        lo_raw = qlo_te[i]-q; hi[i] = qhi_te[i]+q; lo[i] = max(lo_raw, 0.0)
        cov = (y_te[i] >= lo_raw) and (y_te[i] <= hi[i])
        rel.setdefault(i+h, []).append((max(qlo_te[i]-y_te[i], y_te[i]-qhi_te[i]), 0 if cov else 1))
    return lo, hi

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2-lat1), np.radians(lon2-lon1)
    a = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

# ---------- forecasts + intervals per facility ----------
df = pd.read_parquet(PROC/"belgrade_features.parquet")
df["ts"] = pd.to_datetime(df.timestamp)
FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
       ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
coords = pd.read_parquet(PROC/"facility_coords.parquet").set_index("facility_id")
ds = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
dyn = sorted(set(ds[ds >= DYN].index) & set(coords.index))
cap = df.groupby("facility_id").occupancy.max()  # proxy capacity = historical max occupancy (exact)

panel = {}   # fid -> DataFrame indexed by ts with yhat, U, y_true
for fid in dyn:
    g = df[df.facility_id == fid].sort_values("ts").dropna(subset=["occupancy"]+FEAT+[HZ])
    tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
    occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
    d_tr = tr[HZ].values-occ_tr; y_ca = ca[HZ].values; y_te = te[HZ].values
    rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
    rf.fit(tr[FEAT].values, d_tr)
    yhat_te = occ_te+rf.predict(te[FEAT].values)
    glo = HistGradientBoostingRegressor(loss="quantile", quantile=AL/2, max_iter=100, random_state=SEED)
    ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1-AL/2, max_iter=100, random_state=SEED)
    glo.fit(tr[FEAT].values, d_tr); ghi.fit(tr[FEAT].values, d_tr)
    E_cal = np.maximum((occ_ca+glo.predict(ca[FEAT].values))-y_ca,
                       y_ca-(occ_ca+ghi.predict(ca[FEAT].values)))
    qlo_te = occ_te+glo.predict(te[FEAT].values); qhi_te = occ_te+ghi.predict(te[FEAT].values)
    lo, hi = acqr_delayed(E_cal, qlo_te, qhi_te, y_te, AL, H)
    panel[fid] = pd.DataFrame({"ts": te.ts.values, "yhat": yhat_te, "U": hi, "y_true": y_te}).set_index("ts")
    print(f"[vign] fac {fid} ready", flush=True)

# ---------- synthetic demand ----------
rng = np.random.default_rng(SEED)
lat0, lat1 = coords.loc[dyn].latitude.min(), coords.loc[dyn].latitude.max()
lon0, lon1 = coords.loc[dyn].longitude.min(), coords.loc[dyn].longitude.max()
mlat, mlon = 0.15*(lat1-lat0), 0.15*(lon1-lon0)
# demand concentrates where parking is scarce (tight downtown cluster) - 65/35 mixture
TIGHT = [f for f in (8, 9, 10, 23) if f in dyn]
SIG = 0.0035  # ~350 m
common_ts = panel[dyn[0]].index
slots = [t for t in common_ts
         if pd.Timestamp(t).day in (20, 21) and 12 <= pd.Timestamp(t).hour < 19
         and all(t in panel[f].index for f in dyn)]
req_ts = rng.choice(pd.Index(slots).values, size=R_REQ, replace=True)
hot = rng.random(R_REQ) < 0.65
anchor = rng.choice(TIGHT, size=R_REQ)
req_lat = np.where(hot, coords.loc[anchor].latitude.values + rng.normal(0, SIG, R_REQ),
                   rng.uniform(lat0-mlat, lat1+mlat, R_REQ))
req_lon = np.where(hot, coords.loc[anchor].longitude.values + rng.normal(0, SIG, R_REQ),
                   rng.uniform(lon0-mlon, lon1+mlon, R_REQ))

def run_policy(kind):
    recs = []
    for k in range(R_REQ):
        t = req_ts[k]
        dists = {f: haversine(req_lat[k], req_lon[k], coords.loc[f].latitude, coords.loc[f].longitude)
                 for f in dyn}
        assigned = None
        for f in sorted(dyn, key=lambda f: dists[f]):
            row = panel[f].loc[t]
            free_pred = cap[f] - (row.yhat if kind == "POINT" else row.U)
            if free_pred >= SAFETY:
                assigned = f; break
        if assigned is None:
            recs.append(dict(req=k, policy=kind, assigned=np.nan, dist=np.nan, overflow=np.nan))
            continue
        row = panel[assigned].loc[t]
        recs.append(dict(req=k, policy=kind, assigned=assigned, dist=dists[assigned],
                         overflow=int(cap[assigned] - row.y_true < SAFETY)))
    return pd.DataFrame(recs)

res = pd.concat([run_policy("POINT"), run_policy("INTERVAL")], ignore_index=True)
summ = res.groupby("policy").agg(
    assigned_rate=("assigned", lambda x: float(x.notna().mean())),
    overflow_rate=("overflow", "mean"),
    mean_dist_km=("dist", "mean"),
    p90_dist_km=("dist", lambda x: float(np.nanpercentile(x.dropna(), 90)))).round(4)
summ["n_requests"] = R_REQ
summ.to_csv(TAB/"2026-08-04-allocation-vignette.csv")
res.to_csv(TAB/"2026-08-04-allocation-vignette-requests.csv", index=False)
print(summ.to_string())

# ---------- figure ----------
fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
pol = ["POINT", "INTERVAL"]; col = {"POINT": "#C00000", "INTERVAL": "#1F4E79"}
ov = [summ.loc[p].overflow_rate*100 for p in pol]
dk = [summ.loc[p].mean_dist_km for p in pol]
axes[0].bar(pol, ov, color=[col[p] for p in pol], width=0.55)
axes[0].set_ylabel("overflow rate (%)"); axes[0].set_title("Requests sent to a full facility")
for i, v in enumerate(ov): axes[0].text(i, v+0.08, f"{v:.1f}%", ha="center")
axes[1].bar(pol, dk, color=[col[p] for p in pol], width=0.55)
axes[1].set_ylabel("mean distance to assigned facility (km)"); axes[1].set_title("Detour cost")
for i, v in enumerate(dk): axes[1].text(i, v+0.02, f"{v:.2f}", ha="center")
fig.suptitle("Risk-aware allocation vignette — point vs. interval policy (Belgrade, t+15, 90% ACQR)", fontsize=10)
fig.tight_layout(); fig.savefig(FIG/"2026-08-04-allocation-vignette.png", dpi=200)
print("figure saved")
