#!/usr/bin/env python3
"""Why does AgACI-style's MPIW move at facility 8 and nowhere else? Contributes to NO reported number.

The reseed (EXP-033) is applied INSIDE `fit_ngboost`, which runs strictly AFTER `agaci_ewa` in the same
facility iteration, so it cannot logically reach AgACI. This probe tests that empirically instead of
asserting it: it recomputes the RandomForest -> residuals -> `agaci_ewa` path for one facility TWICE in
one process, and then once more with `n_jobs=1`, all under the CURRENT (fixed) code.

  - If the two `n_jobs=-1` runs differ, the movement is run-to-run thread-reduction noise (A8) amplified
    by the facility, and the reseed is exonerated.
  - If they are identical and only the n_jobs=1 arm differs, the mechanism is still the reduction order.
  - If everything is identical, the archived-vs-regenerated difference is systematic and must be
    explained before anything is published.
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "03_code" / "src" / "conformal"
spec = importlib.util.spec_from_file_location("e3", CONF / "2026-09-03-e3-baselines.py")
e3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e3)

FID = int(sys.argv[1]) if len(sys.argv) > 1 else 8
df, feats, cfg, src = e3.load("belgrade", "A3_v2_daychunk")
hz, h = cfg["hz"], cfg["h"]
tr, ca, te = e3.facility_frame(df, feats, FID, hz)
X_tr, d_tr = tr[feats].values, tr[hz].values - tr.occupancy.values
X_ca, X_te = ca[feats].values, te[feats].values
y_te = te[hz].values.astype(float)
y_ca = ca[hz].values.astype(float)


def arm(n_jobs):
    rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=n_jobs,
                               random_state=e3.SEED)
    rf.fit(X_tr, d_tr)
    yhat = te.occupancy.values + rf.predict(X_te)
    resid = np.abs(y_ca - (ca.occupancy.values + rf.predict(X_ca)))
    lo, hi = e3.agaci_ewa(resid, yhat, y_te, e3.AL, h)
    lo = np.maximum(np.asarray(lo, float), 0.0)
    picp, mpiw, wink = e3.interval_metrics(y_te, lo, np.asarray(hi, float), e3.AL) \
        if hasattr(e3, "interval_metrics") else e3.core.interval_metrics(
            y_te, lo, np.asarray(hi, float), e3.AL)
    return dict(yhat=yhat, resid=resid, PICP=picp, MPIW=mpiw, Winkler=wink)


a1 = arm(-1); a2 = arm(-1); a3 = arm(1)
def mx(x, y): return float(np.max(np.abs(x - y)))
rows = [
    dict(contrast="n_jobs=-1 run 1 vs run 2, same process", facility_id=FID,
         max_abs_yhat=mx(a1["yhat"], a2["yhat"]), max_abs_resid=mx(a1["resid"], a2["resid"]),
         dPICP=abs(a1["PICP"] - a2["PICP"]), dMPIW=abs(a1["MPIW"] - a2["MPIW"]),
         dWinkler=abs(a1["Winkler"] - a2["Winkler"])),
    dict(contrast="n_jobs=-1 vs n_jobs=1", facility_id=FID,
         max_abs_yhat=mx(a1["yhat"], a3["yhat"]), max_abs_resid=mx(a1["resid"], a3["resid"]),
         dPICP=abs(a1["PICP"] - a3["PICP"]), dMPIW=abs(a1["MPIW"] - a3["MPIW"]),
         dWinkler=abs(a1["Winkler"] - a3["Winkler"])),
]
out = ROOT / "05_results" / "tables" / "2026-09-05-agaci-x08-amplification-probe.csv"
rd = pd.DataFrame(rows)
if out.exists():
    rd = pd.concat([pd.read_csv(out), rd], ignore_index=True)
rd.to_csv(out, index=False)
print(pd.DataFrame(rows).to_string(index=False))
print(f"\nMPIW(run1) = {a1['MPIW']:.9f}   MPIW(run2) = {a2['MPIW']:.9f}   "
      f"MPIW(1 thread) = {a3['MPIW']:.9f}")
