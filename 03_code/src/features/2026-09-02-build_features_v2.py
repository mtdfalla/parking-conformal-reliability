#!/usr/bin/env python3
"""
Belgrade feature engineering — v2, CAUSALLY CORRECTED (R-Phase 1, D-014).

Supersedes `build_features.py`. Fixes audit issue S01 (split-boundary target leakage) and adds the
provenance columns needed for issues X01 (undisclosed interpolation) and D05 (exclusion sensitivity).

WHAT CHANGED vs v1
------------------
1. **Explicit target timestamps.** v1 created targets with `shift(-steps)` and then labelled every row by
   its ISSUE timestamp only (v1 line 92). A train row issued at 23:55 on the last train day therefore
   carried a t+30 outcome observed inside the calibration split. Measured exposure in v1: 288 of 92,544
   rows (0.31%) at t+30, 144 at t+15, 48 at t+5.
   v2 computes `target_ts = issue_ts + h` for every horizon and emits a per-horizon flag
   `split_ok_{H}` that is True only when issue and target fall in the SAME split.
2. **Boundary embargo.** `embargo_ok_{H}` additionally drops rows whose issue time is within h of the
   START of its own split, so a split never opens with rows whose recent history sits in the previous
   split. Combined flag: `use_{H} = split_ok_{H} & embargo_ok_{H}`.
3. **Per-horizon masks, not row deletion.** A row valid at t+5 but not at t+30 is kept and masked per
   horizon, so sample sizes are not silently reduced for the short horizons. Downstream scripts MUST
   filter with `use_{H}`.
4. **Interpolation provenance.** `occ_interpolated` marks rows whose own occupancy anchor was filled by
   interpolation rather than observed; `target_interpolated_{H}` marks interpolated targets. v1 reported
   neither, so the manuscript could not state its interpolation rate.

UNCHANGED (deliberately, so the only difference is causal structure): 5-min grid, lag/rolling/calendar
features, horizons, split cutoffs, interpolation limit, per-facility NaN dropping.

Input : 01_data/processed/belgrade_long.parquet
Output: 01_data/processed/belgrade_features_v2.parquet  (+ belgrade_features_v2_report.json)
        The v1 file is NOT modified.
Run   : python 2026-09-02-build_features_v2.py
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
OUT_PATH = PROC / "belgrade_features_v2.parquet"

GRID = "5min"
STEP_MIN = 5
HORIZONS_MIN = [5, 15, 30]
LAGS = [1, 2, 3, 6, 9, 12]
ROLL_WINDOWS = [6, 12]
SPLIT = {"train_end": "2017-03-13 23:59:59", "calib_end": "2017-03-17 23:59:59"}
EMBARGO = True

def log(m): print(f"[features-v2] {m}", flush=True)

def assign_split(ts):
    te, ce = pd.Timestamp(SPLIT["train_end"]), pd.Timestamp(SPLIT["calib_end"])
    return np.where(ts <= te, "train", np.where(ts <= ce, "calibration", "test"))

def split_starts(tmin):
    """Start instant of each split. `train` has no preceding split, so it needs no embargo:
    we anchor it at the dataset minimum, which makes every train row embargo-clear by construction."""
    te, ce = pd.Timestamp(SPLIT["train_end"]), pd.Timestamp(SPLIT["calib_end"])
    return {"train": tmin - pd.Timedelta(days=1), "calibration": te, "test": ce}

def build_for_facility(g: pd.DataFrame) -> pd.DataFrame:
    g = g.set_index("timestamp").sort_index()
    occ_raw = g["occupancy"].resample(GRID).mean()
    observed = occ_raw.notna()                                   # before any filling
    occ = occ_raw.interpolate(method="time", limit=2, limit_area="inside")
    df = pd.DataFrame({"occupancy": occ, "occ_observed": observed.reindex(occ.index, fill_value=False)})
    for L in LAGS:
        df[f"lag_{L*STEP_MIN}min"] = df["occupancy"].shift(L)
    for W in ROLL_WINDOWS:
        r = df["occupancy"].shift(1).rolling(W)
        df[f"roll_mean_{W*STEP_MIN}min"] = r.mean()
        df[f"roll_std_{W*STEP_MIN}min"] = r.std()
    for H in HORIZONS_MIN:
        steps = H // STEP_MIN
        df[f"y_t+{H}min"] = df["occupancy"].shift(-steps)
        _sh = df["occ_observed"].shift(-steps)
        df[f"target_observed_{H}"] = _sh.where(_sh.notna(), False).astype(bool)
    return df.reset_index()

def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["timestamp"]
    mod = ts.dt.hour * 60 + ts.dt.minute
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

    # ---- causal integrity flags (the v2 fix) ----
    starts = split_starts(df["timestamp"].min())
    own_start = df["split"].map(starts)
    for H in HORIZONS_MIN:
        tgt_ts = df["timestamp"] + pd.Timedelta(minutes=H)
        df[f"target_ts_{H}"] = tgt_ts
        df[f"split_ok_{H}"] = (assign_split(tgt_ts) == df["split"].values)
        df[f"embargo_ok_{H}"] = (df["timestamp"] - own_start) > pd.Timedelta(minutes=H) if EMBARGO \
                                 else pd.Series(True, index=df.index)
        df[f"use_{H}"] = df[f"split_ok_{H}"] & df[f"embargo_ok_{H}"]

    df["occ_interpolated"] = ~df["occ_observed"].astype(bool)
    for H in HORIZONS_MIN:
        df[f"target_interpolated_{H}"] = ~df[f"target_observed_{H}"].astype(bool)

    feature_cols = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
                   ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    target_cols = [c for c in df.columns if c.startswith("y_t+")]

    before = len(df)
    df = df.dropna(subset=feature_cols + target_cols).reset_index(drop=True)
    log(f"dropped {before-len(df)} rows with NaN (warm-up lags / horizon edges); kept {len(df)}")

    flag_cols = ([f"target_ts_{H}" for H in HORIZONS_MIN] +
                 [f"split_ok_{H}" for H in HORIZONS_MIN] +
                 [f"embargo_ok_{H}" for H in HORIZONS_MIN] +
                 [f"use_{H}" for H in HORIZONS_MIN] +
                 ["occ_interpolated"] + [f"target_interpolated_{H}" for H in HORIZONS_MIN])
    ordered = ["timestamp", "facility_id", "facility_name", "occupancy"] + feature_cols + target_cols + \
              ["split"] + flag_cols
    df = df[ordered]
    df.to_parquet(OUT_PATH, index=False)

    report = {
        "version": "v2-causal", "rows": int(len(df)), "facilities": int(df.facility_id.nunique()),
        "grid": GRID, "horizons_min": HORIZONS_MIN, "embargo": EMBARGO,
        "rows_per_split": {k: int(v) for k, v in df.groupby("split").size().items()},
        "cross_split_targets_blocked": {str(H): int((~df[f"split_ok_{H}"]).sum()) for H in HORIZONS_MIN},
        "embargoed_rows": {str(H): int((~df[f"embargo_ok_{H}"]).sum()) for H in HORIZONS_MIN},
        "usable_rows": {str(H): int(df[f"use_{H}"].sum()) for H in HORIZONS_MIN},
        "occ_interpolated_rows": int(df["occ_interpolated"].sum()),
        "occ_interpolated_pct": round(100*float(df["occ_interpolated"].mean()), 4),
        "target_interpolated_pct": {str(H): round(100*float(df[f"target_interpolated_{H}"].mean()), 4)
                                    for H in HORIZONS_MIN},
        "time_min": str(df.timestamp.min()), "time_max": str(df.timestamp.max()),
        "output": OUT_PATH.name,
    }
    with open(PROC / "belgrade_features_v2_report.json", "w") as f:
        json.dump(report, f, indent=2)
    log("report: " + json.dumps(report, indent=2))
    log("DONE.")

if __name__ == "__main__":
    main()
