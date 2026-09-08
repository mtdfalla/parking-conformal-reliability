#!/usr/bin/env python3
"""
ParkingBirmingham — preprocessing (2nd dataset, external validation).

Harmonizes the UCI ParkingBirmingham CSV to the SAME long format as Belgrade so both datasets
flow through one modeling pipeline.

Input : 01_data/raw/birmingham/dataset.csv  (cols: SystemCodeNumber, Capacity, Occupancy, LastUpdated)
Output: 01_data/processed/birmingham_long.parquet (+ .csv.gz) and birmingham_preprocess_report.json

Differences vs Belgrade to remember:
- 30-minute sampling (not 2-min); coverage ~2016-10-04 .. 2016-12-19.
- Capacity IS provided -> we also compute occupancy_rate = Occupancy / Capacity (clipped to [0,1]).
- facility_id is assigned by sorting unique SystemCodeNumber (stable, 1-based).
- Temporal split mirrors Belgrade's ~10/4/4 ratio, computed from this dataset's own date range.

This script is SAFE TO RUN ONLY AFTER the CSV is present (see raw/birmingham/DOWNLOAD_INSTRUCTIONS.md).

Run:  python preprocess_birmingham.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
RAW  = ROOT / "01_data" / "raw" / "birmingham" / "dataset.csv"
PROC = ROOT / "01_data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# split ratio (train/calib/test) ~ 10/4/4 by time, as fractions of the date span
TRAIN_FRAC, CALIB_FRAC = 10/18, 4/18

def log(m): print(f"[birmingham] {m}")

def main():
    if not RAW.exists():
        log(f"MISSING: {RAW}")
        log("Download first — see 01_data/raw/birmingham/DOWNLOAD_INSTRUCTIONS.md")
        sys.exit(1)

    df = pd.read_csv(RAW)
    df.columns = [c.strip() for c in df.columns]
    need = {"SystemCodeNumber", "Capacity", "Occupancy", "LastUpdated"}
    if not need.issubset(df.columns):
        log(f"Unexpected columns: {list(df.columns)} (need {need})"); sys.exit(1)

    df["timestamp"] = pd.to_datetime(df["LastUpdated"])
    df = df.rename(columns={"SystemCodeNumber": "facility_name",
                            "Occupancy": "occupancy", "Capacity": "capacity"})
    df["occupancy"] = pd.to_numeric(df["occupancy"], errors="coerce")
    df["capacity"]  = pd.to_numeric(df["capacity"], errors="coerce")
    df = df.dropna(subset=["occupancy", "timestamp"])

    # stable facility_id
    names = sorted(df["facility_name"].unique())
    name_to_id = {n: i + 1 for i, n in enumerate(names)}
    df["facility_id"] = df["facility_name"].map(name_to_id)

    # occupancy rate (Birmingham gives capacity)
    df["occupancy_rate"] = (df["occupancy"] / df["capacity"]).clip(lower=0, upper=1)

    # temporal split from this dataset's own range
    tmin, tmax = df["timestamp"].min(), df["timestamp"].max()
    span = (tmax - tmin)
    te = tmin + span * TRAIN_FRAC
    ce = tmin + span * (TRAIN_FRAC + CALIB_FRAC)
    df["split"] = np.where(df["timestamp"] <= te, "train",
                   np.where(df["timestamp"] <= ce, "calibration", "test"))

    df = df[["timestamp", "facility_id", "facility_name", "occupancy", "capacity",
             "occupancy_rate", "split"]].sort_values(["facility_id", "timestamp"]).reset_index(drop=True)

    out = PROC / "birmingham_long.parquet"
    df.to_parquet(out, index=False)
    df.to_csv(PROC / "birmingham_long.csv.gz", index=False, compression="gzip")

    report = {
        "rows": int(len(df)), "facilities": int(df.facility_id.nunique()),
        "time_min": str(tmin), "time_max": str(tmax),
        "median_interval_min": float(df.sort_values("timestamp")
                                       .groupby("facility_id")["timestamp"].diff()
                                       .dropna().dt.total_seconds().median() / 60.0),
        "rows_per_split": {k: int(v) for k, v in df.groupby("split").size().items()},
        "missing_occupancy": int(df.occupancy.isna().sum()),
        "outputs": ["birmingham_long.parquet", "birmingham_long.csv.gz"],
    }
    with open(PROC / "birmingham_preprocess_report.json", "w") as f:
        json.dump(report, f, indent=2)
    log("report: " + json.dumps(report, indent=2))
    log("DONE.")

if __name__ == "__main__":
    main()
