#!/usr/bin/env python3
"""
EXP-018 — Is the multi-step under-coverage of delay-aware ACI a tuning artifact or intrinsic?
R-Phase 3 gate diagnostic (D-014).

EXP-017 found that corrected ACI/ACQR under-cover, and that the shortfall grows monotonically with the
feedback delay h in BOTH cities (Belgrade 0.895/0.886/0.872 at h=1/3/6; Birmingham 0.894/0.888/0.883 at
h=1/2/3) while split-CP and CQR, which have no feedback loop, stay flat at ~0.90.

This script asks whether the step size gamma or the score-window length can buy the coverage back, and at
what cost in width. If no setting reaches ~0.90 without inflating intervals past CQR, the shortfall is
structural -- which is what Wang & Hyndman (2024, AcMCP) prove: the finite-sample coverage error bound of
online conformal methods INCREASES WITH THE FORECAST HORIZON.

Usage: CITY=belgrade python 2026-09-02-delay-sensitivity.py --facilities 8
       (the D-018 low-information exclusion is applied on top of --facilities; see main())
Output: 05_results/tables/2026-09-02-delay-sensitivity.csv
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
SEED = 42; AL = 0.10
GAMMAS = [0.002, 0.005, 0.01, 0.02, 0.05, 0.10]
WINDOW_MULT = [1.0]
HZ_BY_CITY = {"belgrade":   [("y_t+5min",5,1), ("y_t+15min",15,3), ("y_t+30min",30,6)],
              "birmingham": [("y_t+30min",30,1), ("y_t+60min",60,2), ("y_t+90min",90,3)]}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--facilities", type=int, default=10)
    args = ap.parse_args()
    CITY = __import__("os").environ.get("CITY","belgrade")
    df = pd.read_parquet(PROC/f"{CITY}_features_v2.parquet")
    HZ = HZ_BY_CITY[CITY]
    FEAT = [c for c in df.columns if c.startswith(("lag_","roll_"))] + \
           ["tod_sin","tod_cos","dow","is_weekend","is_holiday"]
    sd = df[df.split=="train"].groupby("facility_id")["occupancy"].std()
    dyn = sorted(sd[sd>=5].index)[:args.facilities]
    # 2026-09-05 (revision 45, D-024 option 1): APPLY D-018. This script predates the exclusion, so its
    # population still contained the X08 dead sensor (facility 8) while every other reported number in
    # the paper excludes it. The rule lives in core.py and nowhere else (B9) and is evaluated on EACH
    # SCORED test window, per D-018; a facility excluded in any scored window is excluded from the whole
    # table, so the population does not vary by horizon. Measured: Belgrade 8 -> 7 facilities (8 dropped
    # in all three windows); Birmingham excludes nothing and must not move -- that is the negative
    # control. This RETIRES the clause "gamma = 0.005 restores 0.90 at every horizon": on the excluded
    # base it reaches 0.894-0.896. See DECISIONS_LOG D-024 and EXP-036.
    excl = set()
    for _hz, _hmin, _hs in HZ:
        _te = df[(df.split=="test") & df[f"use_{_hmin}"] & df.facility_id.isin(dyn)]
        excl |= set(core.low_information_facilities(_te))
    if excl:
        print(f"[sens] D-018 exclusion: dropping low-information facilities {sorted(excl)}", flush=True)
    dyn = [f for f in dyn if f not in excl]

    rows=[]; t0=time.time()
    for hz, hmin, hsteps in HZ:
        for fid in dyn:
            g = df[(df.facility_id==fid) & df[f"use_{hmin}"]].sort_values("timestamp")\
                  .dropna(subset=["occupancy"]+FEAT+[hz])
            tr,ca,te = g[g.split=="train"], g[g.split=="calibration"], g[g.split=="test"]
            rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                                       random_state=SEED).fit(tr[FEAT].values,
                                                              tr[hz].values-tr.occupancy.values)
            yhc = ca.occupancy.values + rf.predict(ca[FEAT].values)
            resid = np.abs(ca[hz].values - yhc)
            yht = te.occupancy.values + rf.predict(te[FEAT].values); yt = te[hz].values
            # reference: split-CP has no feedback loop, so it is the "no delay effect" control
            slo, shi = core.split_conformal_interval(resid, yht, AL, clip_low=None)
            p,m,w = core.interval_metrics(yt, slo, shi, AL)
            rows.append(dict(horizon=hz, h=hsteps, facility_id=fid, method="split-CP",
                             gamma=np.nan, window_mult=np.nan, PICP=p, MPIW=m, Winkler=w))
            for gm in GAMMAS:
                for wm in WINDOW_MULT:
                    win = max(50, int(len(resid)*wm))
                    lo,hi = core.adaptive_conformal_stream(resid, yht, yht, yt, AL, hsteps,
                                                           gamma=gm, window=win, clip_low=None)
                    p,m,w = core.interval_metrics(yt, lo, hi, AL)
                    rows.append(dict(horizon=hz, h=hsteps, facility_id=fid, method="ACI",
                                     gamma=gm, window_mult=wm, PICP=p, MPIW=m, Winkler=w))
        print(f"[sens] {hz} done ({time.time()-t0:.0f}s)", flush=True)
    r = pd.DataFrame(rows); r.to_csv(TAB/f"2026-09-02-delay-sensitivity-{CITY}.csv", index=False)

    print(f"\n=== {CITY}, 90%, mean over facilities.  Target PICP = 0.900 ===")
    for hz,h,_ in [(a,c,None) for a,b,c in HZ]:
        sub = r[r.horizon==hz]
        sp = sub[sub.method=="split-CP"]
        print(f"\n{hz}  (h = {h} steps)   split-CP reference: PICP {sp.PICP.mean():.4f}  "
              f"MPIW {sp.MPIW.mean():.2f}  Winkler {sp.Winkler.mean():.2f}")
        a = sub[sub.method=="ACI"]
        piv = a.pivot_table(index="gamma", columns="window_mult", values="PICP")
        wid = a.pivot_table(index="gamma", columns="window_mult", values="MPIW")
        print("   PICP by gamma (rows) x window multiple (cols):")
        print(piv.round(4).to_string())
        print("   MPIW:")
        print(wid.round(2).to_string())
    print(f"\ntotal {time.time()-t0:.0f}s")

if __name__=="__main__": main()
