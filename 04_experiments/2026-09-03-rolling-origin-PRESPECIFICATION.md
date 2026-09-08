# PRESPECIFICATION — R-Phase 3b task 5, rolling-origin (I04, I05)

**Written 2026-09-03, revision 38, BEFORE any result of the corrected run was generated or inspected.**
Purpose: fix the estimand, the contrast family and the decision rules in advance, so that the
"forbidden repairs" (changing the evaluation criterion after seeing the result; dropping an inconvenient
facility, horizon or fold without a prespecified rule) are not available to this session even in principle.

The archived run being replaced is EXP-013 / `2026-08-04-rolling-origin.py`, which carries audit issues
**I04** (pooled Wilcoxon over 66 non-independent fold-facility rows) and **I05** (facility selection from
the main training window rather than per fold). It additionally runs on v1 features, on a private copy of
the ACI recursion carrying the C01 off-by-one, and at a fixed gamma = 0.05.

---

## 1. Design held FIXED from EXP-013 (deliberately not re-optimised)

Three expanding-window folds, boundaries unchanged, so the delta is attributable to the fixes and not to
a redesign:

| fold | train | calibration | test |
|---|---|---|---|
| F1 | Mar 4 – Mar 9  | Mar 10 – Mar 12 | Mar 13 – Mar 15 |
| F2 | Mar 4 – Mar 12 | Mar 13 – Mar 15 | Mar 16 – Mar 18 |
| F3 | Mar 4 – Mar 15 | Mar 16 – Mar 18 | Mar 19 – Mar 21 |

Setting: Belgrade, `y_t+15min`, h = 3 steps (5-min cadence), 90% target, seed 42.
Methods: split-CP, ACI, CQR, ACQR.
Base learners at ARCHIVED hyperparameters (B6): RF(n_estimators=100, min_samples_leaf=2),
HistGBR(loss="quantile", max_iter=100).

**Changed by mandate, not by choice:** v2 features with the `use_15` filter (R-Phase 1), and every
conformal primitive from `core.py` (R-Phase 2 — this is what removes C01/C02/C06).

## 2. Inclusion rules — fixed in advance

- A fold-facility is **evaluated** if `len(train) >= 500`, `len(cal) >= 200`, `len(test) >= 200`.
  Anything failing this is written as a `SKIPPED-thin` marker row (A2) and is excluded from every
  analysis. No facility is removed for any other reason, at any point.
- **`dynamic_fold`** (the I05 fix): `std(occupancy) >= 5.0` computed on **that fold's own training
  window**. This is the primary population.
- **`dynamic_archived`**: the same threshold on the main v2 train split (through Mar 13) — the archived
  rule, recorded per row purely so the I05 delta can be measured.
- **All facilities are run in every fold regardless.** The all-facility sensitivity arm required by I05
  is therefore the same run with the filter dropped, not a separate execution.

## 3. Gamma arms — paired inside one fit

Both arms share the SAME fitted RF and quantile models per fold-facility, so the difference between them
carries no fit-to-fit variation (the D-017 pairing principle).

- **`calibrated`** — PRIMARY. `core.select_gamma_on_calibration`, chosen per fold-facility-method on a
  nested cal-A/cal-B split. Never touches test data. Mandated by the R-Phase 3b definition of done.
- **`fixed05`** — CONTROL. gamma = 0.05, the archived value. Present only so the change from the archived
  numbers can be decomposed into "the fixes" versus "the gamma protocol".

split-CP and CQR do not depend on gamma and are recorded once, with `gamma_mode = "n/a"`.

## 4. Primary estimand and the contrast family (I04)

**Unit of analysis: the facility.** Fold-facility rows are NOT independent replicates — each facility
appears in three folds — which is exactly what makes the archived p < 1e-10 anti-conservative.

Per-facility statistic: `mean over folds of |PICP - 0.90|`, i.e. average within facility first, then test.

**Prespecified contrast family — these four, and no others are primary:**

1. ACI vs split-CP
2. ACI vs CQR
3. ACQR vs CQR
4. ACQR vs split-CP

Tested on the `calibrated` arm, `dynamic_fold` population.

- **Primary test:** two-sided Wilcoxon signed-rank on the per-facility differences, n = number of
  facilities dynamic in all three folds. **Holm-corrected across the four contrasts.**
- **Confirmatory:** facility-clustered bootstrap, B = 10,000, resampling FACILITIES with replacement
  (never fold-facility rows), reporting the 95% percentile CI of the mean difference and a two-sided
  bootstrap p. Seed 42.
- **Reported alongside for contrast, never as evidence:** the archived-style pooled n = 66 Wilcoxon, so
  the size of its anti-conservatism is quantified rather than asserted.

**Note recorded in advance:** at n = 22 the two-sided Wilcoxon signed-rank p cannot fall below
~4.8e-7 (2 / 2^22). A primary p at that floor means "as significant as this test can report", not
"stronger than the archived 1e-10". This is stated now so it is not mistaken later for a weakened result.

## 5. What counts as which outcome — decided before seeing the data

- **Confirms:** ACI/ACQR closer to target than split-CP/CQR on |gap|, surviving Holm at the facility
  level, with the bootstrap CI excluding zero. Expected per the audit; report the honest p.
- **Weakens but survives:** direction holds, some contrasts lose significance after Holm. Report exactly
  which, and narrow the manuscript sentence to the contrasts that survive.
- **Contradicts:** direction reverses, or the dispersion advantage disappears. Then the finding goes on
  the dead list with its evidence, and the thesis-threat protocol is followed — write up, lay out options,
  stop. Do NOT switch to a different criterion, population or fold set to recover it.

**The archived "split-CP collapses in fold F2" claim (std 0.161, Winkler 34.9) is treated as UNVERIFIED
and is expected NOT to reproduce**, since it was produced on v1 features by the C01-affected path. It is
recorded here as a prediction so that whichever way it lands, the outcome is logged rather than narrated
after the fact (C4: do not pre-write the interpretation — but do pre-write the expectation).

## 6. Orthogonal-partition re-run (D-016 #5)

Re-run the EXP-022 check on (a) the three fold test windows and (b) Birmingham. Non-negotiable design
elements carried over: the matched random-label noise floor with the same cell count as the conditioning
partition (B1 — a dispersion comparison without a noise floor is not interpretable), and Cramer's V
measured rather than assumed (B2). Occupancy terciles cut on TRAINING-window percentiles only.

Belgrade's own test split has 4 dates and 4 weekdays each occurring once, so its day-of-week leg is
confounded by construction; Birmingham's has 15 dates spanning all 7 weekdays at ~2.1 replicates each and
is the properly replicated test.
