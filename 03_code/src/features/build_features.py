#!/usr/bin/env python3
"""
Feature engineering (Phase 1 cont.) — Belgrade parking.

Input : 01_data/processed/belgrade_long.parquet  (timestamp, facility_id, facility_name, occupancy, split)
Output: 01_data/processed/belgrade_features.parquet  (model-ready, one row per facility-timestamp)
        + belgrade_features_report.json

Design choices (documented for reproducibility):
- Resample each facility to a REGULAR 5-minute grid (mean within bin). This fixes the slightly irregular
  ~2.05-min native spacing and the 7 small gaps, and makes forecast horizons exact multiples of the grid.
  5-min is still high-frequency for parking (cf. Birmingham at 30-min).
- Forecast horizons: t+5, t+15, t+30 minutes  => 1, 3, 6 grid steps (matches the research blueprint).
- Features: occupancy lags, rolling mean/std, cyclical time-of-day, day-of-week, weekend & holiday flags.
- Split label is re-derived from each row's timestamp using the same cutoffs as preprocessing.
- Rows with NaNs introduced by lagging / horizon-shifting are dropped PER FACILITY.

Run:  python build_features.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
PROC = ROOT / "01_data" / "processed"
IN_PATH  = PROC / "belgrade_long.parquet"
OUT_PATH = PROC / "belgrade_features.parquet"

GRID = "5min"                      # regular resampling grid
STEP_MIN = 5
HORIZONS_MIN = [5, 15, 30]         # forecast targets (minutes ahead)
LAGS = [1, 2, 3, 6, 9, 12]        # in steps -> 5,10,15,30,45,60 min back
ROLL_WINDOWS = [6, 12]            # in steps -> 30, 60 min
SPLIT = {"train_end": "2017-03-13 23:59:59", "calib_end": "2017-03-17 23:59:59"}

def log(m): print(f"[features] {m}")

def assign_split(ts):
    te, ce = pd.Timestamp(SPLIT["train_end"]), pd.Timestamp(SPLIT["calib_end"])
    return np.where(ts <= te, "train", np.where(ts <= ce, "calibration", "test"))

def build_for_facility(g: pd.DataFrame) -> pd.DataFrame:
    g = g.set_index("timestamp").sort_index()
    # regular grid (mean within each bin); interpolate tiny internal gaps only
    occ = g["occupancy"].resample(GRID).mean()
    occ = occ.interpolate(method="time", limit=2, limit_area="inside")
    df = pd.DataFrame({"occupancy": occ})
    # lags
    for L in LAGS:
        df[f"lag_{L*STEP_MIN}min"] = df["occupancy"].shift(L)
    # rolling stats (shifted by 1 so they use only past info)
    for W in ROLL_WINDOWS:
        r = df["occupancy"].shift(1).rolling(W)
        df[f"roll_mean_{W*STEP_MIN}min"] = r.mean()
        df[f"roll_std_{W*STEP_MIN}min"] = r.std()
    # multi-horizon targets
    for H in HORIZONS_MIN:
        steps = H // STEP_MIN
        df[f"y_t+{H}min"] = df["occupancy"].shift(-steps)
    return df.reset_index()

def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["timestamp"]
    mod = ts.dt.hour * 60 + ts.dt.minute                 # minute of day
    df["tod_sin"] = np.sin(2 * np.pi * mod / 1440.0)
    df["tod_cos"] = np.cos(2 * np.pi * mod / 1440.0)
    df["dow"] = ts.dt.dayofweek
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    try:
        import holidays
        rs = holidays.Serbia(years=[2017])
        df["is_holiday"] = ts.dt.date.map(lambda d: int(d in rs))
    except Exception as e:
        log(f"holidays unavailable ({e}); setting is_holiday=0")
        df["is_holiday"] = 0
    return df

def main():
    log(f"reading {IN_PATH.name}")
    long = pd.read_parquet(IN_PATH)
    feats = []
    for fid, g in long.groupby("facility_id"):
        f = build_for_facility(g[["timestamp", "occupancy"]].copy())
        f["facility_id"] = fid
        f["facility_name"] = g["facility_name"].iloc[0]
        feats.append(f)
    df = pd.concat(feats, ignore_index=True)
    df = add_calendar(df)
    df["split"] = assign_split(df["timestamp"])

    feature_cols = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
                   ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    target_cols = [c for c in df.columns if c.startswith("y_t+")]

    before = len(df)
    df = df.dropna(subset=feature_cols + target_cols).reset_index(drop=True)
    log(f"dropped {before-len(df)} rows with NaN (warm-up lags / horizon edges); kept {len(df)}")

    # reorder
    ordered = ["timestamp", "facility_id", "facility_name", "occupancy"] + feature_cols + target_cols + ["split"]
    df = df[ordered]
    df.to_parquet(OUT_PATH, index=False)

    report = {
        "rows": int(len(df)), "facilities": int(df.facility_id.nunique()),
        "grid": GRID, "horizons_min": HORIZONS_MIN, "lags_steps": LAGS, "roll_windows_steps": ROLL_WINDOWS,
        "n_feature_cols": len(feature_cols), "feature_cols": feature_cols, "target_cols": target_cols,
        "rows_per_split": {k: int(v) for k, v in df.groupby("split").size().items()},
        "time_min": str(df.timestamp.min()), "time_max": str(df.timestamp.max()),
        "any_nan": bool(df[feature_cols + target_cols].isna().any().any()),
        "output": OUT_PATH.name,
    }
    with open(PROC / "belgrade_features_report.json", "w") as f:
        json.dump(report, f, indent=2)
    log("report: " + json.dumps(report, indent=2))
    log("DONE.")

if __name__ == "__main__":
    main()
