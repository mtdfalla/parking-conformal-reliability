#!/usr/bin/env python3
"""Facility 8 (X08, the dead sensor) is the ONLY facility whose AgACI-style width moved when the E3 arm
was regenerated (EXP-033). This probe establishes what it is and what it is not. It contributes to NO
reported number, and facility 8 enters no reported number either (D-018).

It runs the RandomForest -> residuals -> `agaci_ewa` path for facility 8 and records the resulting MPIW
plus the number of EXACT ties between the outcome and an expert's interval bound. `fit_ngboost` is never
called, so the 2026-09-05 reseed never executes in this process: any variation observed here exists
INDEPENDENTLY of that change. Append-only, one row per invocation, so repeated calls accumulate the
across-process evidence that a single call cannot give.
"""
from __future__ import annotations
import importlib.util, os, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "e3", ROOT / "03_code" / "src" / "conformal" / "2026-09-03-e3-baselines.py")
e3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e3)
FID = 8
OUT = ROOT / "05_results" / "tables" / "2026-09-05-agaci-x08-bistability-probe.csv"

df, feats, cfg, src = e3.load("belgrade", "A3_v2_daychunk")
hz, h = cfg["hz"], cfg["h"]
tr, ca, te = e3.facility_frame(df, feats, FID, hz)
X_tr, d_tr = tr[feats].values, tr[hz].values - tr.occupancy.values
X_ca, X_te = ca[feats].values, te[feats].values
y_te = te[hz].values.astype(float); y_ca = ca[hz].values.astype(float)

rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=e3.SEED)
rf.fit(X_tr, d_tr)
yhat = te.occupancy.values + rf.predict(X_te)
resid = np.abs(y_ca - (ca.occupancy.values + rf.predict(X_ca)))

# exact ties inside the EXPERT streams the EWA aggregates -- the candidate mechanism: on a series that
# takes two exact values, a coverage indicator `y >= lo` can sit exactly ON the bound, so a 1e-14
# perturbation of the forecast flips the indicator, which changes the ACI alpha trajectory from that
# step onward and moves the aggregate by far more than the perturbation.
ties = 0
for g in e3.AGACI_GAMMAS:
    lo_k, hi_k = e3.core.adaptive_conformal_stream(resid, yhat, yhat, y_te, e3.AL, h,
                                                   gamma=g, clip_low=None)
    ties += int(np.sum(y_te == np.asarray(lo_k)) + np.sum(y_te == np.asarray(hi_k)))

lo, hi = e3.agaci_ewa(resid, yhat, y_te, e3.AL, h)
lo = np.maximum(np.asarray(lo, float), 0.0)
picp, mpiw, wink = e3.core.interval_metrics(y_te, lo, np.asarray(hi, float), e3.AL)

row = dict(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), pid=os.getpid(), facility_id=FID,
           PICP=picp, MPIW=mpiw, Winkler=wink, exact_ties_expert_bounds=ties,
           ngboost_fit_called=False,
           note="archived 30.905034097 / regenerated 30.905102818")
rd = pd.DataFrame([row])
if OUT.exists():
    rd = pd.concat([pd.read_csv(OUT), rd], ignore_index=True)
rd.to_csv(OUT, index=False)
print(f"pid={os.getpid()}  MPIW={mpiw:.9f}  PICP={picp:.10f}  exact ties on expert bounds = {ties}")
