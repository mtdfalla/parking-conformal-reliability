#!/usr/bin/env python3
"""Positive control for EXP-045 arm A5 (T039), run after 2026-11-25-orthogonal-partition-check.py.

1. The successor's four shipped partitions (time_of_day, day_of_week, occupancy_tercile and the single
   draw random_5, made by the old generator call) reproduce every row of the shipped
   2026-09-03-orthogonal-partition-cells.csv: n_cell and the covered count (PICP x n_cell) exactly,
   PICP and Cramer's V to 1e-12, MPIW to 1e-9. The float tolerances absorb two documented artefacts:
   the resume path re-reads earlier facilities from CSV with the default parser (last-bit drift), and
   the RF predictions under n_jobs=-1 sum trees in thread order (MPIW drift of order 1e-14).
2. On the paper base the single draw reproduces the shipped X08 summary (sd to 4 dp, dispersion ratio
   to 2 dp, the 2.05 and 2.04 of Table IV).
3. Every balanced draw has, per facility, exactly the cell sizes of the ToD partition.
4. Negative control: the comparison in 1 FAILS when a balanced draw is put in place of random_5.
Exit 0 only if 1 to 3 pass and 4 fails as it must.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "05_results" / "tables"
OLD = pd.read_csv(TAB / "2026-09-03-orthogonal-partition-cells.csv", float_precision="round_trip")
NEW = pd.read_csv(TAB / "2026-11-25-exp045-partition-random200-cells.csv", float_precision="round_trip")
KEY = ["facility_id", "partition", "cell", "method"]
VAL = ["n_cell", "covered", "dynamic", "degenerate"]
TOL = {"PICP": 1e-12, "cramers_v_vs_tod": 1e-12, "MPIW": 1e-9}
for _d in (OLD, NEW):
    _d["covered"] = (_d.PICP * _d.n_cell).round()


def same(old: pd.DataFrame, new: pd.DataFrame) -> tuple[bool, str]:
    m = old.merge(new, on=KEY, how="outer", suffixes=("_o", "_n"), indicator=True)
    if (m._merge != "both").any():
        return False, f"{int((m._merge != 'both').sum())} unmatched rows"
    for v in VAL:
        a, b = m[f"{v}_o"], m[f"{v}_n"]
        eq = (a == b) | (a.isna() & b.isna())
        if not eq.all():
            return False, f"{v}: {int((~eq).sum())} rows differ"
    worst = {}
    for v, tol in TOL.items():
        d = (m[f"{v}_o"] - m[f"{v}_n"]).abs()
        worst[v] = float(d.max())
        if (d > tol).any():
            return False, f"{v}: {int((d > tol).sum())} rows beyond {tol}"
    return True, f"{len(m)} rows: counts identical, max abs diff {worst}"


fail = []
shipped = ["time_of_day", "day_of_week", "occupancy_tercile", "random_5", "(none)"]
ok, msg = same(OLD, NEW[NEW.partition.isin(shipped)])
print(f"[1] shipped partitions vs 2026-09-03 cells: {'PASS' if ok else 'FAIL'} ({msg})")
ok or fail.append(1)

x08 = pd.read_csv(TAB / "2026-09-04-x08-orthogonal-summary-excl.csv")
per = pd.read_csv(TAB / "2026-11-25-exp045-partition-random200.csv")
for part in ["random_5", "time_of_day"]:
    for _, r in x08[x08.partition == part].iterrows():
        p = per[(per.partition == part) & (per.method == r.method)].iloc[0]
        a = (round(p.sd_PICP, 4) == r.sd_PICP and round(p.dispersion_ratio_vs_splitCP, 2) == r.dispersion_ratio_vs_splitCP
             and p.n_cells == r.n_cells and p.cells_below_080 == r.cells_below_080)
        print(f"[2] {part} {r.method}: sd {p.sd_PICP!r} vs {r.sd_PICP}, ratio {p.dispersion_ratio_vs_splitCP!r} "
              f"vs {r.dispersion_ratio_vs_splitCP}: {'PASS' if a else 'FAIL'}")
        a or fail.append(2)

tod = NEW[(NEW.partition == "time_of_day") & (NEW.method == "split-CP")]
sizes = {f: sorted(g.n_cell) for f, g in tod.groupby("facility_id")}
rb = NEW[NEW.partition.str.startswith("rbal_") & (NEW.method == "split-CP")]
bad = [(f, p) for (f, p), g in rb.groupby(["facility_id", "partition"]) if sorted(g.n_cell) != sizes[f]]
nd = rb.partition.nunique()
print(f"[3] balanced cell sizes: {nd} draws x {rb.facility_id.nunique()} facilities, "
      f"{len(bad)} mismatches: {'PASS' if not bad and nd == 200 else 'FAIL'}")
(not bad and nd == 200) or fail.append(3)

sub = NEW[NEW.partition == "rbal_000"].copy()
sub["partition"] = "random_5"
sub["cell"] = sub.cell.map(lambda c: c)  # labels differ in name and content
old_r5 = OLD[OLD.partition == "random_5"]
ok4, msg4 = same(old_r5, sub)
# a relabelled comparison as well: map each rbal_000 cell onto r0..r4 in order, so names cannot be the reason
order = {c: f"r{i}" for i, c in enumerate(["p_night", "p_am_rush", "p_midday", "p_pm_rush", "p_evening"])}
sub2 = sub.assign(cell=sub.cell.map(order))
ok4b, msg4b = same(old_r5, sub2)
neg = (not ok4) and (not ok4b)
print(f"[4] negative control (balanced draw in place of random_5): comparison "
      f"{'FAILS as required' if neg else 'PASSES (control is broken)'} ({msg4}; relabelled: {msg4b})")
neg or fail.append(4)

print("ALL PASS" if not fail else f"FAILED: {fail}")
sys.exit(1 if fail else 0)
