#!/usr/bin/env python3
"""
X08 — stuck-sensor / closure-encoded-as-value diagnostic for the Belgrade record.

FOUND 2026-09-03 (revision 38) while verifying the rolling-origin F2 result, not by looking for it.
The archived EXP-013 headline "split-CP collapses in fold F2 (std 0.161, Winkler 34.9)" reproduced
almost exactly on corrected code and v2 features -- and then turned out to be one facility whose
sensor had died.

WHAT IT IS
----------
`Garaza "Vukov spomenik"` (facility_id 8) behaves normally 4-14 March (12-64 distinct readings/day),
then reports EXACTLY 0.0 for 15-18 March and EXACTLY 109.0 -- apparently its capacity -- on 20 March.
Over its whole 1,015-row MAIN test window it takes exactly TWO distinct values: 0.0 (44.5%) and
109.0 (55.5%). The pattern is present in `01_data/raw/belgrade_RAW.csv`, so it is a property of the
source export, NOT something the v1 or v2 feature pipeline introduced.

This is the same defect class as S02/X01, and the same one D-016 cites as a reason to reject the
Luxembourg file ("it encodes closure as zero occupancy"). It was not caught in R-Phase 1 because the
integrity suite checks split boundaries, embargoes and interpolation -- not whether a retained series
carries any information.

WHY IT MATTERS, AND IN WHICH DIRECTION
--------------------------------------
Facility 8 is the WORST-covered facility for EnbPI and NGBoost in EXP-025, so it inflates the
baselines' failure and therefore FLATTERS our comparative claim. Correcting it moves numbers AGAINST
us -- the second time in this revision that an audit-style fix has done so (LESSONS_LOG B12).

THE PROPOSED RULE IS A DATA-QUALITY RULE, NOT AN OUTCOME RULE. It is stated on the inputs only and
is blind to any method's performance: exclude a facility-window carrying fewer than
MIN_DISTINCT distinct occupancy readings. The threshold is not delicate -- facility 1 has 1 distinct
value, facility 8 has 2, and the next lowest facility has 64 -- so anything in [3, 60] selects the
same two facilities. That gap is reported below so the choice can be seen to be non-arbitrary.

Usage:  python 2026-09-03-stuck-sensor-diagnostic.py
Output: 05_results/tables/2026-09-03-stuck-sensor-diagnostic.csv
        05_results/tables/2026-09-03-stuck-sensor-impact.csv
Modifies nothing else. Regenerates no logged experiment.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"
MIN_DISTINCT = 10          # any value in [3, 60] gives the identical selection; see the gap report
STUCK_RUN = 12             # >=12 consecutive identical 5-min readings = >=1 hour


def log(m): print(f"[x08] {m}", flush=True)


def run_lengths(s: pd.Series) -> np.ndarray:
    v = s.values
    brk = np.r_[True, v[1:] != v[:-1]]
    gid = np.cumsum(brk)
    counts = pd.Series(gid).value_counts()
    return pd.Series(gid).map(counts).values


def main():
    d = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    d["ts"] = pd.to_datetime(d.timestamp)
    d = d.sort_values(["facility_id", "ts"])

    rows = []
    for fid, g in d.groupby("facility_id"):
        g = g.copy()
        g["runlen"] = run_lengths(g.occupancy)
        for sp in ["train", "calibration", "test"]:
            s = g[g.split == sp]
            if not len(s):
                continue
            rows.append(dict(
                facility_id=fid, facility_name=s.facility_name.iloc[0], split=sp, n_rows=len(s),
                n_distinct=int(s.occupancy.nunique()),
                pct_modal_value=round(100 * float(s.occupancy.value_counts(normalize=True).iloc[0]), 2),
                pct_in_stuck_run=round(100 * float((s.runlen >= STUCK_RUN).mean()), 2),
                pct_zero=round(100 * float((s.occupancy == 0).mean()), 2),
                max_run=int(s.runlen.max()),
                flagged=bool(s.occupancy.nunique() < MIN_DISTINCT)))
    diag = pd.DataFrame(rows)
    diag.to_csv(TAB / "2026-09-03-stuck-sensor-diagnostic.csv", index=False)

    te = diag[diag.split == "test"].sort_values("n_distinct")
    flagged = sorted(te[te.flagged].facility_id.tolist())
    log(f"flagged facilities (test window, n_distinct < {MIN_DISTINCT}): {flagged}")
    log("distinct-value gap, lowest five facilities in the test window:")
    for _, r in te.head(5).iterrows():
        log(f"    fac {int(r.facility_id):2d}  n_distinct={int(r.n_distinct):5d}  "
            f"modal={r.pct_modal_value:5.1f}%  {r.facility_name}")

    # ---- impact on already-logged numbers. RECOMPUTED FROM THE LOGGED PER-FACILITY CSVs.
    #      Nothing is re-fitted and no logged file is rewritten.
    impact = []
    srcs = [("core_t+15", TAB / "2026-09-02-core-belgrade-gcal-per-facility.csv",
             dict(horizon="y_t+15min")),
            ("e3_v2", TAB / "2026-09-03-e3-belgrade-per-facility.csv",
             dict(arm="A3_v2_daychunk"))]
    for label, path, filt in srcs:
        if not path.exists():
            continue
        t = pd.read_csv(path)
        for k, v in filt.items():
            if k in t.columns:
                t = t[t[k] == v]
        t = t.dropna(subset=["PICP"])
        for m, g in t.groupby("method"):
            h = g[~g.facility_id.isin(flagged)]
            impact.append(dict(
                source=label, method=m,
                n_all=len(g), n_excl=len(h),
                mean_PICP_all=round(g.PICP.mean(), 4), mean_PICP_excl=round(h.PICP.mean(), 4),
                sd_PICP_all=round(g.PICP.std(ddof=0), 4), sd_PICP_excl=round(h.PICP.std(ddof=0), 4),
                min_PICP_all=round(g.PICP.min(), 4), min_PICP_excl=round(h.PICP.min(), 4),
                sd_reduction_pct=round(100 * (1 - h.PICP.std(ddof=0) / g.PICP.std(ddof=0)), 1)
                if g.PICP.std(ddof=0) > 0 else np.nan))

    roll = TAB / "2026-09-03-rolling-origin-belgrade.csv"
    if roll.exists():
        r = pd.read_csv(roll)
        r = r[(r.method != "SKIPPED-thin")]
        r = r[(r.gamma_mode == "calibrated") | (r.gamma_mode.isna()) | (r.gamma_mode == "n/a")]
        for fold, g in r.groupby("fold"):
            for m, gg in g.groupby("method"):
                a = gg[~gg.facility_id.isin([1])]           # degenerate only (status quo)
                b = gg[~gg.facility_id.isin(flagged)]       # proposed rule
                impact.append(dict(
                    source=f"rolling_{fold}", method=m, n_all=len(a), n_excl=len(b),
                    mean_PICP_all=round(a.PICP.mean(), 4), mean_PICP_excl=round(b.PICP.mean(), 4),
                    sd_PICP_all=round(a.PICP.std(ddof=0), 4), sd_PICP_excl=round(b.PICP.std(ddof=0), 4),
                    min_PICP_all=round(a.PICP.min(), 4), min_PICP_excl=round(b.PICP.min(), 4),
                    sd_reduction_pct=round(100 * (1 - b.PICP.std(ddof=0) / a.PICP.std(ddof=0)), 1)
                    if a.PICP.std(ddof=0) > 0 else np.nan))

    imp = pd.DataFrame(impact)
    imp.to_csv(TAB / "2026-09-03-stuck-sensor-impact.csv", index=False)
    log(f"wrote diagnostic ({len(diag)} rows) and impact ({len(imp)} rows) CSVs")
    pd.set_option("display.width", 200)
    print("\n=== IMPACT OF THE PROPOSED EXCLUSION ON ALREADY-LOGGED NUMBERS ===")
    print(imp.to_string(index=False))


if __name__ == "__main__":
    main()
