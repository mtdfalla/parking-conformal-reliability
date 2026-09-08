# PRESPECIFICATION — the spatial leg (§5.5) recomputed on the paper's evaluation base

**Written 2026-09-07, revision 49, BEFORE the script was written or run.** Fifteenth prespecification.
Authority: D-030 (this session), taken under the author's go of 2026-09-07. Trigger: locating the ESM figure
makers showed that the two live spatial scripts select facilities by `coords ∩ (train-window occupancy std ≥ 5)`,
which is **not** the population every other reported statistic uses.

## 1. The defect, stated exactly

| | population | n | roster |
|---|---|---|---|
| every other reported statistic | `dynamic` ∧ ¬`core.low_information_facilities` (X08, D-018) | 21 | 2–7, 9, 11–24 |
| §5.5 as published | `facility_coords` ∧ (train std ≥ 5.0) | 21 | 2–9, 11–23 |

The two sets are both 21 and are **not the same 21**: the published spatial set **retains facility 8**, the X08
dead sensor, and omits facility 24 (no coordinates). T1 states the low-information rule applies to *every reported
statistic*; §5.5 is the exception, and it is the section reporting a **null**. A near-constant series correlates
with nothing, so retaining it biases toward the null we report — the direction that matters for a null claim.
**D-028 item 5 and the EXP-037 addendum both assert "the same 21 facilities"; that assertion is wrong** and is
corrected by this entry (the record correction is D-030 and section 8 of the revision-49 record).

**The correct population is the intersection: `evaluation base ∧ has coordinates` = 20 facilities**
(2–7, 9, 11–23). Facility 24 has no coordinates and can never enter a spatial analysis; that is a data limit,
stated, not a choice.

## 2. What is NOT wrong, measured before assuming it

- **The v1/v2 question is closed as a non-issue.** Both scripts read `belgrade_features.parquet` (v1) while the
  rest of the pipeline reads `_v2`. For Belgrade the two are **identical on every column these scripts use**
  (`facility_id, timestamp, split, occupancy, y_t+15min` and all 15 features; 92,544 rows; identical split sizes).
  v2 adds only the `use_*` flag columns. Checked this session, column by column, before any conclusion was drawn.
- **The common test index does not depend on the roster.** 1,018 common test timestamps on both the 21- and the
  20-facility roster, identical sets. Residuals are defined on every test row, so the stored pairwise residual
  correlations are **exactly** correct for the 20-facility subset — no refit is needed and none is done.

## 3. Method — read-only re-aggregation, no model is fitted

`03_code/src/spatial/2026-09-07-spatial-exclusion-base.py`. Reads only manifest-listed artifacts:
`05_results/tables/2026-06-21-spatial-corr-distance.csv` (210 pairs), `2026-06-21-spatial-facility-uncertainty.csv`
(per-facility `lon`, `lat`, `mean_aci_halfwidth`), `01_data/processed/belgrade_features_v2.parquet` (the
`occupancy` column of the test split only, for the raw co-movement). Recomputes Moran's I (inverse-haversine
weights, 999 permutations), the Mantel test (9,999 permutations), the naive Spearman, the near/far means and the
mean pairwise raw-occupancy correlation, with the **same estimators, the same seed (42) and the same permutation
counts** as the live scripts — only the roster differs. Writes no tracker (defect-7 class). Writes one new table,
`05_results/tables/2026-09-07-spatial-statistics-exclusion-base.csv`, carrying **both rosters**, so the negative
control ships beside the result. The frozen 2026-06-21 tables are read and never written; the live spatial
scripts and `2026-09-06-spatial-statistics.csv` are untouched (A21).

**Known limit, stated rather than fixed:** `mean_aci_halfwidth` is the fixed-γ = 0.05 ACI half-width the pre-audit
script computed. The paper's ACI elsewhere uses a calibration-selected γ. Moran's I is a spatial-autocorrelation
test on a per-facility *uncertainty descriptor*, not a coverage claim, so the descriptor is named precisely in the
text instead of being regenerated; regenerating it is a refit and would be its own experiment.

## 4. Predictions

**P1 (negative control, B7/B11 — the gate).** Run on the published 21-facility roster the script reproduces every
published value to 6 dp: Mantel r **−0.128609**, p **0.151300**; naive ρ **−0.121024**, p **0.080156**; mean
pairwise residual correlation **0.007124**; near <2 km **0.025100**; far >5 km **−0.004525**. If any of these
misses, the re-aggregation is wrong and the run is abandoned, not adjusted.

**P2.** On the 20-facility base: Mantel r **−0.128386**, p **0.139300**; naive ρ **−0.132960**, p **0.067436**;
mean pairwise residual correlation **0.012282**; near **0.037066**; far **0.002155**. *Baseline named (C20): these
five were computed read-only from `2026-06-21-spatial-corr-distance.csv` on 2026-09-07, before this script was
written, as the sensitivity check that triggered D-030; the script must reproduce them.*

**P3 (genuinely unknown — not computed before this run).** Moran's I on 20 facilities stays **non-significant
(p > 0.05)**; sign and magnitude unpredicted. Baseline: the published 21-facility value is −0.008668, p 0.905.

**P4 (genuinely unknown).** The mean pairwise raw-occupancy correlation on 20 facilities **rises** above the
published 0.516474, because facility 8 is near-constant and correlates weakly with everything. Magnitude
unpredicted. Baseline: 0.516474 on 21 facilities, 1,018 common timestamps.

**P5.** The null survives on the correct base: **neither** Moran's I **nor** the Mantel test reaches p ≤ 0.05.
If either does, §5.5's conclusion changes and the contradiction protocol applies — the finding is surfaced and the
section is rewritten to what is true, not to what was planned.

**P6.** Two runs produce a byte-identical CSV (fixed seed, fixed permutation counts, sorted output).

## 5. What changes downstream

`2026-09-06-typeset-tables.py` reads the new CSV into `typeset.json`; `2026-09-06-apply-rphase7.py` rewrites
§5.5's sentence to the 20-facility values and **names the population and the coordinate limit** in the text;
the ESM spatial figure is drawn from the same table on the same roster. This is a **table change**, so the
session owes a manifest re-cut, a package rebuild and a **full clean-room run** (C13, C18; gate = exit code,
zero failures, and the regenerated / checks counts restated from EXP-039's 66 / 318 plus this session's additions).
