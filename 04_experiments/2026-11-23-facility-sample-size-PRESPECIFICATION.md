# PRESPECIFICATION: EXP-044, facility sample-size guidance (D-041 addition A2)

**Written 2026-11-23, revision 57, BEFORE any number of this experiment was computed.** Seventeenth prespecification.
Authority: D-041 (A2, approved by the author 2026-11-23) and revision 57 step 0 of `00_admin/2026-11-22-audit-remediation-implementation-plan.md`.
No model is fitted. The only inputs are the existing per-facility v3 tables the paper's own inference reads.

## 1. Question

How many facilities does the paper's own two-level inference need before its tests can see the effects it reports? Concretely, at the facility counts the paper has (21 Belgrade, 28 Birmingham, after the low-information exclusion), and on a fixed grid of other counts:

- **E1, paired dispersion contrast.** The smallest mean paired reduction in absolute coverage gap, mean over facilities of |PICP_a - 0.90| - |PICP_b - 0.90|, that the Holm-adjusted Wilcoxon test detects with 80% power.
- **E2, population safety bound.** The smallest margin by which the true mean facility coverage must exceed 0.88 for the SAFE test (one-sided 95% facility-clustered t lower bound at or above 0.88) to pass with 80% power.
- **E3, population equivalence.** The power of the Holm-adjusted TOST equivalence test (margin 0.02 around 0.90) when the true mean facility coverage is exactly 0.90, and the smallest facility count giving 80%.

## 2. Inputs (fixed)

`05_results/tables/2026-11-22-core-{city}-v3-gcal-per-facility.csv`, filtered exactly as `03_code/src/conformal/2026-09-04-phase4-inference.py` filters it (`core_frame`: paper horizon, level 0.90, dynamic rows, its computed exclusion set, sorted by facility_id). The functions are imported from that file, not re-implemented (B9). Rows: Belgrade t+15, Birmingham t+60. Methods: the four primary methods. Contrasts: the four D-dispersion contrasts of the paper.

**Gate, run first.** On the observed vectors the script must reproduce, to 1e-9, `n_fac`, `mean_PICP` and `sd_PICP` of `2026-09-04-phase4-population.csv` and `mean_diff` and `wilcoxon_p_raw` of the D-dispersion rows of `2026-09-04-phase4-contrasts.csv`. If it does not, the script stops and writes nothing.

## 3. Method (fixed)

Resampling of the observed facility-level values (a location-shift bootstrap). Seed 20261123, B = 4,000 replicates per cell. Facility-count grid n = 10, 15, 21, 28, 40, 60, 80, 100, 150, 200.

- **E1.** Per contrast, centred residuals r_i = d_i - mean(d). For a candidate effect delta (grid 0.000 to 0.060 in steps of 0.0005), a replicate draws n residuals with replacement and subtracts delta. Detection = Wilcoxon signed-rank p below the threshold **and** the replicate mean negative (the adaptive method better). Because resamples contain ties, the Wilcoxon test uses its normal approximation with tie correction (`method="approx"`), a stated departure from the exact test the paper applies to untied data. **Primary threshold: 0.05 / 4 = 0.0125**, the first Holm step, at which a contrast is significant whatever the other three do. Secondary: 0.05 (the most favourable Holm case). Power at the observed effect is also reported, at every n.
- **E2.** Per method, centred values plus a candidate mean mu (grid 0.8800 to 0.9300 in steps of 0.0005), resampled at size n. Pass = one-sided 95% t lower bound at or above 0.88, the paper's SAFE rule.
- **E3.** Per method, centred values plus mu = 0.90, resampled at size n. Pass = TOST p (max of the two one-sided t p-values, margin 0.02) below **0.0125** (primary, first Holm step over four methods) or 0.05 (secondary).
- Minimum detectable effect (MDE) = the smallest grid value with power at least 0.80. If none, reported as "above grid". The smallest n giving 80% is read from the n grid, "above 200" if none.
- Summaries across the four methods or contrasts of a city: the median and the range.

## 4. Output

`04_experiments/2026-11-23-exp044/2026-11-23-exp044-facility-sample-size.csv`, long format: city, family (E1/E2/E3), item (method or contrast), threshold (primary/secondary), quantity (power_at_n, mde_at_paper_n, observed_effect, n_for_80), n, value. Promoted to `05_results/tables/` with the revision 57b reference refresh and manifest re-cut (staged now so that `verify.py` stays green). Script: `03_code/_staging/2026-11-23-exp044/src/conformal/2026-11-23-exp044-facility-sample-size.py`, mirroring its final path.

## 5. The sentence it feeds, written for both directions (ESM, with at most one clause in the main text)

- **If the observed Birmingham dispersion reductions are below the E1 primary MDE at 28 facilities:** "At 28 facilities the Holm-adjusted paired test detects a mean reduction in absolute coverage gap of {MDE} or more with 80% power. The observed Birmingham reductions ({lo} to {hi}) are smaller, so their non-significance reflects the facility count, and about {n80} facilities would be needed to detect them."
- **If they are at or above it:** "At 28 facilities the Holm-adjusted paired test detects a mean reduction of {MDE} or more with 80% power. The observed Birmingham reductions ({lo} to {hi}) are of that size, so their non-significance is not explained by the facility count alone."
- E2 and E3 give the practitioner guidance in either direction: "Passing the population safety bound with 80% power needs a true mean coverage about {E2} above the 0.88 margin at {n} facilities, and demonstrating equivalence to the 0.90 target needs about {n80} facilities." Reported whichever way the numbers fall, including if the paper's own Belgrade results turn out under-powered.

## 6. What this experiment may not do

It may not change any test of record, any verdict, the Birmingham rule or any existing table. It is descriptive guidance. Nothing in this file is changed after the script's output is read. A defect found after the run is fixed and rerun with the defect and the fix logged, never tuned to an outcome.
