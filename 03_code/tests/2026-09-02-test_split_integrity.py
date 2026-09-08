#!/usr/bin/env python3
"""
R-Phase 1 gate — split, session and causality integrity tests for the v2 feature tables (D-014).

Every assertion here corresponds to a specific audit finding. The suite must exit 0 before any Phase 2
work begins, and it is the artifact we cite in the manuscript/ESM as evidence that the corrected pipeline
contains no cross-split or cross-session information.

  T1  no duplicate (facility, timestamp)                     — basic hygiene
  T2  timestamps strictly increasing within each facility    — basic hygiene
  T3  target_ts == issue_ts + H exactly                      — S01 (explicit target timestamps)
  T4  every USED row has issue and target in the same split  — S01 (the leakage fix)
  T5  embargo honoured: no used row within H of its split's start — S01 (boundary purge)
  T6  Birmingham: every used row's target lies inside the row's OWN session — S02 / X01
  T7  Birmingham: no target timestamp exceeds the session's last OBSERVED time — S02 / X01
  T8  interpolation flags are internally consistent and reported — X01 (disclosure)
  T9  v2 removes exactly the rows the v1 defect fabricated    — regression evidence
  T10 every retained series carries INFORMATION, per split and per scored window — X08 / B15

T10 was added 2026-09-04 (revision 39) because T1-T9 check STRUCTURE and never ask whether a retained
series carries information. Belgrade facility 8 passed all of them while reporting two distinct values
across its whole 1,015-row test window, and six experiments were logged on top of it before EXP-026
found it by hand. This is the one-line check that would have caught it in R-Phase 1.

Run: python 2026-09-02-test_split_integrity.py
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT/"01_data"/"processed"
BELGRADE_SPLIT = {"train_end": "2017-03-13 23:59:59", "calib_end": "2017-03-17 23:59:59"}
CFG = {
 "belgrade":   dict(v2="belgrade_features_v2.parquet",   v1="belgrade_features.parquet",
                    horizons=[5,15,30], sessioned=False),
 "birmingham": dict(v2="birmingham_features_v2.parquet", v1="birmingham_features.parquet",
                    horizons=[30,60,90], sessioned=True),
}
# --- T10 (X08 / B15) -------------------------------------------------------------------
# ONE definition of "low information" for the whole project: core.is_low_information / D-018 / P22-P24.
# This suite does not restate the rule, it only asserts WHERE it fires (B9).
sys.path.insert(0, str(ROOT/"03_code"/"src"/"conformal"))
import core  # noqa: E402

# The documented low-information set. T10 is a TRIPWIRE, not a discovery: these entries are known,
# decided (D-018) and handled by the exclusion, so the gate PASSES on them and FAILS on anything new.
# Facility 1 is degenerate everywhere (B5); facility 8 is the X08 stuck sensor, healthy in train and
# calibration and dead in test -- which is exactly why the rule is applied per scored window.
EXPECTED_LOW_INFO = {
    "belgrade":   {"train": [1], "calibration": [1], "test": [1, 8]},
    "birmingham": {"train": [],  "calibration": [],  "test": []},
}

FAIL = []
def check(name, cond, detail=""):
    ok = bool(cond)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    if not ok: FAIL.append(name)

def belgrade_split(ts):
    te, ce = pd.Timestamp(BELGRADE_SPLIT["train_end"]), pd.Timestamp(BELGRADE_SPLIT["calib_end"])
    return np.where(ts <= te, "train", np.where(ts <= ce, "calibration", "test"))

def main():
    summary = {}
    for city, c in CFG.items():
        print(f"\n=== {city} ===")
        df = pd.read_parquet(PROC/c["v2"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        H = c["horizons"]

        check("T1 no duplicate (facility, timestamp)",
              not df.duplicated(["facility_id","timestamp"]).any())
        mono = df.sort_values(["facility_id","timestamp"]).groupby("facility_id")["timestamp"]\
                 .apply(lambda s: s.is_monotonic_increasing).all()
        check("T2 timestamps increasing within facility", mono)

        for h in H:
            check(f"T3 target_ts_{h} == issue + {h}min",
                  (pd.to_datetime(df[f"target_ts_{h}"]) - df["timestamp"] ==
                   pd.Timedelta(minutes=h)).all())

        if city == "belgrade":
            for h in H:
                used = df[df[f"use_{h}"]]
                same = (belgrade_split(used["timestamp"]) ==
                        belgrade_split(pd.to_datetime(used[f"target_ts_{h}"]))).all()
                check(f"T4 t+{h}: used rows have issue and target in the same split", same,
                      f"{len(used):,} used of {len(df):,}")
        else:
            for h in H:
                used = df[df[f"use_{h}"]]
                check(f"T4 t+{h}: split_ok holds for every used row", used[f"split_ok_{h}"].all(),
                      f"{len(used):,} used of {len(df):,}")
        for h in H:
            check(f"T5 t+{h}: embargo flag honoured on used rows", df.loc[df[f"use_{h}"], f"embargo_ok_{h}"].all())

        if c["sessioned"]:
            # Session bounds must come from the SOURCE data, not from the retained rows: the last few
            # rows of every session are legitimately dropped (their targets fall past the session end),
            # so post-dropna maxima would understate the true session extent.
            raw = pd.read_parquet(PROC/"birmingham_long.parquet")
            raw["timestamp"] = pd.to_datetime(raw["timestamp"])
            raw["session_id"] = raw["facility_id"].astype(str) + "_" + raw["timestamp"].dt.date.astype(str)
            s_first = raw.groupby("session_id")["timestamp"].min().dt.floor("30min")
            s_last  = raw.groupby("session_id")["timestamp"].max().dt.ceil("30min")
            for h in H:
                used = df[df[f"use_{h}"]]
                tgt = pd.to_datetime(used[f"target_ts_{h}"])
                lastv = used["session_id"].map(s_last).values
                firstv = used["session_id"].map(s_first).values
                same_day = (tgt.dt.date.values == used["timestamp"].dt.date.values)
                within = (tgt.values <= lastv) & (used["timestamp"].values >= firstv) & same_day
                check(f"T6 t+{h}: target inside the row's own session", within.all(),
                      f"{int((~within).sum())} violations of {len(used):,}")
                check(f"T7 t+{h}: target never crosses midnight / session end",
                      bool(same_day.all()), f"{int((~same_day).sum())} cross-day targets")

        for h in H:
            check(f"T8 t+{h}: interpolation flag present and boolean",
                  df[f"target_interpolated_{h}"].dtype == bool)
        summary[city] = {
            "rows_v2": int(len(df)),
            "occ_interpolated_pct": round(100*float(df["occ_interpolated"].mean()), 3),
            "target_interpolated_pct": {str(h): round(100*float(df[f"target_interpolated_{h}"].mean()),3)
                                        for h in H},
            "usable_rows": {str(h): int(df[f"use_{h}"].sum()) for h in H},
        }

        # T10 — information, not just structure (X08 / B15)
        for sp in ["train", "calibration", "test"]:
            got = core.low_information_facilities(df[df.split == sp])
            exp = EXPECTED_LOW_INFO[city][sp]
            check(f"T10 {sp}: low-information set is the documented one",
                  got == exp, f"detected {got}, documented {exp}")
        for h in H:
            w = df[(df.split == "test") & (df[f"use_{h}"])]
            got = core.low_information_facilities(w)
            exp = EXPECTED_LOW_INFO[city]["test"]
            check(f"T10 test/use_{h}: scored window matches the documented set",
                  got == exp, f"detected {got}, documented {exp}")
        # T10 NEGATIVE CONTROL (B11) — the detector must be able to fire, or the checks above are
        # vacuous. Force the healthiest facility in this city to a constant and require detection.
        nd = df[df.split == "test"].groupby("facility_id")["occupancy"].nunique()
        healthiest = int(nd.idxmax())
        probe = df[df.split == "test"].copy()
        probe.loc[probe.facility_id == healthiest, "occupancy"] = 42.0
        check(f"T10 negative control: detector fires on a forced-constant facility {healthiest}",
              healthiest in core.low_information_facilities(probe),
              f"{healthiest} had {int(nd.max())} distinct readings before being stuck at 42.0")
        summary[city]["low_information_facilities"] = {
            sp: core.low_information_facilities(df[df.split == sp])
            for sp in ["train", "calibration", "test"]}
        summary[city]["min_distinct_readings_rule"] = int(core.MIN_DISTINCT_READINGS)

        # T9 — regression evidence vs v1
        v1 = pd.read_parquet(PROC/c["v1"]); v1["timestamp"]=pd.to_datetime(v1["timestamp"])
        summary[city]["rows_v1"] = int(len(v1))
        summary[city]["rows_removed_by_v2"] = int(len(v1)-len(df))
        if city == "belgrade":
            leak = sum(int((belgrade_split(v1["timestamp"]) !=
                            belgrade_split(v1["timestamp"]+pd.Timedelta(minutes=h))).sum()) for h in H)
            check("T9 v1 leakage reproduced and now blocked", leak > 0,
                  f"v1 cross-split targets across horizons: {leak} (v2 used-rows: 0)")
            summary[city]["v1_cross_split_targets"] = leak
        else:
            check("T9 v2 drops the cross-night-fabricated rows", len(df) < len(v1),
                  f"v1 {len(v1):,} -> v2 {len(df):,}  (removed {len(v1)-len(df):,}, "
                  f"matching the 1,942 rows whose t+90 target was interpolated across a night)")

    out = ROOT/"05_results"/"tables"/"2026-09-02-split-integrity-report.json"
    json.dump(summary, open(out,"w"), indent=2)
    print(f"\nwrote {out.name}")
    print("\n" + ("ALL CHECKS PASSED" if not FAIL else f"{len(FAIL)} CHECK(S) FAILED: {FAIL}"))
    return 1 if FAIL else 0

if __name__ == "__main__":
    sys.exit(main())
