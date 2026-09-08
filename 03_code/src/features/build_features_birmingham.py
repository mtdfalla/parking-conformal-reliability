#!/usr/bin/env python3
"""
Birmingham feature engineering (gap-aware) — parallel to Belgrade, adapted to 30-min daytime-only data.

Key correctness point (see 01_data/BIRMINGHAM_QC.md): the data is daytime-only (~07:00-16:30), so each
facility is reindexed to a CONTINUOUS 30-min grid over its span; night slots become NaN, so any lag or
target that would cross a night becomes NaN and is dropped. This guarantees no feature/target spans a gap.

Input : 01_data/processed/birmingham_long.parquet
Output: 01_data/processed/birmingham_features.parquet (+ report json)

Run: python build_features_birmingham.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

HERE=Path(__file__).resolve(); ROOT=HERE.parents[3]; PROC=ROOT/"01_data"/"processed"
IN=PROC/"birmingham_long.parquet"; OUT=PROC/"birmingham_features.parquet"

GRID="30min"; STEP=30
HORIZONS_MIN=[30,60,90]          # 1,2,3 steps
LAGS=[1,2,3,4,5,6]               # 30..180 min
ROLL=[3,6]                       # 90,180 min
MIN_RECORDS=500                  # exclude too-sparse facilities (8, 21)
TRAIN_FRAC, CALIB_FRAC = 10/18, 4/18

def log(m): print(f"[bham-feat] {m}")

def build_fac(g):
    g=g.set_index("timestamp").sort_index()
    # continuous 30-min grid over span; night slots -> NaN (no cross-night interpolation)
    full=pd.date_range(g.index.min().floor("30min"), g.index.max().ceil("30min"), freq=GRID)
    occ=g["occupancy"].resample(GRID).mean().reindex(full)
    occ=occ.interpolate("time", limit=1, limit_area="inside")   # only tiny within-day 1-step fills
    df=pd.DataFrame({"occupancy":occ})
    for L in LAGS: df[f"lag_{L*STEP}min"]=df["occupancy"].shift(L)
    for W in ROLL:
        r=df["occupancy"].shift(1).rolling(W)
        df[f"roll_mean_{W*STEP}min"]=r.mean(); df[f"roll_std_{W*STEP}min"]=r.std()
    for H in HORIZONS_MIN: df[f"y_t+{H}min"]=df["occupancy"].shift(-(H//STEP))
    return df.reset_index().rename(columns={"index":"timestamp"})

def main():
    long=pd.read_parquet(IN)
    long["occupancy"]=long["occupancy"].clip(lower=0)         # fix 12 negative rows
    counts=long.groupby("facility_id").size()
    keep=counts[counts>=MIN_RECORDS].index.tolist()
    excluded=sorted(set(counts.index)-set(keep))
    log(f"excluding sparse facilities {excluded}; keeping {len(keep)}")
    long=long[long.facility_id.isin(keep)]

    feats=[]
    for fid,g in long.groupby("facility_id"):
        f=build_fac(g[["timestamp","occupancy"]].copy())
        f["facility_id"]=fid; f["facility_name"]=g["facility_name"].iloc[0]
        feats.append(f)
    df=pd.concat(feats,ignore_index=True)

    ts=df["timestamp"]; mod=ts.dt.hour*60+ts.dt.minute
    df["tod_sin"]=np.sin(2*np.pi*mod/1440); df["tod_cos"]=np.cos(2*np.pi*mod/1440)
    df["dow"]=ts.dt.dayofweek; df["is_weekend"]=(df["dow"]>=5).astype(int)
    import holidays; uk=holidays.UnitedKingdom(subdiv="England", years=[2016])
    df["is_holiday"]=ts.dt.date.map(lambda d:int(d in uk))

    tmin,tmax=df.timestamp.min(),df.timestamp.max(); span=tmax-tmin
    te=tmin+span*TRAIN_FRAC; ce=tmin+span*(TRAIN_FRAC+CALIB_FRAC)
    df["split"]=np.where(df.timestamp<=te,"train",np.where(df.timestamp<=ce,"calibration","test"))

    fcols=[c for c in df.columns if c.startswith(("lag_","roll_"))]+["tod_sin","tod_cos","dow","is_weekend","is_holiday"]
    tcols=[c for c in df.columns if c.startswith("y_t+")]
    before=len(df); df=df.dropna(subset=fcols+tcols).reset_index(drop=True)
    log(f"dropped {before-len(df)} rows (warm-up / night-crossing / edges); kept {len(df)}")

    df=df[["timestamp","facility_id","facility_name","occupancy"]+fcols+tcols+["split"]]
    df.to_parquet(OUT,index=False)
    rep={"rows":int(len(df)),"facilities":int(df.facility_id.nunique()),"excluded":excluded,
         "grid":GRID,"horizons_min":HORIZONS_MIN,"feature_cols":fcols,"target_cols":tcols,
         "rows_per_split":{k:int(v) for k,v in df.groupby("split").size().items()},
         "any_nan":bool(df[fcols+tcols].isna().any().any()),
         "time_min":str(df.timestamp.min()),"time_max":str(df.timestamp.max())}
    json.dump(rep,open(PROC/"birmingham_features_report.json","w"),indent=2)
    log("report: "+json.dumps(rep,indent=2)); log("DONE.")

if __name__=="__main__": main()
