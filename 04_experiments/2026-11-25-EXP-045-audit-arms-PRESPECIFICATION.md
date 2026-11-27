# PRESPECIFICATION: EXP-045, the external-audit arms (revision 59)

**Written 2026-11-25, revision 59, BEFORE any staged successor was written and before any EXP-045 run.** Nineteenth prespecification.
Authority: D-053 and section S59 of `00_admin/2026-11-25-external-audit-validation/2026-11-25-external-audit-fix-plan.md`.

**Disclosure on the predictions.** The predictions below are taken from the validation agents' scratch measurements (`verdicts/`, scripts in `2026-11-25-validation-scratch-scripts.tar.gz`). Those numbers were seen before this file was written. This experiment is therefore a **confirmation on the canonical code path**, not a blind test, and the record says so. What it fixes in advance is the code path, the inputs, the statistics, the stop rules and the sentence each outcome feeds, so that no choice is made after a result is read.

**Inputs for every arm.** The live project files, read from a byte copy in the cloud workspace (`_cleanroom/2026-11-25-s59-workcopy.tar.gz`, sha256 `873be827d47f605f`). Pinned stack: numpy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, scipy 1.15.3, pyarrow 25.0.1, holidays 0.103, matplotlib 3.10.9, ngboost 0.5.11, mapie 1.5.0 (Python 3.12). Every run records the sha256 of each input it reads and the package versions.

**Code rule (D-037, D-039).** Every changed script is a staged successor in `03_code/_staging/2026-11-25-exp045/`, mirroring its final path. `core.py` is not edited except as stated for T030. Each successor has a test or a positive control, listed per arm. Existing result tables are never overwritten: every new output carries a 2026-11-25 name.

**Paper base.** Wherever an arm uses "the paper base" it means the rows `2026-09-04-phase4-inference.py` selects with `core_frame` (paper horizon, level 0.90, dynamic rows, its computed exclusion set): Belgrade t+15, 21 facilities; Birmingham t+60, 28 facilities. Those functions are imported, not re-implemented (B9).

## 1. Arms

### A1. T005, the rolling-pool fixed-alpha arm (the decisive arm)

- **What.** `adaptive_conformal_stream(..., gamma=0.0)` on the same delayed stream, window, clip and scores as ACI and ACQR. Method labels **RS-CP** (centres = the RF point forecast, scores |y - yhat|, levels 0.80, 0.85, 0.90, 0.95) and **RS-CQR** (centres = the repaired CQR band, CQR scores, levels 0.90 and 0.95). Every facility and every horizon of both cities. gamma = 0 makes the gamma mode irrelevant, so there is one run per city.
- **Code.** Successor `03_code/src/conformal/2026-11-25-run-core-methods.py` with `--arm rolling0`. Everything else is the 2026-11-22 runner unchanged. Outputs `2026-11-25-core-{city}-v3-rolling0-per-facility.csv` and `...-rows-L90.csv` (Belgrade t+15 only, every Birmingham horizon, as the 2026-11-22 runner).
- **Reproduction gate (positive control), run inside the arm.** For every (facility, horizon), the run also recomputes split-CP, CQR, and ACI and ACQR at each row's shipped gamma, from the same fits, and compares PICP and Winkler with `2026-11-22-core-{city}-v3-gcal-per-facility.csv`: PICP exactly, Winkler to 1e-9 (A8). Any difference stops the arm.
- **Test.** `03_code/tests/2026-11-25-test-rolling-arm.py`: on synthetic data, gamma = 0 keeps the level fixed at alpha on every step; with a horizon longer than the stream (no release), RS-CP equals split-CP exactly; with releases, the pool is the last `window` scores. Control: gamma = 0.05 fails the first check.
- **Predicted counts.** Per-facility rows: Belgrade 24 x 3 x 6 = 432, Birmingham 28 x 3 x 6 = 504. Rows-L90: Belgrade 2 x 24,360 = 48,720; Birmingham 2 x 8,977 = 17,954.
- **Predicted values (paper base, level 0.90; g3 rerun.py).** Belgrade RS-CP mean 0.892, sd 0.016, worst 0.851, Winkler 23.87; RS-CQR 0.896, 0.015, 0.857, 19.61. Birmingham RS-CP 0.883, 0.032, 0.823, 220.2; RS-CQR 0.896, 0.034, 0.856, 220.6. Tolerance: 0.002 on means and sds, 0.005 on the worst facility, 0.5 on Winkler.
- **Inference.** Script `03_code/src/conformal/2026-11-25-exp045-rolling-inference.py`, output `2026-11-25-exp045-rolling-inference.csv`.
  - **Family R** (new, per city, two contrasts): ACI against RS-CP, ACQR against RS-CQR. Statistic: paired difference in |PICP - 0.90| per facility. Test: two-sided Wilcoxon signed-rank (exact when untied, as phase4 does), Holm over the two contrasts within a city.
  - Also reported, unadjusted and descriptive: RS-CP against split-CP, RS-CQR against CQR (the refresh share), Winkler differences for both family-R contrasts, and the share of the split-to-adaptive sd reduction that RS gives.
  - Population rules for RS-CP and RS-CQR exactly as phase4 applies them to the four methods: pointwise safety (one-sided 95% t lower bound at or above 0.88), exact (TOST, margin 0.02), and the Holm outcome beside it (T003).
  - Predictions. Belgrade: ACI against RS-CP mean -0.0049, raw p 0.020; ACQR against RS-CQR -0.0060, raw p 0.013; Holm p about 0.026 for both. Birmingham: -0.0041, p 0.29; -0.0057, p 0.064; ACQR Winkler +6.5 against RS-CQR.

### A2. T009, T010, T011, T053, the allocation ladder

- **What.** On the identical fitted panel and request seeds as `2026-09-05-relative-threshold-allocation.py`, three added policies: **CQR-RAW** (the HGB 95% upper quantile before conformalization), **SPLIT-CQR** (that bound plus the split calibration quantile of E_cal, no adaptation) and **RF-SPLITCP** (RF point forecast plus the split-CP upper quantile). Weekend and weekday windows, theta in {0.85, 0.90, 0.925, 0.95}, 20 seeds.
- **Also from the same panel:** T053 paired seed uncertainty (mean, sd and SE of POINT minus INTERVAL per cell) and the two weekend days separately; T011 the upper-tail miss rate P(Y > U) on all slots, offered slots and INTERVAL-assigned requests, per cell; T010 per-facility capacity perturbation, factor U(1 - s, 1 + s) per facility for s in {0.05, 0.10}, 40 draws, seed 20261125, the same capacity used for offering and outcome, weekend theta 0.90.
- **Code.** Successors of `2026-09-04-allocation-vignette.py` (caches the raw and split-CQR upper bounds and the RF split-CP bound) and `2026-09-05-relative-threshold-allocation.py` / `2026-09-05-rel-alloc-summary.py` (the three policies and the diagnostics). Outputs `2026-11-25-exp045-allocation-ladder.csv` and `2026-11-25-exp045-allocation-capacity.csv`.
- **Reproduction gate.** POINT, INTERVAL and MARGIN reproduce every cell of `2026-09-05-rel-alloc-summary.csv` and every row of `2026-09-05-rel-alloc-seeds.csv` exactly. Any difference stops the arm.
- **Predictions (weekend, bad assignments per 600 requests, g4 extra.py).** theta 0.90: POINT 27.30, CQR-RAW 7.35, SPLIT-CQR 4.70, ACQR 1.05, RF-SPLITCP 4.25, MARGIN 3.90. Share of the POINT-to-INTERVAL reduction given by CQR-RAW: 76%. SPLIT-CQR below ACQR at theta 0.925 and 0.95. T053: SE of POINT minus INTERVAL about 1.13. T011: INTERVAL-assigned miss rate about 5.6% at the primary cell, 3.8% to 5.9% across cells. T010: s = 0.05 reduction 75% to 100%; s = 0.10 reduction 55% to 100%, POINT above INTERVAL in at least 18 of 20 seeds in every draw. Tolerance: 0.1 on cells reproduced from the agents' code; directions exactly.

### A3. T006, the spatial refit on the canonical pipeline

- **What.** The spatial residual-correlation, Mantel and Moran analyses re-run on `belgrade_features_v2.parquet` with the `use_15` mask, the 2026-11-22 RF fit and the canonical delayed ACI at each facility's shipped calibrated gamma (read from the gcal per-facility table, not re-selected).
- **Code.** Successors of `03_code/src/spatial/2026-09-05-spatial-analysis.py` and `2026-09-05-spatial-mantel.py`; `2026-09-07-spatial-exclusion-base.py` re-subsets the new outputs. Outputs dated 2026-11-25, same columns as `2026-09-06-spatial-statistics.csv` and `2026-09-07-spatial-statistics-exclusion-base.csv`.
- **Control.** The refit's ACI PICP per facility equals the gcal table's ACI PICP at t+15, level 0.90, exactly.
- **Predictions.** 1,015 common timestamps; mean residual correlation 0.012; Mantel r -0.13 (p about 0.14); Moran I between 0.005 and 0.015 with p above 0.5. Verdict unchanged: no spatial dependence detected.

### A4. T024, the trust-abstain boundary rule

- **What.** The calibration replay seeds the score pool with `E_cal[:cut - gap]`, gap = h - 1, and uses `clip_low=None`, exactly as `core.select_gamma_on_calibration` does.
- **Code.** Successor of `2026-09-03-trust-abstain.py`; outputs dated 2026-11-25 beside the 2026-09-03 tables.
- **Control.** The replay, run with the selector's inputs, reproduces `gamma_calB_picp` of the gcal per-facility table for every ACQR row it uses.
- **Prediction.** No printed ESM S6 number moves at the printed precision (2 of about 383 seed scores change).

### A5. T039, 200 balanced random partitions

- **What.** The orthogonal partition check with 200 random partitions instead of one draw. "Balanced" means each draw permutes the facility's ToD bucket labels, so bucket sizes match the ToD partition exactly. Seed 20261125.
- **Code.** Successor of `2026-09-03-orthogonal-partition-check.py`. Output `2026-11-25-exp045-partition-random200.csv` (per draw, per method) and a summary row per method: the observed single draw, the ToD value, the median and 5th to 95th percentiles of the 200 draws, and the ToD value's percentile.
- **Control.** Draw index 0 with the old generator call reproduces the shipped single-draw value exactly.
- **Prediction.** The shipped single draw lies inside the 5th to 95th percentile band. The ToD-over-random ratios (2.04, 2.05 from one draw) become a band. The direction (ToD partition concentrates more miscoverage than a random partition of equal sizes) is predicted to hold at the median.

### A6. T069, CQR and ACQR cell diagnostics

- **What.** Facility-by-ToD cell coverage for CQR and ACQR from the shipped `2026-11-22-core-belgrade-v3-gcal-rows-L90.csv`, with the ToD buckets of `2026-09-03-tod-conditional.py`. Birmingham: the cell count per bucket, to document that every t+60 target falls in one bucket.
- **Code.** New script `03_code/src/conformal/2026-11-25-exp045-tod-cells.py`. Output `2026-11-25-exp045-tod-cells.csv`.
- **Control.** The same script reproduces the shipped split-CP and ACI cell figures (worst 0.516 and 0.672, 12 cells below 0.80 for each) exactly.
- **Prediction.** Belgrade CQR worst cell 0.636, 7 of 105 below 0.80; ACQR worst 0.755, 4 of 105.

### A7. T002, block bootstrap for both cities with the Exact column

- **What.** The synchronous 3 h time-block bootstrap of `2026-11-22-block-bootstrap-belgrade.py` (B 10,000, seed 42), parametrised by city, with the exact (TOST-style interval within [0.88, 0.92]) verdict beside the safety verdict. Birmingham: block 6 rows.
- **Code.** Successor `03_code/src/conformal/2026-11-25-block-bootstrap.py --city`. Output `2026-11-25-block-bootstrap-both-cities.csv`.
- **Control.** The Belgrade rows reproduce `2026-11-22-block-bootstrap-belgrade.csv` exactly.
- **Prediction.** Belgrade lower bounds 0.8785, 0.8798, 0.8665, 0.8769 (split-CP, CQR, ACI, ACQR), all below 0.88, and the exact verdict fails for all four. Birmingham: split-CP [0.8674, 0.9202], CQR [0.8743, 0.9198], ACI [0.8546, 0.9030], ACQR [0.8658, 0.9140], all four not safe.

### A8. T086, normalised Winkler

- **What.** Winkler divided by each facility's training-window maximum occupancy, paper base, the four methods and the two RS arms.
- **Code.** New script `03_code/src/conformal/2026-11-25-exp045-normalised-winkler.py`. Output `2026-11-25-exp045-normalised-winkler.csv`.
- **Prediction.** Belgrade order ACQR 0.1055, CQR 0.1058, ACI 0.1241, split-CP 0.1290; Birmingham CQR 0.2128 and split-CP 0.2168 swap places relative to raw Winkler.

### A9. T044, T090, T028, representativeness

- **What.** One script, three tables. T044: retained against excluded Birmingham rows (feature-complete rows whose target is unobserved), per horizon, with the carried-anchor share and pre-issue covariates. T090: Birmingham usable test rows by hour of issue and horizon. T028: the release lag of the delayed stream in clock time, per city and horizon (share equal to h, above h, above 12 h).
- **Code.** New script `03_code/src/conformal/2026-11-25-exp045-representativeness.py`. Outputs `2026-11-25-exp045-retained-excluded.csv`, `2026-11-25-exp045-rows-by-hour.csv`, `2026-11-25-exp045-release-lag.csv`.
- **Predictions.** T044: excluded share 25.5%, 31.1%, 39.0% (t+30, t+60, t+90); at t+60 test, carried anchor 49.1% of excluded against 16.1% of retained. T090: no usable test row before 10:00 at any horizon, none at 16:00 for t+60. T028: Birmingham release lag above h at 41.6%, 63.1%, 79.7% and above 12 h at 11.3%, 25.3%, 43.1%; Belgrade exactly h at 98.8% to 99.8%, never below h.

### A10. T030, the grouped fallback without double counting

- **What.** In `core.grouped_adaptive_conformal_stream`, the fallback pool is the facility's own scores plus the pooled scores of the OTHER facilities only (it now contains the own scores twice). The same fix in the Mondrian split-CP of `2026-09-03-tod-conditional.py`.
- **Code.** Successor of `core.py` (this function only) and of `tod-conditional.py`.
- **Proof that outputs are unchanged.** (i) The fallback branch is instrumented and its firing count on the shipped ToD inputs is 0 (minimum own count 96 against the threshold). (ii) `tod-conditional.py` old and new produce byte-identical outputs on the paper base. (iii) `test-conformal-core` and core v3 still pass. (iv) A unit test where the fallback fires shows that the own scores now enter once. Control: the old function fails (iv).
- **Prediction.** Firing count 0, outputs byte-identical.

### A11. T001, the Belgrade builder guard and causality test

- **What.** `2026-09-02-build_features_v2.py` gains an assertion that no retained row carries an interpolated value in any input column (anchor, lag, rolling). A Belgrade case joins the causality test: perturb or delete every reading after a cut time and require that no input of a retained row at or before the cut changes.
- **Code.** Successors of the builder and of `03_code/tests/2026-09-03-test-feature-causality.py` (or a new Belgrade test file, whichever keeps the Birmingham gate untouched).
- **Proof.** The successor builder writes `belgrade_features_v2.parquet` and its report byte-identical to the shipped files. The Belgrade causality test reports 0 violations at the 17 cut times of g1 m3.py, and its positive control (a builder that interpolates inputs two-sided) is detected.
- **Prediction.** 0 of 92,544 retained rows interpolated in any input; 336 interpolated t+30 targets (96 in test); perturbation test 0 violations; control detected.

### A12. T016, `run_all.sh --city birmingham` and the VS_ROOT fix

- **What.** `run_all.sh` gains `--city belgrade|birmingham|both` (default both). With birmingham, every Belgrade step is skipped and each step that loops over cities runs Birmingham only. `verify-state.sh` takes its root from `VS_ROOT`, set by `run_all.sh` to the repository it runs in, instead of the author's local path.
- **Test.** On a fresh clone of the public repository (`main` at 36edc4b) in the cloud workspace, with the two successors copied in and a fresh venv from the lock: `bash run_all.sh --city birmingham` runs to exit 0, every in-run gate green. `--smoke` is either wired to bound the runtime or removed from the README (decided by what the code supports; recorded).
- **Prediction.** Exit 0. Every Birmingham table regenerates; `verify.py` in that tree passes on the Birmingham entries (Belgrade entries are absent from the public tree by licence and are skipped).

### A13. T021, T022, the power script with simulated Holm

- **What.** Successor of `2026-11-23-exp044-facility-sample-size.py`: E1 detection uses the Holm procedure applied jointly to the four D-dispersion contrasts of a city in each replicate (facilities resampled jointly, so the contrasts keep their correlation), not the first Holm step alone. The ESM-ready settings line (B, seed, grids, test method) is written into the output.
- **Control.** With Holm replaced by the first step, the successor reproduces `2026-11-23-exp044-facility-sample-size.csv` exactly.
- **Prediction.** MDE at the paper's facility counts at or slightly below the first-step values; n for 80% power unchanged or lower by one grid step.

## 2. Stop rules and branches

1. **T005 (the author's rule).** On Belgrade t+15, level 0.90, if either family-R contrast (ACI against RS-CP, ACQR against RS-CQR) has Holm-adjusted p at or above 0.05, or a mean difference at or above 0, **stop and report to the author before any text work.** The headline sentence would change beyond D-053 item 2.
2. **Any reproduction gate or control fails** (A1 to A7, A10, A11, A13): that arm stops. It is diagnosed by reproduction (protocol item 4). If the cause is not found, stop and report.
3. **The Belgrade feature table is not byte-identical** after the guard (A11): the builder successor is not promoted; stop and report.
4. **T030 outputs differ** (A10): the `core.py` successor is not promoted; stop and report.
5. **`run_all.sh --city birmingham` fails on the fresh clone** (A12): fixed in code within this session if the cause is in the runner; otherwise report.

**Branches that do not stop the session** (each outcome feeds S60 text, written both ways here):
- **A1 Birmingham.** If a family-R contrast is significant on Birmingham, the S60 text reports a gain from the adaptive level in both cities. If not (predicted), it says no gain beyond recalibration is detectable on Birmingham, and the rolling arms are compared on Winkler and the worst facility.
- **A2.** If CQR-RAW gives at least half of the POINT-to-INTERVAL reduction (predicted 76%), the 96% is credited to committing on an upper bound, with calibration credited only the step from CQR-RAW to SPLIT-CQR and ACQR on the same predictor. If less than half, calibration is credited the larger share as measured.
- **A3.** If Moran I has p below 0.05 or the Mantel test does, the "no spatial dependence detected" sentence is withdrawn and the result reported as measured.
- **A5.** If the ToD value lies inside the random-partition 5th to 95th band, the section V-F claim that the ToD partition is special is withdrawn. If above (predicted), the claim is kept with the percentile.
- **A7.** Whatever the bounds, both cities' safety and exact verdicts under the time-block bootstrap are printed beside the facility-clustered ones.

## 3. Not run, and why (D-053 items 3 and 4)

SPCI and a faithful AgACI (T015), matched-frequency EnbPI (T032), the per-bucket rolling pool (T040), anchor age as a feature (T088): scoped wording in S60. The ToD part of T005 (bucket pools against bucket alpha states) is also scoped as text, as the cross-check rated it (g8 T005); A1 covers the global methods the headline rests on.

## 4. Promotion and counts

Promotion by a register script `03_code/2026-11-25-revision59-promote-exp045.py`: moves into place, no overwrite without the author's approval, sha256 on both sides of every move. Then the EXPERIMENTS_LOG entry (appended only in the step that re-cuts the manifest, C52), manifest re-cut, `verify.py` PASS, and the C16 fresh-unzip pass. The predicted manifest count is written as an addendum to this file, in the C47 form (`layout: baseline in that layout + delta`), once the staged file list is final and before promotion.

## 5. Gates at the end

All STEP 1 gates of the session brief, with the expected numbers changed only where an addendum here says so, plus: the new rolling-arm test, the Belgrade causality test (0 violations, control detected), byte-identity of the Belgrade feature table and report, and the T030 byte-identity proof.
