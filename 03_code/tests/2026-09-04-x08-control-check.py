#!/usr/bin/env python3
"""NEGATIVE CONTROL for the X08 batch (B11): filter-OFF re-aggregation must reproduce every logged
summary number to 4 dp. If any pair FAILS, that experiment does not get a re-aggregated result -- it
falls back to a genuine rerun of its script. Exit code is the gate.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

TAB = Path(__file__).resolve().parents[2] / "05_results" / "tables"

PAIRS = [
    ("core headline (EXP-017/019)", "2026-09-02-corrected-headline-gcal.csv",
     "2026-09-04-x08-core-headline-control.csv", ["city", "horizon", "method"]),
    ("E3 baselines (EXP-025)", "2026-09-03-e3-summary.csv",
     "2026-09-04-x08-e3-summary-control.csv", ["dataset", "horizon", "level", "method"]),
    ("base learners (EXP-020)", "2026-09-03-base-learner-robustness.csv",
     "2026-09-04-x08-base-learner-control.csv", ["base", "level", "method"]),
    ("time-of-day (EXP-021)", "2026-09-03-tod-summary.csv",
     "2026-09-04-x08-tod-summary-control.csv", ["method", "scope", "bucket"]),
    ("orthogonal (EXP-022)", "2026-09-03-orthogonal-partition-summary.csv",
     "2026-09-04-x08-orthogonal-summary-control.csv", ["partition", "method"]),
    ("trust/abstain (EXP-024)", "2026-09-03-trust-abstain-summary.csv",
     "2026-09-04-x08-trust-abstain-control.csv", ["method", "commit_target"]),
]

TOL = 5e-5  # 4 dp


def main() -> int:
    total_checks = total_fail = 0
    for label, logged_f, ctrl_f, keys in PAIRS:
        a = pd.read_csv(TAB / logged_f)
        b = pd.read_csv(TAB / ctrl_f)
        for k in keys:
            for d in (a, b):
                d[k] = d[k].astype(str)
        m = a.merge(b, on=keys, how="outer", suffixes=("_logged", "_ctrl"), indicator=True)
        checks = fails = 0
        msgs = []
        unmatched = int((m["_merge"] != "both").sum())
        if unmatched:
            fails += unmatched
            msgs.append(f"{unmatched} row(s) present in only one file")
        num = [c for c in a.columns if c not in keys
               and pd.api.types.is_numeric_dtype(a[c]) and f"{c}_ctrl" in m.columns]
        for c in num:
            x, y = m[f"{c}_logged"], m[f"{c}_ctrl"]
            both_nan = x.isna() & y.isna()
            d = (x - y).abs()
            bad = (~both_nan) & (d.isna() | (d > TOL))
            checks += int((~both_nan).sum())
            if bad.any():
                fails += int(bad.sum())
                w = m.loc[bad, keys + [f"{c}_logged", f"{c}_ctrl"]].head(3)
                msgs.append(f"column '{c}': {int(bad.sum())} mismatch(es)\n"
                            + w.to_string(index=False))
        total_checks += checks
        total_fail += fails
        status = "PASS" if fails == 0 else "FAIL"
        print(f"  {status}  {label:28s} {checks:4d} numeric checks, {fails} failed")
        for s in msgs:
            print("        " + s.replace("\n", "\n        "))
    print("-" * 72)
    print(f"NEGATIVE CONTROL: {total_checks} checks, {total_fail} failed")
    if total_fail:
        print("The re-aggregator does NOT reproduce the logged aggregation. Its filtered output is")
        print("not to be trusted for the failing experiments; rerun those scripts instead.")
        return 1
    print("PASS -- filter-off reproduces every logged summary number to 4 dp, so the only difference")
    print("between the control and the filtered run is the D-018 exclusion itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
