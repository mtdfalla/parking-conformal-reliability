#!/usr/bin/env python3
"""
EXP-031 (A) — the ESM capability table for the allocation null.

Prespecified in `04_experiments/2026-09-04-rphase5-PRESPECIFICATION.md`, section 1.1 and section 3 gate 1.

WHY THIS SCRIPT EXISTS AT ALL. The (A) sentence asserts two numbers that no CSV in the tree carries:
the PEAK healthy occupancy as a fraction of capacity (98.7% / 99.8%), and the event count under the
allocation design's OWN definition of full, `cap - y < 1`. `2026-09-04-vignette-overflow-capability.csv`
carries only `ratio >= threshold` rows. Under the project's rule that every manuscript number traces to a
CSV, (A) cannot be written from the existing table. This script adds exactly those two columns.

NO NEW EXPERIMENT. Same inputs, same base, same scored quantity (`y_t+15min`), same capacity proxy CSV.
GATED: every cell of the 2026-09-04 table must reproduce to 4 dp BEFORE the new columns are read (B17).
The 2026-09-04 file is NOT overwritten; this supersedes it by date.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))

TAB = ROOT / "05_results" / "tables"
OLD = TAB / "2026-09-04-vignette-overflow-capability.csv"
OUT = TAB / "2026-09-04-esm-overflow-capability.csv"
HZ, HOURS = "y_t+15min", (12, 19)
WINDOWS = {"weekday": (20, 21), "weekend": (18, 19)}
THRESHOLDS = [0.90, 0.95, 0.97, 0.98, 0.99, 0.995, 1.00]
SAFETY = 1


def log(*a): print(*a, flush=True)


def build():
    df = pd.read_parquet(ROOT / "01_data" / "processed" / "belgrade_features_v2.parquet")
    df["ts"] = pd.to_datetime(df.timestamp); df = df[df.use_15]
    cap = pd.read_csv(TAB / "2026-09-04-vignette-capacity-proxy.csv").set_index("facility_id")
    te = df[df.split == "test"]
    rows = []
    for wname, days in WINDOWS.items():
        w = te[te.ts.dt.day.isin(days) & (te.ts.dt.hour >= HOURS[0]) & (te.ts.dt.hour < HOURS[1])]
        w = w[w.facility_id.isin(cap.index)]
        for label, sub in (("healthy base (fac 8 excluded)", w[w.facility_id != 8]),
                           ("facility 8 only", w[w.facility_id == 8])):
            if not len(sub):
                continue
            c = cap.loc[sub.facility_id, "cap_train"].values
            y = sub[HZ].values
            ratio = y / c
            peak_i = int(np.argmax(ratio))
            n_event = int(((c - y) < SAFETY).sum())          # the design's OWN definition of "full"
            for th in THRESHOLDS:
                sel = ratio >= th
                rows.append(dict(
                    window=wname, population=label, threshold_frac_of_cap=th,
                    n_facility_slots=len(ratio), n_at_or_above=int(sel.sum()),
                    pct_at_or_above=round(float(sel.mean()) * 100, 3),
                    facilities=";".join(map(str, sorted(set(sub.facility_id.values[sel].astype(int).tolist())))),
                    # ---- the two columns the ESM sentence needs and the 2026-09-04 table lacks ----
                    peak_pct_of_cap=round(float(ratio.max()) * 100, 3),
                    peak_facility_id=int(sub.facility_id.values[peak_i]),
                    n_event_cap_minus_y_lt_1=n_event,
                    pct_event_cap_minus_y_lt_1=round(n_event / len(ratio) * 100, 3),
                    event_definition="capacity - y_t+15min < 1 space (the allocation design's own rule)",
                    capacity_source="training window only (D01)",
                ))
    return pd.DataFrame(rows)


def gate(new: pd.DataFrame) -> int:
    """Every cell of the logged table must reproduce to 4 dp before any new column is read."""
    old = pd.read_csv(OLD)
    keys = ["window", "population", "threshold_frac_of_cap"]
    m = old.merge(new, on=keys, suffixes=("_old", "_new"), how="outer", indicator=True)
    fails = 0; checks = 0
    if (m._merge != "both").any():
        log(f"  FAIL: row-set mismatch — {int((m._merge != 'both').sum())} rows"); fails += 1
    for col in ["n_facility_slots", "n_at_or_above", "pct_at_or_above"]:
        a, b = m[f"{col}_old"].values.astype(float), m[f"{col}_new"].values.astype(float)
        bad = ~np.isclose(a, b, atol=1e-4, equal_nan=True)
        checks += len(a); fails += int(bad.sum())
        log(f"  {col:22s} {len(a) - int(bad.sum())}/{len(a)} match to 4 dp")
    a = m["facilities_old"].fillna("").astype(str).values
    b = m["facilities_new"].fillna("").astype(str).values
    bad = a != b
    checks += len(a); fails += int(bad.sum())
    log(f"  {'facilities':22s} {len(a) - int(bad.sum())}/{len(a)} match exactly")
    log(f"  GATE: {checks} checks, {fails} failures")
    return fails


def main():
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--overwrite", action="store_true",
                     help="permit rewriting this script's own output (used by run_all.sh)")
    _a = _ap.parse_args()
    new = build()
    log("[gate] reproducing 2026-09-04-vignette-overflow-capability.csv before reading anything new")
    if gate(new) != 0:
        log("GATE FAILED — nothing written."); sys.exit(1)
    if OUT.exists() and not _a.overwrite:
        # 2026-09-05 (revision 44, EXP-035): a bare `sys.exit(1)` here makes this step
        # NON-IDEMPOTENT. `run_all.sh` runs single-shot steps on every pass, so a replicator
        # whose run is interrupted and restarted -- the resumable design invites exactly that --
        # fails here on a file THEIR OWN run wrote. The guard protects the repository's logged
        # artifacts and is kept for a bare invocation; the runner passes --overwrite, because in
        # the shipped package 05_results/tables/ is the replicator's own output directory.
        # Found by the clean-room run, not by reading the code (C12).
        log(f"REFUSING to overwrite {OUT.name}; delete or rename it first, or pass --overwrite.")
        sys.exit(1)
    new.to_csv(OUT, index=False)
    log(f"[out] {OUT.name}  ({len(new)} rows)")
    key = new[new.threshold_frac_of_cap == 1.00][
        ["window", "population", "n_facility_slots", "peak_pct_of_cap", "peak_facility_id",
         "n_event_cap_minus_y_lt_1"]]
    log("\n[the (A) sentence's numbers, now traceable]")
    log(key.to_string(index=False))
    log("\nALL DONE")


if __name__ == "__main__":
    main()
