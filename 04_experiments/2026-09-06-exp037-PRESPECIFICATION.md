# PRESPECIFICATION — EXP-037, the pooled-vs-worst-facility pilot, DESCRIPTIVE HALF ONLY

**Written 2026-09-06, revision 48, BEFORE the script was run.** Twelfth prespecification. Authority: revision-45
record §12.3 (which reserved the number and named B25 as the reason), D-025 (which reserved it a second time),
the author's decision on 2026-09-06 (revision 48): *"Yes, descriptive half only"*. D-016 (no new data), D-018
(the exclusion), D-020/D-027 (the display-item budget is closed and is **not** reopened here — this experiment
produces a CSV and at most one sentence, never a display item).

## 0. What this is, and what it is not

The revision-45 pilot re-aggregated, **in chat**, the 0.90-level per-facility results across 24 configurations
and found that 23 of 24 sit within 0.02 of nominal on mean facility coverage while their worst facility ranges
0.763–0.888. Those numbers are unquotable until a script writes them to a CSV that names its population
(**B25**). This experiment is that script. **It is descriptive.** It reports counts, ranges and extremes. It
does **not** compute the pooled-vs-worst correlation, its p-value, or any test — the inferential half stays
unrun by the author's decision, because the 24 units share facilities and the pilot's p = 0.076 would need
facility-clustered inference that nobody has designed.

**The confound the pilot found is honoured by construction:** every statistic is computed **within one
nominal level**; nothing is pooled across levels (the unconditioned correlation was +0.844 — a level effect,
not a finding).

## 1. Population — named here, and written into the CSV

Source tables: `05_results/tables/2026-09-02-core-{belgrade,birmingham}-gcal-per-facility.csv` (the R-Phase 3b
core run; the same files `2026-09-04-x08-reaggregate.py` builds T2's primary rows from).

Filter, in this order: `dynamic == True`; the X08 exclusion from `core.low_information_facilities` applied to
the **test** rows of the horizon's `use_*` flag (never hardcoded — Belgrade facility 8 is expected to be the only
exclusion, on every horizon); configurations with fewer than **10** remaining facilities are dropped (none are
expected to be).

Units: city × horizon × method × **nominal level** — 2 cities, 3 horizons each (Belgrade t+5/15/30; Birmingham
t+30/60/90), 4 primary methods (split-CP, CQR, ACI, ACQR), 4 levels (0.80, 0.85, 0.90, 0.95) = **96 rows**;
the **24 rows at 0.90** are the pilot's population. (The revision-45 record wrote "2 cities × 5 horizons × 4
methods"; the arithmetic that gives 24 is 6 city-horizons × 4 methods, and that is what the pilot was.)

## 2. Outputs — two CSVs, both per-unit flushed, both resumable

**(a) `05_results/tables/2026-09-06-exp037-pooled-vs-worst.csv`**, one row per unit:
`city, horizon, level, method, n_facilities, excluded_facilities, mean_facility_PICP, pooled_PICP_obs_weighted,
sd_PICP, worst_facility_id, worst_facility_PICP, best_facility_PICP, mean_minus_worst, n_within_002,
mean_within_002 (bool), n_facilities_below_080, source_file`.
"Mean facility PICP" is the unweighted mean over facilities — the quantity T2 reports; the observation-weighted
pooled PICP is given beside it so a reader can see they differ by < 0.01.

**(b) `05_results/tables/2026-09-06-exp037-ncal-picp-correlation.csv`** — the source for the §5.8 sentence
*"the correlation between calibration size and per-facility coverage is null in every city-method-horizon
combination tested (all |ρ| ≤ 0.17, p ≥ 0.40)"*, which D-025 computed in chat and which has **no CSV** (the
S47 record §8 list of non-CSV numbers missed it). One row per city × method ∈ {split-CP, ACI} × horizon at
level 0.90 (12 rows, the twelve tests D-025 names): `n_facilities, n_cal_min, n_cal_max, n_cal_distinct,
spearman_rho, spearman_p, note`. Where `n_cal` is constant across facilities the correlation is **undefined**
and the row says so — it is not reported as zero.

## 3. Predictions, fixed before running

| # | prediction | source |
|---|---|---|
| P1 | 96 rows; every configuration keeps ≥ 10 facilities; Belgrade n = 21 and Birmingham n = 28 on every row | D-018 |
| P2 | at level 0.90: **23 of 24** rows have mean facility PICP within ±0.02 of 0.90 | pilot |
| P3 | at level 0.90: worst-facility PICP ranges **0.763–0.888** across the 24 rows | pilot |
| P4 | at level 0.90: the range of mean facility PICP across the 24 rows is ≈ **0.031**; the range of worst-facility PICP is ≈ **0.125** (about four times wider) | pilot |
| P5 | at level 0.90, Belgrade t+15 and Birmingham t+60 rows reproduce T2 exactly: mean PICP, sd and worst facility equal `2026-09-04-x08-core-headline-excl.csv` / `2026-09-04-T3prime-two-level-inference.csv` to 4 dp | negative control (B7): if this fails the script's aggregation is wrong, not T2 |
| P6 | **Belgrade `n_cal` is constant within each horizon** (764 / 760 / 754), so the six Belgrade correlation rows are **undefined**; the six Birmingham rows have |ρ| ≤ 0.17 and p ≥ 0.40 | D-025 §1 and its own first bullet |

**P6 is the one that matters for the text.** If it holds, §5.8's sentence as written ("in every city-method-
horizon combination tested") overstates what exists: on Belgrade there is no variation to correlate, which is
the *stronger* form of the point (identical calibration counts) and the sentence is rewritten to say exactly
that. If Birmingham exceeds the bounds, the sentence is rewritten to the measured values — never trimmed.

## 4. What the result may change, and what it may not

- **May change:** one sentence in §5.3 or §8 (a descriptive count: "across 24 city-horizon-method
  configurations at the 0.90 level, N sit within 0.02 of nominal on mean facility coverage while their worst
  facility ranges a–b"), read from CSV (a) by the generator; the §5.8 sentence, read from CSV (b).
- **May not change:** any table, any figure, the display-item set (D-027), any inferential claim. No
  correlation or p-value from this experiment enters the manuscript.

## 5. Gate

The script is resumable (`--budget`, per-unit flush, `ALL DONE` only when both CSVs hold their full row
counts — C18: the completion marker covers **every** artifact). Success = both files written, P1 and P5 hold
exactly. P2–P4 and P6 are recorded as found; a miss is a finding about the pilot, not a reason to rerun.
