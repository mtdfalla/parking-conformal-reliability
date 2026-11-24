#!/usr/bin/env python3
"""
Birmingham feature engineering, v3: availability-safe inputs, observed targets only.

Supersedes `2026-09-02-build_features_birmingham_v2.py` (prespecified in
04_experiments/2026-11-22-birmingham-causal-rebuild-PRESPECIFICATION.md, section 2).

THE DEFECT THIS FIXES
---------------------
v2 filled an empty 30-minute bin inside a session with `interpolate("time", limit=1,
limit_area="inside")`, the time-weighted mean of the bins on either side. The value stored at bin t
therefore depended on the reading in bin t+1, and it was used as the anchor of row t, as a lag of later
rows and as the target of earlier rows. About a quarter of the bins are empty, because the half-hourly
feed jitters around the half hour and floor-binning puts two readings in one bin and none in the next.

THE RULE
--------
1. No interpolation anywhere.
2. Anchor and feature series: the observed bin value, or, where the bin is empty, the last observed bin
   value carried forward AT MOST ONE grid step. Lags and rolling features are shifts and windows of
   this series, as in v2. A longer gap stays missing.
3. Targets: the observed bin value only.
4. use_H = split_ok_H & embargo_ok_H & target_observed_H. A row is kept when its features are complete
   and at least one horizon is usable. Target columns are missing where the target is unobserved.
5. Flags on every row: occ_observed, occ_carried, anchor_age_steps, target_observed_H.
   occ_interpolated and target_interpolated_H are kept and are identically False.

TIME CONVENTION
---------------
Row t is a forecast issued at the close of bin t: it may use any reading with timestamp < t + 30 min.
Its target at horizon H is the mean reading in bin t + H. tests/2026-11-22-test-feature-causality.py
perturbs later raw readings and asserts that no feature of an earlier row moves.

UNCHANGED from v2: grid, horizons, lags, rolling windows, calendar features, MIN_RECORDS, clipping at
zero, split fractions and boundaries, embargo, session identity.

Input : 01_data/processed/birmingham_long.parquet
Output: <out-dir>/birmingham_features_v3.parquet and birmingham_features_v3_report.json
        (out-dir defaults to 01_data/processed)
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd

_p = Path(__file__).resolve()
while _p != _p.parent and not (_p / "01_data").is_dir():
    _p = _p.parent
ROOT = _p; PROC = ROOT / "01_data" / "processed"
IN = PROC / "birmingham_long.parquet"

GRID = "30min"; STEP = 30
HORIZONS_MIN = [30, 60, 90]
LAGS = [1, 2, 3, 4, 5, 6]
ROLL = [3, 6]
MIN_RECORDS = 500
TRAIN_FRAC, CALIB_FRAC = 10/18, 4/18
EMBARGO = True
MAX_CARRY_STEPS = 1          # an empty bin takes the previous bin's observed value, once

def log(m): print(f"[bham-feat-v3] {m}", flush=True)

def build_session(s: pd.DataFrame, fid, day) -> pd.DataFrame:
    """Grid one facility-day session. Features use past and present bins only."""
    s = s.set_index("timestamp").sort_index()
    lo = s.index.min().floor(GRID); hi = s.index.max().ceil(GRID)
    if hi <= lo: return pd.DataFrame()
    grid = pd.date_range(lo, hi, freq=GRID)
    occ_raw = s["occupancy"].resample(GRID).mean().reindex(grid)
    observed = occ_raw.notna()
    occ = occ_raw.ffill(limit=MAX_CARRY_STEPS)            # backward-looking only
    carried = occ.notna() & ~observed
    df = pd.DataFrame({"occupancy": occ, "occ_observed": observed, "occ_carried": carried,
                       "anchor_age_steps": carried.astype(int)})
    for L in LAGS: df[f"lag_{L*STEP}min"] = df["occupancy"].shift(L)
    for W in ROLL:
        r = df["occupancy"].shift(1).rolling(W)
        df[f"roll_mean_{W*STEP}min"] = r.mean(); df[f"roll_std_{W*STEP}min"] = r.std()
    for H in HORIZONS_MIN:
        k = H // STEP
        df[f"y_t+{H}min"] = occ_raw.shift(-k)             # observed bins only, never carried
        df[f"target_observed_{H}"] = observed.shift(-k, fill_value=False).astype(bool)
    df = df.reset_index().rename(columns={"index": "timestamp"})
    df["session_id"] = f"{fid}_{day}"
    return df

FEATURE_PREFIX = ("lag_", "roll_")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(PROC))
    ap.add_argument("--tab-dir", default=None,
                    help="where the representativeness table goes; default 05_results/tables when --out-dir is "
                         "the project's processed folder, else --out-dir (so a test run never writes into 05_results)")
    args = ap.parse_args()
    outdir = Path(args.out_dir); outdir.mkdir(parents=True, exist_ok=True)
    tabdir = Path(args.tab_dir) if args.tab_dir else (ROOT / "05_results" / "tables"
                                                      if outdir.resolve() == PROC.resolve() else outdir)
    OUT = outdir / "birmingham_features_v3.parquet"

    long = pd.read_parquet(IN)
    long["occupancy"] = long["occupancy"].clip(lower=0)
    counts = long.groupby("facility_id").size()
    keep = counts[counts >= MIN_RECORDS].index.tolist()
    excluded = sorted(set(counts.index) - set(keep))
    log(f"excluding sparse facilities {excluded}; keeping {len(keep)}")
    long = long[long.facility_id.isin(keep)].copy()
    long["timestamp"] = pd.to_datetime(long["timestamp"])
    long["day"] = long["timestamp"].dt.date

    feats = []
    for (fid, day), g in long.groupby(["facility_id", "day"]):
        f = build_session(g[["timestamp", "occupancy"]].copy(), fid, day)
        if len(f) == 0: continue
        f["facility_id"] = fid; f["facility_name"] = g["facility_name"].iloc[0]
        feats.append(f)
    df = pd.concat(feats, ignore_index=True)
    log(f"built {df.session_id.nunique()} facility-day sessions")

    ts = df["timestamp"]; mod = ts.dt.hour*60 + ts.dt.minute
    df["tod_sin"] = np.sin(2*np.pi*mod/1440); df["tod_cos"] = np.cos(2*np.pi*mod/1440)
    df["dow"] = ts.dt.dayofweek; df["is_weekend"] = (df["dow"] >= 5).astype(int)
    import holidays; uk = holidays.UnitedKingdom(subdiv="England", years=[2016])
    df["is_holiday"] = ts.dt.date.map(lambda d: int(d in uk))

    tmin, tmax = df.timestamp.min(), df.timestamp.max(); span = tmax - tmin
    te = tmin + span*TRAIN_FRAC; ce = tmin + span*(TRAIN_FRAC + CALIB_FRAC)
    def asg(t): return np.where(t <= te, "train", np.where(t <= ce, "calibration", "test"))
    df["split"] = asg(df.timestamp)
    starts = {"train": tmin - pd.Timedelta(days=1), "calibration": te, "test": ce}
    own_start = df["split"].map(starts)
    for H in HORIZONS_MIN:
        tgt = df["timestamp"] + pd.Timedelta(minutes=H)
        df[f"target_ts_{H}"] = tgt
        df[f"split_ok_{H}"] = (asg(tgt) == df["split"].values)
        df[f"embargo_ok_{H}"] = (df["timestamp"] - own_start) > pd.Timedelta(minutes=H) if EMBARGO \
                                else pd.Series(True, index=df.index)
        df[f"use_{H}"] = df[f"split_ok_{H}"] & df[f"embargo_ok_{H}"] & df[f"target_observed_{H}"]
    df["occ_interpolated"] = False
    for H in HORIZONS_MIN: df[f"target_interpolated_{H}"] = False

    fcols = [c for c in df.columns if c.startswith(FEATURE_PREFIX)] + \
            ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    tcols = [c for c in df.columns if c.startswith("y_t+")]
    before = len(df)
    df = df.dropna(subset=["occupancy"] + fcols)
    any_use = np.zeros(len(df), dtype=bool)
    for H in HORIZONS_MIN: any_use |= df[f"use_{H}"].values
    n_no_h = int((~any_use).sum())
    df = df[any_use].reset_index(drop=True)
    log(f"dropped {before-len(df)} rows (warm-up, long gaps, session edges, {n_no_h} with no usable horizon); kept {len(df)}")

    # a usable row never carries a missing or unobserved target
    for H in HORIZONS_MIN:
        u = df[df[f"use_{H}"]]
        assert u[f"y_t+{H}min"].notna().all() and u[f"target_observed_{H}"].all(), f"use_{H} admits an unobserved target"

    flag = ([f"target_ts_{H}" for H in HORIZONS_MIN] + [f"split_ok_{H}" for H in HORIZONS_MIN] +
            [f"embargo_ok_{H}" for H in HORIZONS_MIN] + [f"use_{H}" for H in HORIZONS_MIN] +
            ["occ_observed", "occ_carried", "anchor_age_steps"] +
            [f"target_observed_{H}" for H in HORIZONS_MIN] +
            ["occ_interpolated"] + [f"target_interpolated_{H}" for H in HORIZONS_MIN])
    df = df[["timestamp", "facility_id", "facility_name", "session_id", "occupancy"] + fcols + tcols + ["split"] + flag]
    df.to_parquet(OUT, index=False)

    rep = {"version": "v3-availability-safe", "rows": int(len(df)), "facilities": int(df.facility_id.nunique()),
           "sessions": int(df.session_id.nunique()), "excluded": excluded, "embargo": EMBARGO,
           "max_carry_steps": MAX_CARRY_STEPS,
           "rows_per_split": {k: int(v) for k, v in df.groupby("split").size().items()},
           "usable_rows": {str(H): int(df[f"use_{H}"].sum()) for H in HORIZONS_MIN},
           "usable_rows_per_split": {str(H): {k: int(v) for k, v in df[df[f"use_{H}"]].groupby("split").size().items()}
                                     for H in HORIZONS_MIN},
           "anchor_carried_pct_of_usable": {str(H): round(100*float(df.loc[df[f"use_{H}"], "occ_carried"].mean()), 4)
                                            for H in HORIZONS_MIN},
           "occ_interpolated_pct": 0.0,
           "target_interpolated_pct": {str(H): 0.0 for H in HORIZONS_MIN},
           "time_min": str(df.timestamp.min()), "time_max": str(df.timestamp.max())}
    json.dump(rep, open(outdir / "birmingham_features_v3_report.json", "w"), indent=2)

    # Revision 56 (register row 2.1): the measured exposure, per horizon, in the same columns as
    # 2026-09-02-v2-representativeness.csv, so Table 5's interpolation row reads both sides from a table.
    # Percentages are of the rows usable at that horizon; interpolation shares are COMPUTED from the flags.
    rr = []
    for H in HORIZONS_MIN:
        u = df[df[f"use_{H}"]]
        rr.append(dict(city="Birmingham", horizon=f"t+{H}min", facilities=int(u.facility_id.nunique()),
                       rows_usable=int(len(u)),
                       anchor_interpolated_pct=round(100 * float(u["occ_interpolated"].mean()), 2),
                       anchor_carried_pct=round(100 * float(u["occ_carried"].mean()), 2),
                       target_interpolated_pct=round(100 * float(u[f"target_interpolated_{H}"].mean()), 2),
                       train_rows=int((u.split == "train").sum()), calib_rows=int((u.split == "calibration").sum()),
                       test_rows=int((u.split == "test").sum()), days=int(u.timestamp.dt.date.nunique())))
    tabdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rr).to_csv(tabdir / "2026-11-22-v3-representativeness.csv", index=False)
    log("report: " + json.dumps(rep, indent=2)); log("DONE.")

if __name__ == "__main__": main()
