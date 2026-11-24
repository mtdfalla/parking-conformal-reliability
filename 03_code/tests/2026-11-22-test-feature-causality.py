#!/usr/bin/env python3
"""
End-to-end causality test of a Birmingham session builder: perturb LATER raw readings and assert that
no feature, anchor or flag of an EARLIER row moves.

  python3 2026-11-22-test-feature-causality.py --builder PATH_TO_BUILDER [--expect-fail]

Time convention under test: row t is issued at the close of bin t and may use any reading with
timestamp < t + 30 min. For a cut bin c, every reading with timestamp >= c + 30 min is perturbed
(shifted by +50, and separately deleted). Rows at bins <= c must keep every non-target column.

`--expect-fail` is the positive control: pointed at the v2 builder the test must report violations,
and the script exits 0 only if it does. A causality test that passes on a builder known to look ahead
is blind.
"""
from __future__ import annotations
import argparse, importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

SEED = 42; N_SESSIONS = 200; N_CUTS = 5; STEP = pd.Timedelta(minutes=30)

def load(path):
    spec = importlib.util.spec_from_file_location("builder_under_test", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def non_target_cols(df):
    return [c for c in df.columns if not c.startswith(("y_t+", "target_observed_", "target_interpolated_"))]

def same(a: pd.DataFrame, b: pd.DataFrame, cols) -> bool:
    if len(a) != len(b): return False
    for c in cols:
        x, y = a[c].values, b[c].values
        if x.dtype.kind in "fc":
            if not np.array_equal(x, y, equal_nan=True): return False
        elif not (x == y).all(): return False
    return True

def run(builder, sessions):
    viol = 0; checks = 0; first = None
    for (fid, day), raw in sessions:
        base = builder.build_session(raw.copy(), fid, day)
        if len(base) < 4: continue
        cols = non_target_cols(base)
        bins = base["timestamp"].iloc[1:-1]
        cuts = bins.iloc[np.linspace(0, len(bins) - 1, min(N_CUTS, len(bins))).astype(int)]
        for c in cuts:
            later = raw["timestamp"] >= c + STEP
            if not later.any() or later.all(): continue
            for kind in ("shift", "delete"):
                pert = raw.copy()
                if kind == "shift": pert.loc[later, "occupancy"] = pert.loc[later, "occupancy"] + 50.0
                else: pert = pert[~later]
                out = builder.build_session(pert, fid, day)
                a = base[base["timestamp"] <= c].reset_index(drop=True)
                b = out[out["timestamp"] <= c].reset_index(drop=True)
                checks += 1
                if not same(a, b, cols):
                    viol += 1
                    if first is None: first = (fid, str(day), str(c), kind)
    return checks, viol, first

def synthetic():
    """The auditor's case: readings at 09:30 and 10:35, none in the 10:00 bin."""
    t = pd.to_datetime(["2016-10-04 08:05", "2016-10-04 08:35", "2016-10-04 09:05", "2016-10-04 09:35",
                        "2016-10-04 10:35", "2016-10-04 11:05", "2016-10-04 11:35", "2016-10-04 12:05"])
    return [((0, "synthetic"), pd.DataFrame({"timestamp": t, "occupancy": [10., 12., 15., 17.5, 67.5, 70., 71., 72.]}))]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--builder", required=True)
    ap.add_argument("--expect-fail", action="store_true")
    args = ap.parse_args()
    b = load(args.builder)
    long = pd.read_parquet(b.IN)
    long["occupancy"] = long["occupancy"].clip(lower=0).astype(float)
    long["timestamp"] = pd.to_datetime(long["timestamp"]); long["day"] = long["timestamp"].dt.date
    keys = sorted(long.groupby(["facility_id", "day"]).groups.keys())
    rng = np.random.default_rng(SEED)
    pick = [keys[i] for i in sorted(rng.choice(len(keys), size=min(N_SESSIONS, len(keys)), replace=False))]
    gb = long.groupby(["facility_id", "day"])
    sessions = synthetic() + [(k, gb.get_group(k)[["timestamp", "occupancy"]].copy()) for k in pick]
    checks, viol, first = run(b, sessions)
    print(f"[causality] builder: {Path(args.builder).name}")
    print(f"[causality] {len(sessions)} sessions, {checks} perturbation checks, {viol} violation(s)"
          + (f"; first at facility {first[0]}, day {first[1]}, cut {first[2]}, {first[3]}" if first else ""))
    if args.expect_fail:
        ok = viol > 0
        print("[causality] POSITIVE CONTROL " + ("PASS: the test detects a builder that looks ahead" if ok
                                                 else "FAIL: the test is blind"))
    else:
        ok = viol == 0 and checks > 0
        print("[causality] " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
