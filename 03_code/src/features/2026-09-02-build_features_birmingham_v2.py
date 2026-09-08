#!/usr/bin/env python3
"""
Birmingham feature engineering — v2, SESSION-SAFE AND CAUSALLY CORRECTED (R-Phase 1, D-014).

Supersedes `build_features_birmingham.py`. Fixes audit issues S02 / X01 (cross-night construction) and
S01 (split-boundary target leakage).

THE DEFECT THIS FIXES (measured on the v1 output, 2026-09-02)
-------------------------------------------------------------
v1 built ONE continuous 30-min grid across the whole multi-month span (v1 lines 34-36) and then called
`interpolate("time", limit=1, limit_area="inside")`. With `limit=1`, pandas fills the FIRST NaN of every
run — including the first slot after closing time, which is interpolated between the last observation of
the day and THE NEXT MORNING'S first observation. Consequences measured against the real observation grid:

  * 4,849 / 19,429 retained rows (25.0%) had an interpolated, unobserved occupancy anchor;
  * 6,351 rows (32.7%) had an interpolated t+90 target;
  * of those, 1,942 rows (10.0% of the whole Birmingham sample) had a t+90 target interpolated ACROSS A
    NIGHT — directly falsifying the manuscript's "feature construction is gap-aware so that no input or
    target spans a night".

WHAT CHANGED vs v1
------------------
1. **Session-grouped resampling.** Resample and interpolate WITHIN each facility x operating-day session
   only. Nothing is ever interpolated across a session boundary, by construction rather than by relying on
   `limit=1` and a later `dropna`.
2. **Session identity carried on every row** (`session_id`), so integrity tests can assert that a row's
   lags, anchor and target all belong to the same session.
3. **Explicit target timestamps + same-split constraint + boundary embargo**, identical in form to the
   Belgrade v2 builder (`use_{H} = split_ok_{H} & embargo_ok_{H}`).
4. **Interpolation provenance** (`occ_interpolated`, `target_interpolated_{H}`) so the rate is reportable.

UNCHANGED: 30-min grid, horizons, lags, rolling windows, calendar features, MIN_RECORDS exclusion,
negative clipping, split fractions.

Input : 01_data/processed/birmingham_long.parquet
Output: 01_data/processed/birmingham_features_v2.parquet (+ report json). v1 file NOT modified.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd

HERE=Path(__file__).resolve(); ROOT=HERE.parents[3]; PROC=ROOT/"01_data"/"processed"
IN=PROC/"birmingham_long.parquet"; OUT=PROC/"birmingham_features_v2.parquet"

GRID="30min"; STEP=30
HORIZONS_MIN=[30,60,90]
LAGS=[1,2,3,4,5,6]
ROLL=[3,6]
MIN_RECORDS=500
TRAIN_FRAC, CALIB_FRAC = 10/18, 4/18
EMBARGO=True
MAX_INTRA_SESSION_FILL=1     # steps; only tiny within-session gaps are filled

def log(m): print(f"[bham-feat-v2] {m}", flush=True)

def build_session(s: pd.DataFrame, fid, day) -> pd.DataFrame:
    """Resample/interpolate strictly inside one facility-day session."""
    s = s.set_index("timestamp").sort_index()
    lo = s.index.min().floor(GRID); hi = s.index.max().ceil(GRID)
    if hi <= lo: return pd.DataFrame()
    grid = pd.date_range(lo, hi, freq=GRID)
    occ_raw = s["occupancy"].resample(GRID).mean().reindex(grid)
    observed = occ_raw.notna()
    # interpolation cannot reach outside this session: the series ends at the session edges
    occ = occ_raw.interpolate("time", limit=MAX_INTRA_SESSION_FILL, limit_area="inside")
    df = pd.DataFrame({"occupancy": occ, "occ_observed": observed})
    for L in LAGS: df[f"lag_{L*STEP}min"] = df["occupancy"].shift(L)
    for W in ROLL:
        r = df["occupancy"].shift(1).rolling(W)
        df[f"roll_mean_{W*STEP}min"] = r.mean(); df[f"roll_std_{W*STEP}min"] = r.std()
    for H in HORIZONS_MIN:
        df[f"y_t+{H}min"] = df["occupancy"].shift(-(H//STEP))
        _sh = df["occ_observed"].shift(-(H//STEP))
        df[f"target_observed_{H}"] = _sh.where(_sh.notna(), False).astype(bool)
    df = df.reset_index().rename(columns={"index":"timestamp"})
    df["session_id"] = f"{fid}_{day}"
    return df

def main():
    long=pd.read_parquet(IN)
    long["occupancy"]=long["occupancy"].clip(lower=0)
    counts=long.groupby("facility_id").size()
    keep=counts[counts>=MIN_RECORDS].index.tolist()
    excluded=sorted(set(counts.index)-set(keep))
    log(f"excluding sparse facilities {excluded}; keeping {len(keep)}")
    long=long[long.facility_id.isin(keep)].copy()
    long["timestamp"]=pd.to_datetime(long["timestamp"])
    long["day"]=long["timestamp"].dt.date

    feats=[]
    for (fid,day),g in long.groupby(["facility_id","day"]):
        f=build_session(g[["timestamp","occupancy"]].copy(), fid, day)
        if len(f)==0: continue
        f["facility_id"]=fid; f["facility_name"]=g["facility_name"].iloc[0]
        feats.append(f)
    df=pd.concat(feats,ignore_index=True)
    log(f"built {df.session_id.nunique()} facility-day sessions")

    ts=df["timestamp"]; mod=ts.dt.hour*60+ts.dt.minute
    df["tod_sin"]=np.sin(2*np.pi*mod/1440); df["tod_cos"]=np.cos(2*np.pi*mod/1440)
    df["dow"]=ts.dt.dayofweek; df["is_weekend"]=(df["dow"]>=5).astype(int)
    import holidays; uk=holidays.UnitedKingdom(subdiv="England", years=[2016])
    df["is_holiday"]=ts.dt.date.map(lambda d:int(d in uk))

    tmin,tmax=df.timestamp.min(),df.timestamp.max(); span=tmax-tmin
    te=tmin+span*TRAIN_FRAC; ce=tmin+span*(TRAIN_FRAC+CALIB_FRAC)
    def asg(t): return np.where(t<=te,"train",np.where(t<=ce,"calibration","test"))
    df["split"]=asg(df.timestamp)
    # train has no preceding split -> anchor before the data so every train row is embargo-clear
    starts={"train":tmin-pd.Timedelta(days=1),"calibration":te,"test":ce}
    own_start=df["split"].map(starts)
    for H in HORIZONS_MIN:
        tgt=df["timestamp"]+pd.Timedelta(minutes=H)
        df[f"target_ts_{H}"]=tgt
        df[f"split_ok_{H}"]=(asg(tgt)==df["split"].values)
        df[f"embargo_ok_{H}"]=(df["timestamp"]-own_start)>pd.Timedelta(minutes=H) if EMBARGO \
                               else pd.Series(True,index=df.index)
        df[f"use_{H}"]=df[f"split_ok_{H}"]&df[f"embargo_ok_{H}"]
    df["occ_interpolated"]=~df["occ_observed"].astype(bool)
    for H in HORIZONS_MIN: df[f"target_interpolated_{H}"]=~df[f"target_observed_{H}"].astype(bool)

    fcols=[c for c in df.columns if c.startswith(("lag_","roll_"))]+["tod_sin","tod_cos","dow","is_weekend","is_holiday"]
    tcols=[c for c in df.columns if c.startswith("y_t+")]
    before=len(df); df=df.dropna(subset=fcols+tcols).reset_index(drop=True)
    log(f"dropped {before-len(df)} rows (warm-up / session edges); kept {len(df)}")

    flag=([f"target_ts_{H}" for H in HORIZONS_MIN]+[f"split_ok_{H}" for H in HORIZONS_MIN]+
          [f"embargo_ok_{H}" for H in HORIZONS_MIN]+[f"use_{H}" for H in HORIZONS_MIN]+
          ["occ_interpolated"]+[f"target_interpolated_{H}" for H in HORIZONS_MIN])
    df=df[["timestamp","facility_id","facility_name","session_id","occupancy"]+fcols+tcols+["split"]+flag]
    df.to_parquet(OUT,index=False)

    rep={"version":"v2-session-safe","rows":int(len(df)),"facilities":int(df.facility_id.nunique()),
         "sessions":int(df.session_id.nunique()),"excluded":excluded,"embargo":EMBARGO,
         "rows_per_split":{k:int(v) for k,v in df.groupby("split").size().items()},
         "cross_split_targets_blocked":{str(H):int((~df[f"split_ok_{H}"]).sum()) for H in HORIZONS_MIN},
         "usable_rows":{str(H):int(df[f"use_{H}"].sum()) for H in HORIZONS_MIN},
         "occ_interpolated_pct":round(100*float(df["occ_interpolated"].mean()),4),
         "target_interpolated_pct":{str(H):round(100*float(df[f"target_interpolated_{H}"].mean()),4)
                                    for H in HORIZONS_MIN},
         "time_min":str(df.timestamp.min()),"time_max":str(df.timestamp.max())}
    json.dump(rep,open(PROC/"birmingham_features_v2_report.json","w"),indent=2)
    log("report: "+json.dumps(rep,indent=2)); log("DONE.")

if __name__=="__main__": main()
