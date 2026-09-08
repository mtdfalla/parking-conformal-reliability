#!/usr/bin/env python3
"""EXP-027 — the X08 batch: re-aggregate every affected summary under the D-018 exclusion.

WHAT THIS DOES AND WHY IT IS NOT A SHORTCUT
-------------------------------------------
D-018 adopts a data-quality exclusion (fewer than `core.MIN_DISTINCT_READINGS` distinct occupancy
readings in the scored window). Every script in scope fits each facility INDEPENDENTLY -- own model,
own calibration split, own gamma -- and no summary statistic in any of them pools rows across
facilities (verified by reading each script's own `write_summary` before this was written; see
`04_experiments/2026-09-04-x08-batch-PRESPECIFICATION.md` section 3). Excluding a facility therefore
changes only which rows enter the aggregate. Re-aggregating the logged per-facility CSVs is EXACTLY
equivalent to refitting with the exclusion applied, and strictly better, because it carries no RF
thread-reduction drift (A8) and no MAPIE between-fit variation (A13): the exclusion is the only thing
that differs between the two runs.

ONE DEFINITION, NOT SEVEN (B9)
------------------------------
The exclusion comes from `core.low_information_facilities` and nowhere else. Four of the six summaries
are produced by IMPORTING the original script and calling its own `write_summary` with the output
constant redirected -- so this file does not re-implement their aggregation and cannot drift from it.
The core-headline and E3 summaries have NO writer anywhere in the tree (they were produced ad hoc in an
earlier stage -- itself a provenance finding), so their aggregation is written here and is validated
ONLY by the negative control below.

THE NEGATIVE CONTROL IS THE GATE (B11)
--------------------------------------
`--filter off` must reproduce every logged summary number to 4 dp. If it does not, this file does not
match the original aggregation and its filtered output is worthless -- that experiment falls back to a
genuine rerun of its script. Nothing is patched into agreement.

Nothing here overwrites a logged file. Outputs are written to `2026-09-04-x08-*-{control,excl}.csv`.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
sys.path.insert(0, str(HERE))
import core  # noqa: E402


def log(m):
    print(f"[x08-reagg] {m}", flush=True)


# --------------------------------------------------------------------------------------
# The exclusion set, computed from the DATA, per scored window. Never hardcoded.
# --------------------------------------------------------------------------------------

def exclusion_sets() -> dict[tuple[str, str], list]:
    """{(dataset, use_flag): [facility_id, ...]} judged on that window's TEST rows only."""
    out = {}
    for ds, flags in (("belgrade", ["use_5", "use_15", "use_30"]),
                      ("birmingham", ["use_30", "use_60", "use_90"])):
        d = pd.read_parquet(ROOT / "01_data" / "processed" / f"{ds}_features_v2.parquet")
        te = d[d.split == "test"]
        for f in flags:
            out[(ds, f)] = core.low_information_facilities(te[te[f]])
    return out


def threshold_gap(ds: str, flag: str) -> pd.Series:
    """Distinct-reading counts per facility on the scored window -- the B16 evidence, republished."""
    d = pd.read_parquet(ROOT / "01_data" / "processed" / f"{ds}_features_v2.parquet")
    te = d[(d.split == "test") & (d[flag])]
    return te.groupby("facility_id")["occupancy"].nunique().sort_values()


# --------------------------------------------------------------------------------------
# Reuse of the original scripts' own aggregation
# --------------------------------------------------------------------------------------

def load_script(fname: str):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_")[:-3], HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def via_original(fname: str, per_csv: str, out_csv: Path, drop: list, caller) -> None:
    """Call the original script's write_summary on the filtered per-facility frame."""
    mod = load_script(fname)
    per = pd.read_csv(TAB / per_csv)
    if drop:
        per = per[~per.facility_id.isin(drop)]
    mod.SUM = out_csv
    caller(mod, per)
    log(f"wrote {out_csv.name}  (aggregation: {fname}::write_summary, dropped={drop})")


# --------------------------------------------------------------------------------------
# The two summaries with no writer in the tree
# --------------------------------------------------------------------------------------

CORE_ROWS = [("belgrade", "y_t+15min"), ("birmingham", "y_t+60min")]


def core_headline(drop_map: dict, out_csv: Path) -> None:
    out = []
    for city, hz in CORE_ROWS:
        d = pd.read_csv(TAB / f"2026-09-02-core-{city}-gcal-per-facility.csv")
        d = d[(d.horizon == hz) & (d.level == 0.90) & (d.dynamic)]
        drop = drop_map.get(city, [])
        if drop:
            d = d[~d.facility_id.isin(drop)]
        for meth in ["split-CP", "CQR", "ACI", "ACQR"]:
            s = d[d.method == meth]
            if s.empty:
                continue
            out.append(dict(
                city=city, horizon=hz, method=meth,
                PICP=float(s.PICP.mean()), std=float(s.PICP.std()),
                MPIW=float(s.MPIW.mean()), Winkler=float(s.Winkler.mean()),
                ci_contains=float(((s.picp_ci_lo <= 0.90) & (s.picp_ci_hi >= 0.90)).mean()),
                safe=float((s.picp_ci_lo >= 0.88).mean()), n=int(s.facility_id.nunique())))
    pd.DataFrame(out).to_csv(out_csv, index=False)
    log(f"wrote {out_csv.name}  (aggregation: local, validated by the control)")


E3_ROWS = [("belgrade", "y_t+15min"), ("birmingham", "y_t+60min")]
E3_METHODS = ["ACI-crosscheck", "AgACI-style", "EnbPI", "NGBoost", "NGBoost-conformal"]
E3_ARCHIVED = {("belgrade", "AgACI-style"): (0.9330, 0.0090),
               ("belgrade", "EnbPI"): (0.8874, 0.0680),
               ("belgrade", "NGBoost"): (0.7600, 0.0867),
               ("birmingham", "AgACI-style"): (0.9066, 0.0199),
               ("birmingham", "EnbPI"): (0.8448, 0.0782),
               ("birmingham", "NGBoost"): (0.3837, 0.1575)}


def e3_summary(drop_map: dict, out_csv: Path) -> None:
    out = []
    for ds, hz in E3_ROWS:
        d = pd.read_csv(TAB / f"2026-09-03-e3-{ds}-per-facility.csv")
        d = d[(d.arm == "A3_v2_daychunk") & (d.dynamic) & (d.degenerate != True)
              & (d.status == "ok")]
        drop = drop_map.get(ds, [])
        if drop:
            d = d[~d.facility_id.isin(drop)]
        for meth in E3_METHODS:
            s = d[d.method == meth]
            if s.empty:
                continue
            a = E3_ARCHIVED.get((ds, meth), (np.nan, np.nan))
            out.append(dict(
                dataset=ds, horizon=hz, level=0.9, method=meth,
                n_facilities=int(s.facility_id.nunique()),
                mean_PICP=round(float(s.PICP.mean()), 4),
                sd_PICP=round(float(s.PICP.std()), 4),
                mean_MPIW=round(float(s.MPIW.mean()), 4),
                mean_Winkler=round(float(s.Winkler.mean()), 4),
                frac_below_0p90=round(float((s.PICP < 0.90).mean()), 4),
                worst_facility_PICP=round(float(s.PICP.min()), 4),
                archived_mean_PICP=a[0], archived_sd_PICP=a[1]))
    pd.DataFrame(out).to_csv(out_csv, index=False)
    log(f"wrote {out_csv.name}  (aggregation: local, validated by the control)")


# --------------------------------------------------------------------------------------

def run(apply_filter: bool) -> None:
    tag = "excl" if apply_filter else "control"
    ex = exclusion_sets()
    log(f"exclusion sets from core.low_information_facilities "
        f"(MIN_DISTINCT_READINGS={core.MIN_DISTINCT_READINGS}): "
        + ", ".join(f"{k[0]}/{k[1]}={v}" for k, v in ex.items()))

    if apply_filter:
        bel15 = ex[("belgrade", "use_15")]
        drop_map = {"belgrade": bel15, "birmingham": ex[("birmingham", "use_60")]}
    else:
        bel15 = []
        drop_map = {"belgrade": [], "birmingham": []}

    core_headline(drop_map, TAB / f"2026-09-04-x08-core-headline-{tag}.csv")
    e3_summary(drop_map, TAB / f"2026-09-04-x08-e3-summary-{tag}.csv")

    via_original("2026-09-03-base-learner-robustness.py",
                 "2026-09-03-base-learner-robustness-per-facility.csv",
                 TAB / f"2026-09-04-x08-base-learner-{tag}.csv", bel15,
                 lambda m, per: m.write_summary(per))
    via_original("2026-09-03-tod-conditional.py",
                 "2026-09-03-tod-facility-bucket.csv",
                 TAB / f"2026-09-04-x08-tod-summary-{tag}.csv", bel15,
                 lambda m, per: m.write_summary(per, 30))
    via_original("2026-09-03-orthogonal-partition-check.py",
                 "2026-09-03-orthogonal-partition-cells.csv",
                 TAB / f"2026-09-04-x08-orthogonal-summary-{tag}.csv", bel15,
                 lambda m, per: m.write_summary(per))
    via_original("2026-09-03-trust-abstain.py",
                 "2026-09-03-trust-abstain-per-facility.csv",
                 TAB / f"2026-09-04-x08-trust-abstain-{tag}.csv", bel15,
                 lambda m, per: m.write_summary(per))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", choices=["on", "off"], required=True,
                    help="'off' is the negative control: it must reproduce the logged summaries")
    ap.add_argument("--gap", action="store_true", help="print the B16 threshold-gap evidence")
    a = ap.parse_args()
    if a.gap:
        for ds, fl in (("belgrade", "use_15"), ("birmingham", "use_60")):
            g = threshold_gap(ds, fl)
            log(f"{ds}/{fl} distinct-reading counts, lowest 5: {g.head(5).to_dict()}")
    run(a.filter == "on")
    log("ALL DONE")


if __name__ == "__main__":
    main()
