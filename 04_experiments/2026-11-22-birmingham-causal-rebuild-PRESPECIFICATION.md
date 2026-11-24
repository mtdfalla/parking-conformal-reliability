# PRESPECIFICATION — EXP-042: the Birmingham causal rebuild (v3 inputs) and its decisive check

**Written 2026-11-22, revision 55, BEFORE the v3 builder, the causality test or any scoring code was written or run.** Sixteenth prespecification.
Authority: D-036 and the "Fixed decisions" table of `00_admin/2026-11-22-audit-remediation-implementation-plan.md`. Register rows 1.1, 1.2, 1.3, 2.1, 4.1, 4.2, 3.4.
Everything measured below was read from existing artifacts (`birmingham_features_v2.parquet`, `birmingham_long.parquet`, the shipped tables). No model was fitted to write this file.

## 1. The defect, stated exactly

The v2 builder resamples each facility-day session to a 30-minute grid and calls `interpolate("time", limit=1, limit_area="inside")`. An empty grid bin between two observed bins is filled with their time-weighted mean, so the value stored at bin *t* depends on the observation in bin *t*+1. That value is used as the anchor (`occupancy`), as lags and rolling features of later rows, and as the target of earlier rows.

Why a quarter of the bins are empty: the raw feed is roughly half-hourly but its timestamps jitter around the half hour (07:59, 08:25, 08:59, 09:32). Floor-binning puts two readings in one bin and none in the next. The gaps are an artefact of the grid, not missing sensor data.

Measured on v2 (17,487 rows, 28 facilities, split 9,758 / 4,141 / 3,588): 26.27% of usable anchors interpolated. Targets interpolated at t+30 / t+60 / t+90: 26.25 / 26.82 / 25.21%.

## 2. The rule (fixed, not reopened here)

1. Same session grouping, same 30-minute grid, same bin statistic (mean of the readings inside the bin). **No interpolation anywhere.**
2. **Anchor and feature series:** the observed bin value, or, where the bin is empty, the last observed bin value carried forward **at most one grid step**. Lags and rolling features are shifts and windows of this series, exactly as in v2. A bin empty for two or more steps stays missing, and rows whose features need it are dropped, as in v2.
3. **Targets:** the observed bin value only. Never carried, never interpolated.
4. **A row is usable at horizon H only if its target at H is observed:** `use_H = split_ok_H & embargo_ok_H & target_observed_H`. Rows are kept in the table when at least one horizon is usable. Target columns are missing where unobserved.
5. Flags on every row: `occ_observed`, `occ_carried` (anchor carried one step), `anchor_age_steps` (0 or 1), `target_observed_H`. `occ_interpolated` and `target_interpolated_H` are kept as columns and are identically False, so a consumer that reads them keeps working and reports the true rate.
6. Unchanged from v2: horizons, lags, rolling windows, calendar features, `MIN_RECORDS`, clipping at zero, the split fractions and their time boundaries, the embargo, the session identity.

**Time convention, stated because the causality test depends on it:** a row at bin *t* is a forecast issued at the close of bin *t* (it may use every reading with timestamp < *t*+30 min). Its target at horizon H is the mean reading in bin *t*+H. A raw reading with timestamp >= *t*+30 min must not move any feature of row *t*.

**A limit of the rule, recorded and not acted on:** binning by nearest half hour, or as-of alignment on the raw timestamps, would lose far fewer rows than floor-binning does. That is a different builder and a different approved rule. It is not tried, in this experiment or after it, without the author.

## 3. Code and where it lives until revision 56

Every file in `03_code/src/` and `03_code/tests/` is hash-locked by `verify.py`, and a new file there fails it as unlisted. The batch is therefore **staged** in `03_code/_staging/2026-11-22-v3/`, mirroring the final paths, and promoted in revision 56 in the same step that retires the v2 builder by moving it (A19) and re-cuts the manifest (A23). No manifest-listed file is edited in revision 55. The decisive check runs the staged code from a scratch tree outside the project, with outputs outside `05_results/`.

Staged: `src/features/2026-11-22-build_features_birmingham_v3.py`; `tests/2026-11-22-test-feature-causality.py`; `src/conformal/core.py` (successor: final-band rule and counters); `src/conformal/2026-11-22-run-core-methods.py` (successor: v3 inputs, counters written to the output).

**Final-band rule (row 4.2).** After any clip, a band with lower > upper is an **empty interval**: it covers nothing, its width is zero, and for the interval score its two ends are set to their midpoint. The number of such bands is written per facility, horizon, level and method (`n_inverted`). **Clip-binding (row 4.1):** the number of test steps at which the adaptive state sits on a projection bound is written as `n_alpha_clipped`.

## 4. The causality test (rows 1.1 to 1.3), with its positive control

For each of a fixed sample of sessions (seed 42, 200 sessions, plus the auditor's synthetic case): build features from the raw session, then, for each of up to five cut bins *c*, replace every raw reading with timestamp >= *c*+30 min by a perturbed value (+50, and separately a deletion) and rebuild. **Assert that every feature, anchor and flag of every row at bins <= *c* is identical**, and that targets may differ. A second assertion: no usable row has an unobserved target.

**Positive control, run first (C29):** the same test pointed at the v2 `build_session` must FAIL. If it passes on v2 the test is blind and is fixed before it is used.

## 5. The decisive check (C5)

Birmingham, t+60 (the primary horizon), split-CP, CQR, ACI, ACQR, calibrated gamma, seed 42, pinned environment, every other setting as the canonical runner. Level 0.90 is the reported level. Device compute serial, resumable, one phase per call.

Compared against the shipped v2 values at t+60, n = 28: mean PICP 0.9066 / 0.9021 / 0.8890 / 0.8928 (split-CP / CQR / ACI / ACQR), across-facility sd 0.0513 / 0.0417 / 0.0155 / 0.0234, worst facility 0.7868 / 0.7794 / 0.8659 / 0.8537, mean Winkler 175.4 / 172.7 / 175.3 / 176.3, RF-delta RMSE 30.86 against persistence 59.32.

## 6. Predictions (each names its baseline, C20)

| # | Quantity | Prediction | Baseline it is computed from |
|---|---|---|---|
| P1 | usable rows at t+60 | 12,797 to 13,100 (train about 7,196, calibration about 3,015, test about 2,586) | v2 rows with `use_60` and an observed t+60 target = 12,797. Carry-forward fills the same single gaps interpolation filled, plus one trailing bin per session |
| P2 | facilities evaluated at t+60 | 28 of 28, none skipped as thin | smallest per-facility counts among those rows: train 197, calibration 94, test 57. The guard is 100 / 50 / 50 |
| P3 | scored rows with a carried anchor | 14 to 19% | 16.58% of those v2 rows have an interpolated anchor |
| P4 | RF-delta RMSE | rises, by 0 to 25% of 30.86. Still below persistence | the interpolated anchor carried half of the next bin |
| P5 | mean PICP at 0.90 | split-CP and CQR in [0.88, 0.93], ACI and ACQR in [0.875, 0.910] | calibration and test are rebuilt the same way, so exchangeability is no worse |
| P6 | sd(split-CP) / sd(ACI) across facilities | in [2.0, 4.5] | 3.32 on v2. Test n per facility falls from about 128 to about 97, which adds binomial noise to both |
| P7 | worst facility | split-CP below 0.85. ACI at or above 0.84 | 0.7868 and 0.8659 on v2 |
| P8 | mean Winkler | rises for all four, by 0 to 25% | follows P4 |
| P9 | causality test | 0 violations on v3. FAIL on v2 | section 4 |
| P10 | inverted final bands | 0 for split-CP and ACI. Under 0.5% of test rows for CQR and ACQR | the auditor's "nine" was never reproduced |
| P11 | clip-binding steps | under 2% of test steps for ACI and ACQR | not measured before. A guess, labelled as one |

**Sampling benchmark, reported and not a criterion:** a method with exact 0.90 coverage at every facility would show an across-facility sd of about 0.030 at n = 97 from binomial noise alone. Each method's sd is reported beside this figure.

## 7. Outcome branches, fixed now

Computed at t+60, level 0.90, over the facilities evaluated.

- **Branch R, replicates.** All of: sd(split-CP) / sd(ACI) >= 2.0. Split-CP worst facility <= 0.85. ACI worst facility exceeds split-CP worst facility by >= 0.03. ACI mean PICP in [0.875, 0.925]. Then every Birmingham number is regenerated in revision 56 and no claim sentence changes.
- **Branch W, replicates in direction, weaker.** sd ratio >= 1.25 and ACI worst facility > split-CP worst facility, with at least one Branch R condition failing. Then revision 56 proceeds, and the revision 57 edit table carries the Birmingham sentences whose adjectives the numbers no longer support. Recorded in the record.
- **Branch N, does not replicate.** sd ratio < 1.25, or ACI worst facility <= split-CP worst facility, or ACI mean PICP outside [0.86, 0.94], or fewer than 20 facilities evaluable. **STOP. Report to the author before revision 56 is spent.** D-036's reopening condition.

The 0.5160 keystone and every Belgrade number are outside this experiment. Belgrade inputs carry 0% interpolated anchors.

## 8. Block-bootstrap sensitivity (row 3.4), prespecified here, run in the clean-room cycle

One ESM row. Belgrade, t+15, the four primary methods, level 0.90, evaluation base of 21 facilities. Statistic: the mean over facilities of facility PICP. Resampling: moving blocks of 36 consecutive common test timestamps (3 hours), drawn **synchronously**, the same blocks for every facility, so cross-facility dependence at a timestamp is preserved. B = 10,000, seed 42, percentile 90% interval. Rows sorted by timestamp then facility before resampling (C15).
**Rule, fixed now:** the row is reported whichever way it falls. If the split-CP lower bound is below 0.88, the keystone sentence gains "under facility-clustered inference". The test of record does not change (register section 4, item 8). The auditor's [0.8786, 0.9237] is a hypothesis this run confirms or does not. No prediction is made of which side of 0.88 the bound falls: the shipped facility-clustered bound is 0.885.

## 9. Forbidden moves

1. Changing the rule in section 2, the thin-facility guard, the gamma grid, the seed or the level after any result is seen.
2. Dropping or adding a facility after the check.
3. Re-running the check with a different setting and reporting the better run.
4. Writing any output of the check into `05_results/`, or touching `birmingham_features_v2.parquet`.
5. Editing a manifest-listed or frozen file in place.
6. Any manuscript edit in revision 55 or 56.
7. Framing a missed prediction as anything other than a missed prediction (C20).

## 10. Addendum, written 2026-11-22 AFTER the decisive check and the independent review. Not part of the prespecified test

The check landed in Branch R (see `_applied-tracker-blocks/_pending_exp042.md`). Nothing above is altered. Two sensitivities and one fix are added for revision 56. They are labelled post hoc wherever they are reported, and neither replaces the main result.

- **S1, like-for-like rows.** The four primary methods at t+60 refitted on rows with all three targets observed, which is v2's row filter. Reported beside the main result. It answers whether the v2-to-v3 movement is the anchor rule or the 1,973 added rows.
- **S2, anchor age.** The Birmingham headline at each horizon split by `occ_carried`, from the main run's per-row coverage. No refit.
- **Fix, register item 2.7.** `select_gamma_on_calibration` leaves `horizon - 1` rows between its two halves. Applied before the full run, in both cities.

Forbidden move 3 still applies: S1 and S2 are reported whichever way they fall.

## 11. Addendum 2, written 2026-11-22 (revision 56), before any population-level S1 result. Not part of the prespecified test

- **S1 is redefined to match its stated purpose (D-038 item 2).** "Rows with all three targets observed" keeps 6,179 rows at t+60, and 27 of 28 facilities fall under the thin-facility guard. It is also not v2's filter, because v2's targets were present only because they were interpolated. S1 is the v3 rows whose (facility, timestamp) were usable at the same horizon in `birmingham_features_v2.parquet`: 12,797 rows at t+60 (7,196 / 3,015 / 2,586), all 28 facilities evaluable. Counted before running. Forbidden move 3 still applies.
- **The block bootstrap's common axis** (section 8) is the union of the 21 facilities' test timestamps, with the intersection count written beside it (D-038 item 6).
