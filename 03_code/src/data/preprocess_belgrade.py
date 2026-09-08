#!/usr/bin/env python3
"""
Belgrade parking — data preprocessing pipeline (Phase 1).

Parses the raw 2-minute occupancy export into a clean long-format table, reconciles
facilities against the coordinates file, builds a temporal train/calibration/test split,
runs sanity checks, and writes processed outputs + a QC plot.

Raw -> Processed. Raw files are READ-ONLY; all outputs go to 01_data/processed and 05_results.

Run:  python preprocess_belgrade.py
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path
import pandas as pd
import numpy as np

# ----- paths (resolve relative to this file, so it runs from anywhere) -----
HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                      # project root
RAW  = ROOT / "01_data" / "raw"
PROC = ROOT / "01_data" / "processed"
FIG  = ROOT / "05_results" / "figures"
PROC.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

RAW_CSV    = RAW / "belgrade_RAW.csv"
COORD_CSV  = RAW / "parking_coordinates_BG.csv"

# ----- split configuration (temporal, no shuffling) -----
# Data spans 2017-03-04 15:00 .. 2017-03-21 19:22. ~10 / 4 / 4 days.
SPLIT = {
    "train_end": "2017-03-13 23:59:59",     # train: start .. Mar 13
    "calib_end": "2017-03-17 23:59:59",     # calibration: Mar 14 .. Mar 17
    # test: Mar 18 .. end
}

def log(msg): print(f"[preprocess] {msg}")

def parse_raw() -> tuple[pd.DataFrame, list[str]]:
    """Return long-format dataframe and the ordered list of facility names."""
    rows = pd.read_csv(RAW_CSV, header=None, dtype=str, keep_default_na=False)
    names = [c for c in rows.iloc[3, 1:].tolist() if c.strip() != ""]
    n_fac = len(names)
    log(f"facilities detected in header: {n_fac}")

    data = rows.iloc[4:, : 1 + n_fac].copy()
    data.columns = ["timestamp"] + names
    data = data[data["timestamp"].str.strip() != ""]

    # timestamp like 'Sat Mar 2017 04 15:00:59'
    data["timestamp"] = pd.to_datetime(data["timestamp"], format="%a %b %Y %d %H:%M:%S")

    long = data.melt(id_vars="timestamp", var_name="facility_name", value_name="occupancy")
    long["occupancy"] = pd.to_numeric(long["occupancy"], errors="coerce")
    # stable facility_id by header order (1-based)
    name_to_id = {n: i + 1 for i, n in enumerate(names)}
    long["facility_id"] = long["facility_name"].map(name_to_id)
    long = long[["timestamp", "facility_id", "facility_name", "occupancy"]]
    return long.sort_values(["facility_id", "timestamp"]).reset_index(drop=True), names

def load_coords() -> pd.DataFrame:
    c = pd.read_csv(COORD_CSV, header=None, dtype=str, keep_default_na=False)
    recs = []
    for _, r in c.iterrows():
        if len(r) >= 4 and str(r[1]).strip().isdigit():
            recs.append((int(r[1]), float(r[2]), float(r[3])))
    df = pd.DataFrame(recs, columns=["facility_id", "longitude", "latitude"])
    log(f"coordinate entries: {len(df)}")
    return df

def assign_split(ts: pd.Series) -> pd.Series:
    te = pd.Timestamp(SPLIT["train_end"]); ce = pd.Timestamp(SPLIT["calib_end"])
    s = np.where(ts <= te, "train", np.where(ts <= ce, "calibration", "test"))
    return pd.Series(s, index=ts.index)

def sanity_checks(long: pd.DataFrame, coords: pd.DataFrame) -> dict:
    out = {}
    out["n_facilities"] = int(long["facility_id"].nunique())
    out["n_timestamps"] = int(long["timestamp"].nunique())
    out["n_rows"] = int(len(long))
    out["missing_occupancy"] = int(long["occupancy"].isna().sum())
    out["time_min"] = str(long["timestamp"].min())
    out["time_max"] = str(long["timestamp"].max())
    # sampling interval (per facility)
    one = long[long["facility_id"] == long["facility_id"].min()].sort_values("timestamp")
    deltas = one["timestamp"].diff().dropna().dt.total_seconds() / 60.0
    out["median_interval_min"] = float(deltas.median())
    out["interval_gaps_gt_5min"] = int((deltas > 5).sum())
    # facility / coordinate reconciliation
    fac_ids = set(long["facility_id"].unique()); coord_ids = set(coords["facility_id"].unique())
    out["facilities_without_coords"] = sorted(int(x) for x in (fac_ids - coord_ids))
    out["coords_without_facility"] = sorted(int(x) for x in (coord_ids - fac_ids))
    return out

def make_plot(long: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # pick a high-occupancy facility for the QC plot
    totals = long.groupby("facility_id")["occupancy"].mean()
    fid = int(totals.idxmax())
    sub = long[long["facility_id"] == fid].sort_values("timestamp")
    name = sub["facility_name"].iloc[0]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(sub["timestamp"], sub["occupancy"], lw=0.7, color="#1F4E79")
    te = pd.Timestamp(SPLIT["train_end"]); ce = pd.Timestamp(SPLIT["calib_end"])
    ax.axvspan(sub["timestamp"].min(), te, alpha=0.06, color="green")
    ax.axvspan(te, ce, alpha=0.10, color="orange")
    ax.axvspan(ce, sub["timestamp"].max(), alpha=0.10, color="red")
    ax.set_title(f"QC: occupancy over time — facility {fid} ({name})\n"
                 f"green=train  orange=calibration  red=test")
    ax.set_xlabel("time"); ax.set_ylabel("cars parked")
    fig.tight_layout()
    p = FIG / "2026-06-20-qc-occupancy-splits.png"
    fig.savefig(p, dpi=130); plt.close(fig)
    log(f"QC plot -> {p}")

def main():
    log(f"reading {RAW_CSV.name}")
    long, names = parse_raw()
    coords = load_coords()
    long["split"] = assign_split(long["timestamp"])

    checks = sanity_checks(long, coords)
    log("sanity checks: " + json.dumps(checks, indent=2))

    split_counts = long.groupby("split")["timestamp"].nunique().to_dict()
    log(f"timestamps per split: {split_counts}")

    # ----- write outputs -----
    long_path = PROC / "belgrade_long.parquet"
    long.to_parquet(long_path, index=False)
    long.to_csv(PROC / "belgrade_long.csv.gz", index=False, compression="gzip")
    coords.to_parquet(PROC / "facility_coords.parquet", index=False)
    pd.DataFrame([{"facility_id": i + 1, "facility_name": n} for i, n in enumerate(names)]) \
        .to_csv(PROC / "facility_index.csv", index=False)

    report = {"checks": checks, "split_config": SPLIT,
              "timestamps_per_split": {k: int(v) for k, v in split_counts.items()},
              "outputs": ["belgrade_long.parquet", "belgrade_long.csv.gz",
                          "facility_coords.parquet", "facility_index.csv"]}
    with open(PROC / "preprocess_report.json", "w") as f:
        json.dump(report, f, indent=2)
    log(f"report -> {PROC/'preprocess_report.json'}")

    make_plot(long)
    log("DONE.")


if __name__ == "__main__":
    main()
