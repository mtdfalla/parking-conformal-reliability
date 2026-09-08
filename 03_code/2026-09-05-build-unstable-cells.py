#!/usr/bin/env python3
"""Generate `00_admin/2026-09-05-unstable-cells.csv` — the registry of cells MEASURED to be
nondeterministic across processes, with every observed value and its observation count.

Branch S applied to a CELL rather than to a whole artifact. The 58 never-regenerated reference tables are
reported with a stated reason instead of as failures; this does the same for a cell that a from-scratch
run legitimately reproduces at either of two values, so a replicator is not told a defect in their
environment is a defect in ours.

WHAT THIS IS NOT. It is not a relaxed tolerance. `verify.py` excuses a registered cell ONLY when its
value equals one of the values recorded here; any third value is a failure. It never excuses a column in
the `exact` class, so PICP stays gated — and PICP is identical across every observation, which is why the
instability is reportable at all. An unregistered cell that differs is still a failure.

The registry is GENERATED from `05_results/tables/2026-09-05-agaci-x08-bistability-probe.csv`, the
append-only probe that runs the RandomForest -> residuals -> agaci_ewa path for facility 8 with
`fit_ngboost` never called. It is never typed by hand, so it cannot quietly acquire a cell that should
have been reproducible.

Usage: python 03_code/2026-09-05-build-unstable-cells.py
"""
from __future__ import annotations
import csv
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "05_results" / "tables" / "2026-09-05-agaci-x08-bistability-probe.csv"
OUT = ROOT / "00_admin" / "2026-09-05-unstable-cells.csv"

MECHANISM = ("facility 8 (X08) reports two distinct occupancy values across its whole test window, so the "
             "outcome sits exactly ON an expert interval bound many times; the RandomForest's n_jobs=-1 "
             "aggregation order (A8) perturbs yhat at ~1e-14, one tie flips, and the ACI alpha trajectory "
             "diverges from that step. Measured: the width branch is a function of the tie count "
             "(78 ties -> the lower value, 77 ties -> the higher). Survives pinning OMP/OpenBLAS/MKL "
             "threads to 1, so the driver is joblib forest aggregation, not BLAS.")
NO_MOVE = ("no reported number moves: D-018 excludes facility 8 from every published figure, and 6.9e-5 "
           "spread over the 21-facility published base is 3e-6, invisible at the 4 dp the summaries carry")

def main():
    d = pd.read_csv(PROBE)
    rows = []
    for col in ("MPIW", "Winkler"):
        # Cluster the observations before recording them. Repeated runs of the SAME branch still differ
        # at ~1e-15 (A8's thread-reduction noise, far below the 1e-12 width tolerance), so the raw set of
        # floats would list four "values" where two branches exist. Group at 9 dp -- 1e-9 is three orders
        # coarser than the jitter and four orders finer than the 6.9e-5 gap between the branches -- and
        # record the MEAN of each cluster as its canonical value.
        vals = d[col].round(9).value_counts().sort_index()
        if len(vals) < 2:
            continue
        exact = [float(d.loc[d[col].round(9) == v, col].mean()) for v in vals.index]
        rows.append(dict(
            file="2026-09-03-e3-belgrade-per-facility.csv",
            match="arm=A3_v2_daychunk;facility_id=8;method=AgACI-style",
            column=col,
            observed_values="|".join(f"{v:.15g}" for v in exact),
            n_observations=int(len(d)),
            counts_per_value="|".join(f"{int(c)}" for c in vals.values),
            picp_identical_across_observations=bool(d.PICP.nunique() == 1),
            mechanism=MECHANISM,
            evidence="EXP-033 (B26), EXP-036; probe 05_results/tables/2026-09-05-agaci-x08-bistability-probe.csv",
            reported_number_moved=NO_MOVE))
    if not rows:
        raise SystemExit("no cell showed more than one observed value — registry NOT written")
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"[unstable-cells] wrote {len(rows)} registered cell(s) from {len(d)} probe observations -> {OUT.name}")
    for r in rows:
        print(f"    {r['file']} :: {r['match']} :: {r['column']} = {r['observed_values']} "
              f"(counts {r['counts_per_value']})")

if __name__ == "__main__":
    main()
