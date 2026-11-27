#!/usr/bin/env python3
"""
EXP-042 sensitivities S1 and S2, and the three counters, read from the canonical runner's outputs (EXP-043).

No model is fitted here. Everything is re-aggregation of tables the 2026-11-22 runner wrote.

S1  like-for-like rows (EXP-042 addendum 2, D-038 item 2). Birmingham, t+60, level 0.90, the four primary
    methods, on the v3 rows whose (facility, timestamp) were usable at t+60 in the v2 table, beside the
    main result. Answers whether the v2-to-v3 movement comes from the anchor rule or from the added rows.
S2  anchor age (EXP-042 addendum 1). Birmingham, every horizon, level 0.90, the four primary methods: the
    main run's per-row coverage split by `occ_carried` (anchor carried one step vs observed). No refit.
    Statistic: the mean over facilities of the facility's coverage in that stratum, beside the pooled row
    coverage and the row and facility counts. A facility with no row in a stratum is absent from it.
COUNTERS  `n_inverted` (final bands empty under core.finalize_band), `n_alpha_clipped` (adaptive level on
    a projection bound) and `n_q_saturated` (quantile at the pool maximum), summed by variant, city,
    horizon, level and method, each beside its denominator (test steps).

Both sensitivities are labelled post hoc wherever they are reported and are reported whichever way they
fall (EXP-042 section 9, forbidden move 3).

Refuses to run if a counter column is missing, or if the per-row coverage does not reproduce the
per-facility PICP of the same run exactly: a stratified number from rows that do not add up to the
headline would be a different population.

Outputs: 05_results/tables/2026-11-23-birmingham-s1-s2.csv, 2026-11-23-core-counters.csv

Revision 59b (2026-11-25): `--city birmingham` (the public-data path of run_all.sh) writes the S1/S2 table
and stops before the counters table, which holds both cities. The default, `--city both`, is unchanged.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
ADAPTIVE = ["ACI", "ACQR"]
LEVEL = 0.90


def log(m):
    print(f"[sens] {m}", flush=True)


def die(m):
    log(f"REFUSED: {m}")
    sys.exit(1)


def per(tab: Path, tag: str) -> pd.DataFrame:
    f = tab / f"2026-11-22-core-{tag}-per-facility.csv"
    if not f.exists():
        die(f"{f.name} missing")
    d = pd.read_csv(f)
    return d[d.method.isin(METHODS)].copy()


def summary(d: pd.DataFrame) -> dict:
    p = d.PICP.to_numpy(float)
    return dict(n_fac=int(d.facility_id.nunique()), n_test_total=int(d.n_test.sum()),
                mean_PICP=float(p.mean()), sd_PICP=float(p.std(ddof=1)), worst_PICP=float(p.min()),
                worst_facility=int(d.loc[d.PICP.idxmin(), "facility_id"]),
                mean_MPIW=float(d.MPIW.mean()), mean_Winkler=float(d.Winkler.mean()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tab-dir", default=str(ROOT / "05_results" / "tables"))
    ap.add_argument("--city", choices=["both", "birmingham"], default="both",
                    help="birmingham: write the S1/S2 table only (the counters table needs both cities)")
    a = ap.parse_args()
    tab = Path(a.tab_dir)

    main_b = per(tab, "birmingham-v3-gcal")
    s1_b = per(tab, "birmingham-v3-S1-gcal")
    rows_f = tab / "2026-11-22-core-birmingham-v3-gcal-rows-L90.csv"
    if not rows_f.exists():
        die(f"{rows_f.name} missing")
    rows = pd.read_csv(rows_f)

    # ---- the per-row file must reproduce the per-facility PICP exactly
    m = main_b[np.isclose(main_b.level, LEVEL)]
    r = rows.groupby(["facility_id", "horizon", "method"]).covered.agg(["mean", "size"]).reset_index()
    j = m.merge(r, on=["facility_id", "horizon", "method"], how="left")
    bad = j["mean"].isna() | (np.abs(j["mean"] - j.PICP) > 1e-12) | (j["size"] != j.n_test)
    if bad.any():
        die(f"per-row coverage does not reproduce {int(bad.sum())} per-facility cell(s)")
    if (rows.occ_carried < 0).any():
        die("Birmingham per-row file carries no occ_carried flag")
    log(f"per-row file reproduces all {len(j)} per-facility cells at level 0.90")

    dyn = set(m.loc[m.dynamic.astype(bool), "facility_id"])
    out = []
    # ---- S1
    for variant, d in (("main", main_b), ("S1 v2-rows", s1_b)):
        s = d[(d.horizon == "y_t+60min") & np.isclose(d.level, LEVEL) & d.facility_id.isin(dyn)]
        for meth in METHODS:
            x = s[s.method == meth]
            if x.empty:
                continue
            out.append(dict(analysis="S1", variant=variant, horizon="y_t+60min", stratum="all",
                            method=meth, pooled_row_coverage=np.nan, **summary(x)))
    # ---- S2
    rr = rows[rows.facility_id.isin(dyn)]
    for hz in sorted(rr.horizon.unique()):
        for meth in METHODS:
            for flag, name in ((0, "anchor observed"), (1, "anchor carried one step")):
                x = rr[(rr.horizon == hz) & (rr.method == meth) & (rr.occ_carried == flag)]
                if x.empty:
                    continue
                fac = x.groupby("facility_id").covered.mean()
                out.append(dict(analysis="S2", variant="main", horizon=hz, stratum=name, method=meth,
                                n_fac=int(fac.size), n_test_total=int(len(x)),
                                mean_PICP=float(fac.mean()), sd_PICP=float(fac.std(ddof=1)),
                                worst_PICP=float(fac.min()), worst_facility=int(fac.idxmin()),
                                mean_MPIW=np.nan, mean_Winkler=np.nan,
                                pooled_row_coverage=float(x.covered.mean())))
    pd.DataFrame(out).to_csv(tab / "2026-11-23-birmingham-s1-s2.csv", index=False)
    log(f"wrote 2026-11-23-birmingham-s1-s2.csv ({len(out)} rows)")

    if a.city == "birmingham":
        log("--city birmingham: 2026-11-23-core-counters.csv holds both cities and is not written")
        log("ALL DONE")
        return 0

    # ---- counters
    cnt = []
    for city in ("belgrade", "birmingham"):
        for tag, variant in ((f"{city}-v3-gcal", "calibrated gamma"), (f"{city}-v3", "fixed gamma"),
                             (f"{city}-v3-S1-gcal", "S1 v2-rows")):
            f = tab / f"2026-11-22-core-{tag}-per-facility.csv"
            if not f.exists():
                if variant == "S1 v2-rows" and city == "belgrade":
                    continue
                die(f"{f.name} missing")
            d = per(tab, tag)
            for c in ("n_inverted", "n_alpha_clipped", "n_q_saturated"):
                if c not in d.columns:
                    die(f"{f.name} has no {c} column")
            if d.n_inverted.isna().any():
                die(f"{f.name}: n_inverted missing on {int(d.n_inverted.isna().sum())} row(s)")
            for (hz, lv, meth), g in d.groupby(["horizon", "level", "method"]):
                ad = meth in ADAPTIVE
                if ad and (g.n_alpha_clipped.isna().any() or g.n_q_saturated.isna().any()):
                    die(f"{f.name}: an adaptive counter is missing for {meth} {hz} {lv}")
                cnt.append(dict(variant=variant, city=city, horizon=hz, level=lv, method=meth,
                                n_fac=int(g.facility_id.nunique()), test_steps=int(g.n_test.sum()),
                                n_inverted=int(g.n_inverted.sum()),
                                n_alpha_clipped=(int(g.n_alpha_clipped.sum()) if ad else np.nan),
                                n_q_saturated=(int(g.n_q_saturated.sum()) if ad else np.nan)))
    pd.DataFrame(cnt).to_csv(tab / "2026-11-23-core-counters.csv", index=False)
    log(f"wrote 2026-11-23-core-counters.csv ({len(cnt)} rows)")
    log("ALL DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
