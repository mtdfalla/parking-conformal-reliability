#!/usr/bin/env python3
"""
The writer that three summary tables never had (EXP-043, revision 56b).

WHY THIS FILE EXISTS
--------------------
Three tables that live gates and a display item read were produced ad hoc in earlier stages and had no
writer anywhere in the tree:
  * `2026-09-02-corrected-headline-gcal.csv`, the reference of the `phase4-inference` gate and of the x08
    negative control (core headline, four primary methods);
  * `2026-09-03-e3-summary.csv`, the reference of the x08 negative control for the E3 baselines;
  * `2026-09-04-phase4-safe-mechanism.csv`, read by row G of the protocol-sensitivity table.
Every Birmingham number and the gamma-calibrated Belgrade ACI and ACQR numbers move in the v3 run, so a
gate that compares a fresh run with those archived files would fail by construction. This script writes
the three tables from the run's own per-facility outputs, and the gates compare with them instead.

IT IS A SEPARATE IMPLEMENTATION ON PURPOSE
------------------------------------------
`2026-09-04-x08-reaggregate.py` and `2026-09-04-phase4-inference.py` aggregate the same rows with their own
code. This file uses a grouped aggregation and shares no function with them, so agreement between the two
is evidence, not a tautology.

BRIDGE CONTROL (run once, at promotion)
---------------------------------------
`--bridge` reads the 2026-09-02 core tables and the v2 Birmingham feature table, writes to `--out-dir`, and
compares each output with its archived file to 4 dp. It must pass before any gate is re-pointed here: it
is what shows this writer computes the same statistic the archived files hold.

Outputs (05_results/tables unless --out-dir):
    2026-11-23-core-headline-gcal.csv      columns of 2026-09-02-corrected-headline-gcal.csv
    2026-11-23-e3-summary.csv              columns of 2026-09-03-e3-summary.csv
    2026-11-23-phase4-safe-mechanism.csv   columns of 2026-09-04-phase4-safe-mechanism.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
PROC = ROOT / "01_data" / "processed"
sys.path.insert(0, str(HERE))
import core  # noqa: E402

PRIMARY = [("belgrade", "y_t+15min", "use_15"), ("birmingham", "y_t+60min", "use_60")]
CORE_METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
E3_METHODS = ["ACI-crosscheck", "AgACI-style", "EnbPI", "NGBoost", "NGBoost-conformal"]
# Archived means of the pre-audit E3 run, carried as labels in the summary exactly as the archived table
# carries them. They are inputs to no computation here.
E3_ARCHIVED = {("belgrade", "AgACI-style"): (0.9330, 0.0090), ("belgrade", "EnbPI"): (0.8874, 0.0680),
               ("belgrade", "NGBoost"): (0.7600, 0.0867), ("birmingham", "AgACI-style"): (0.9066, 0.0199),
               ("birmingham", "EnbPI"): (0.8448, 0.0782), ("birmingham", "NGBoost"): (0.3837, 0.1575)}
SAFE, OVER, NOMINAL = 0.88, 0.92, 0.90
TOL = 5e-5


def log(m):
    print(f"[summaries] {m}", flush=True)


def x08_drop(feat: Path, flag: str) -> list:
    d = pd.read_parquet(feat)
    te = d[(d.split == "test") & (d[flag].astype(bool))]
    return list(core.low_information_facilities(te))


def headline(core_tpl: str) -> pd.DataFrame:
    """Dynamic facilities, level 0.90, no X08 exclusion: the archived headline's population."""
    out = []
    for city, hz, _ in PRIMARY:
        d = pd.read_csv(TAB / core_tpl.format(city=city))
        d = d[(d.horizon == hz) & (d.level == NOMINAL) & (d.dynamic.astype(bool))
              & d.method.isin(CORE_METHODS)].copy()
        d["contains"] = (d.picp_ci_lo <= NOMINAL) & (d.picp_ci_hi >= NOMINAL)
        d["is_safe"] = d.picp_ci_lo >= SAFE
        g = d.groupby("method").agg(PICP=("PICP", "mean"), std=("PICP", "std"), MPIW=("MPIW", "mean"),
                                    Winkler=("Winkler", "mean"), ci_contains=("contains", "mean"),
                                    safe=("is_safe", "mean"), n=("facility_id", "nunique"))
        for m in CORE_METHODS:
            if m in g.index:
                r = g.loc[m]
                out.append(dict(city=city, horizon=hz, method=m, PICP=r.PICP, std=r["std"], MPIW=r.MPIW,
                                Winkler=r.Winkler, ci_contains=float(r.ci_contains), safe=float(r.safe),
                                n=int(r.n)))
    return pd.DataFrame(out)


def e3(e3_tpl: str) -> pd.DataFrame:
    out = []
    for city, hz, _ in PRIMARY:
        d = pd.read_csv(TAB / e3_tpl.format(city=city))
        keep = ((d.arm == "A3_v2_daychunk") & d.dynamic.astype(bool) & (d.degenerate != True)
                & (d.status == "ok"))
        d = d[keep]
        for m in E3_METHODS:
            s = d[d.method == m]
            if s.empty:
                continue
            a = E3_ARCHIVED.get((city, m), (np.nan, np.nan))
            p = s.PICP.to_numpy(float)
            out.append(dict(dataset=city, horizon=hz, level=0.9, method=m,
                            n_facilities=int(s.facility_id.nunique()),
                            mean_PICP=round(float(np.mean(p)), 4), sd_PICP=round(float(np.std(p, ddof=1)), 4),
                            mean_MPIW=round(float(s.MPIW.to_numpy(float).mean()), 4),
                            mean_Winkler=round(float(s.Winkler.to_numpy(float).mean()), 4),
                            frac_below_0p90=round(float(np.mean(p < NOMINAL)), 4),
                            worst_facility_PICP=round(float(np.min(p)), 4),
                            archived_mean_PICP=a[0], archived_sd_PICP=a[1]))
    return pd.DataFrame(out)


def safe_mechanism(core_tpl: str, feats: dict) -> pd.DataFrame:
    """Dynamic, X08-excluded facilities at level 0.90: what a facility's PICP must be to pass the bound."""
    out = []
    for city, hz, flag in PRIMARY:
        drop = x08_drop(feats[city], flag)
        d = pd.read_csv(TAB / core_tpl.format(city=city))
        d = d[(d.horizon == hz) & (d.level == NOMINAL) & (d.dynamic.astype(bool))
              & (~d.facility_id.isin(drop))]
        for m in CORE_METHODS:
            s = d[d.method == m]
            if s.empty:
                continue
            gap = float(np.median(s.PICP.to_numpy(float) - s.picp_ci_lo.to_numpy(float)))
            passers = s[s.picp_ci_lo >= SAFE]
            out.append(dict(city=city, horizon=hz, method=m, n_fac=int(s.facility_id.nunique()),
                            PICP_min=round(float(s.PICP.min()), 4),
                            PICP_median=round(float(s.PICP.median()), 4),
                            PICP_max=round(float(s.PICP.max()), 4),
                            median_point_to_lower_gap=round(gap, 4),
                            implied_PICP_needed_to_pass_SAFE=round(SAFE + gap, 4),
                            n_passing_SAFE=int(len(passers)),
                            n_passing_SAFE_that_overcover_ge_0p92=int((passers.PICP >= OVER).sum()),
                            min_PICP_among_passers=(round(float(passers.PICP.min()), 4)
                                                    if len(passers) else np.nan)))
    return pd.DataFrame(out)


def compare(new: pd.DataFrame, old: pd.DataFrame, keys: list, label: str) -> int:
    a, b = old.copy(), new.copy()
    for k in keys:
        a[k] = a[k].astype(str); b[k] = b[k].astype(str)
    m = a.merge(b, on=keys, how="outer", suffixes=("_old", "_new"), indicator=True)
    fails = int((m._merge != "both").sum())
    n = 0
    for c in [c for c in old.columns if c not in keys and pd.api.types.is_numeric_dtype(old[c])]:
        x, y = m[f"{c}_old"].astype(float), m[f"{c}_new"].astype(float)
        both = x.isna() & y.isna()
        bad = (~both) & ((x - y).abs().isna() | ((x - y).abs() > TOL))
        n += int((~both).sum()); fails += int(bad.sum())
        if bad.any():
            log(f"  {label}: column {c} differs in {int(bad.sum())} row(s)")
    log(f"BRIDGE {label}: {n} values compared, {fails} failure(s)")
    return fails


def main() -> int:
    global TAB
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridge", action="store_true",
                    help="control: v2-era inputs, must reproduce the three archived tables to 4 dp")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--bham-feat", default=None, help="Birmingham feature table (bridge: the v2 table)")
    a = ap.parse_args()
    out_dir = Path(a.out_dir) if a.out_dir else TAB
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.bridge:
        core_tpl = "2026-09-02-core-{city}-gcal-per-facility.csv"
        bham = Path(a.bham_feat) if a.bham_feat else PROC / "archived-v2" / "birmingham_features_v2.parquet"
    else:
        core_tpl = "2026-11-22-core-{city}-v3-gcal-per-facility.csv"
        bham = Path(a.bham_feat) if a.bham_feat else PROC / "birmingham_features_v3.parquet"
    feats = {"belgrade": PROC / "belgrade_features_v2.parquet", "birmingham": bham}
    e3_tpl = "2026-09-03-e3-{city}-per-facility.csv"

    h, e, s = headline(core_tpl), e3(e3_tpl), safe_mechanism(core_tpl, feats)
    for df, name in ((h, "2026-11-23-core-headline-gcal.csv"), (e, "2026-11-23-e3-summary.csv"),
                     (s, "2026-11-23-phase4-safe-mechanism.csv")):
        df.to_csv(out_dir / name, index=False)
        log(f"wrote {name} ({len(df)} rows)")
    if not a.bridge:
        log("ALL DONE")
        return 0
    ref = ROOT / "05_results" / "reference"
    def arch(n):
        p = TAB / n
        return pd.read_csv(p if p.exists() else ref / n)
    f = (compare(h, arch("2026-09-02-corrected-headline-gcal.csv"), ["city", "horizon", "method"], "headline")
         + compare(e, arch("2026-09-03-e3-summary.csv"), ["dataset", "horizon", "level", "method"], "e3")
         + compare(s, arch("2026-09-04-phase4-safe-mechanism.csv"), ["city", "horizon", "method"], "safe"))
    log("BRIDGE PASS" if f == 0 else f"BRIDGE FAIL ({f})")
    return 0 if f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
