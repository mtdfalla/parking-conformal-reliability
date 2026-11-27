#!/usr/bin/env python3
"""EXP-045 arm A4 (external-audit finding T024): the X08 re-aggregation of the 2026-11-25 trust/abstain run.

The trust/abstain leg of `2026-09-04-x08-reaggregate.py`, run on `2026-11-25-trust-abstain-per-facility.csv`.
It imports that script and calls its own `exclusion_sets` and `via_original` with the 2026-11-25 successor's
`write_summary`, so no aggregation is re-implemented here. Outputs:
  05_results/tables/2026-11-25-x08-trust-abstain-control.csv   (filter off)
  05_results/tables/2026-11-25-x08-trust-abstain-excl.csv      (filter on, the base ESM Table S6 reads)
Gate (as `03_code/tests/2026-09-04-x08-control-check.py` does for the 2026-09-03 tables): the control table
equals `2026-11-25-trust-abstain-summary.csv` on every numeric column to 4 dp, or the script exits nonzero.
That gate is a wiring check only: both sides come from one `write_summary` on one frame (59b review note 10).
Revision 61 adds a control that shares neither the exclusion code nor the aggregation:
  * the exclusion set is re-derived from the rule as the data dictionary states it (fewer than 10 distinct
    occupancy readings on the t+15 test rows), without `core.low_information_facilities`, and must be equal;
  * the filtered table is re-aggregated from the per-facility rows with a plain groupby (no `write_summary`,
    no `via_original`) and must equal the written `-excl` table on every shared column at its printed precision;
  * negative control: the same re-aggregation without the exclusion must DIFFER from the `-excl` table, and the
    `-excl` table must count fewer facilities than the control table, so the comparison can fail.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB = HERE.parents[2] / "05_results" / "tables"
spec = importlib.util.spec_from_file_location("x08_reagg", HERE / "2026-09-04-x08-reaggregate.py")
x08 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(x08)

PER = "2026-11-25-trust-abstain-per-facility.csv"
SCRIPT = "2026-11-25-trust-abstain.py"


def main():
    ex = x08.exclusion_sets()
    bel15 = ex[("belgrade", "use_15")]
    print(f"[x08-trust] exclusion set belgrade/use_15 = {bel15}")
    for tag, drop in (("control", []), ("excl", bel15)):
        x08.via_original(SCRIPT, PER, TAB / f"2026-11-25-x08-trust-abstain-{tag}.csv", drop,
                         lambda m, per: m.write_summary(per))
    a = pd.read_csv(TAB / "2026-11-25-trust-abstain-summary.csv")
    b = pd.read_csv(TAB / "2026-11-25-x08-trust-abstain-control.csv")
    keys = ["method", "commit_target"]
    m = a.merge(b, on=keys, how="outer", suffixes=("_a", "_b"), indicator=True)
    bad = int((m._merge != "both").sum())
    for c in [c for c in a.columns if c not in keys and pd.api.types.is_numeric_dtype(a[c])]:
        d = np.abs(m[f"{c}_a"] - m[f"{c}_b"])
        bad += int(((d > 5e-5) | (m[f"{c}_a"].isna() != m[f"{c}_b"].isna())).sum())
    if bad:
        sys.exit(f"[x08-trust] CONTROL FAIL: {bad} cell(s) of the filter-off table differ from the summary")
    print(f"[x08-trust] CONTROL PASS: filter-off table equals 2026-11-25-trust-abstain-summary.csv ({len(a)} rows)")
    independent_control(bel15)
    print("[x08-trust] ALL DONE")


def independent_control(bel15):
    """Revision 61 (59b review note 10): exclusion and aggregation re-derived without the code under test."""
    d = pd.read_parquet(x08.ROOT / "01_data" / "processed" / "belgrade_features_v2.parquet",
                        columns=["facility_id", "split", "use_15", "occupancy"])
    te = d[(d.split == "test") & d.use_15]
    rule = sorted(int(f) for f, k in te.groupby("facility_id").occupancy.nunique().items() if k < 10)
    if rule != sorted(int(f) for f in bel15):
        sys.exit(f"[x08-trust] INDEPENDENT CONTROL FAIL: rule gives {rule}, exclusion_sets gives {bel15}")
    per = pd.read_csv(TAB / PER)
    elig = per[(per.dynamic == True) & (per.degenerate != True) & (per.method != "SKIPPED-thin")]
    elig = elig.dropna(subset=["commit_rate"])
    dp = {"commit_rate": 3, "MAE_cars": 3, "MAE_pct": 3, "committed_PICP": 4, "committed_MPIW": 2}

    def agg(drop):
        g = elig[~elig.facility_id.isin(drop)].groupby(["method", "commit_target"])
        out = g[list(dp)].mean()
        out["n_facilities"] = g.facility_id.nunique()
        return out

    def differs(mine, path):
        t = pd.read_csv(path).set_index(["method", "commit_target"])
        if sorted(t.index) != sorted(mine.index):
            return len(set(t.index) ^ set(mine.index))
        n = int((t.n_facilities != mine.loc[t.index, "n_facilities"]).sum())
        for c, k in dp.items():
            n += int((np.abs(t[c] - mine.loc[t.index, c].round(k)) > 0.5 * 10.0 ** -k).sum())
        return n

    excl = TAB / "2026-11-25-x08-trust-abstain-excl.csv"
    n_on, n_off = differs(agg(bel15), excl), differs(agg([]), excl)
    fewer = int(pd.read_csv(excl).n_facilities.max()) < int(pd.read_csv(TAB / "2026-11-25-x08-trust-abstain-control.csv").n_facilities.max())
    print(f"[x08-trust] INDEPENDENT CONTROL: rule exclusion {rule}; re-aggregation with it: {n_on} cell(s) differ; "
          f"without it (negative control): {n_off} cell(s) differ; excl counts fewer facilities: {fewer}")
    if rule == [] or n_on or not n_off or not fewer:
        sys.exit("[x08-trust] INDEPENDENT CONTROL FAIL")
    print("[x08-trust] INDEPENDENT CONTROL PASS")


if __name__ == "__main__":
    main()
