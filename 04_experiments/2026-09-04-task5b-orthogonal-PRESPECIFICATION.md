# PRESPECIFICATION — R-Phase 3b task 5b, the deferred EXP-022 orthogonal re-run (EXP-028)

**Written 2026-09-04, revision 39, BEFORE the run.** Third prespecification in this project. Closes
**D-016 #5**, deferred from revision 38 because its Belgrade arm included facility 8 and the X08 decision
had not been taken. That decision is now taken (D-018) and applied (EXP-027), so the check is unblocked.

---

## 0. TWO FACTS MEASURED FIRST, BOTH OF WHICH CHANGE THE DESIGN

These were measured on the inputs before anything was run, and they are recorded here because the plan
in D-016 #5 assumes otherwise. Neither is a result; both are properties of the data.

**(a) Birmingham lies entirely inside ONE time-of-day bucket.** Its usable rows span hours **10-15 in
every split** (train, calibration and test alike), so under EXP-021's bucket definition every Birmingham
row is `midday`. ToD conditioning there is therefore **vacuous, not merely sparse**: with one group,
`core.grouped_adaptive_conformal_stream` is bit-identical to the ungrouped stream — that is property
**P14**, the reduction test, so ToD-ACI **provably equals global ACI on Birmingham**. EXP-021 anticipated
"the night bucket will be empty on Birmingham"; the truth is that **four of the five buckets are empty**.
Consequence: the Birmingham arm cannot test off-axis transfer of a ToD-conditional method using the
coarse buckets, because on that city there is no conditioning to transfer.

**(b) The Belgrade fold arm does NOT give day-of-week a properly replicated test, contrary to
D-016 #5.** Each fold's test window is three consecutive days, so weekday and date remain in exact
one-to-one correspondence *within a fold* — the identical confound to the main split, only smaller:
F1 = Mon/Tue/Wed, F2 = Thu/Fri/Sat, F3 = Sun/Mon/Tue. Pooled across folds the nine dates do cover all
seven weekdays, but only at 1-2 replicates and across three different model fits.
**Birmingham remains the only properly replicated day-of-week test** — 15 dates, all 7 weekdays at 2-3
replicates each, inside a single fit — and that is what the D-016 #5 deliverable rests on.

**(c) The X08 exclusion is fold-dependent, and this arm demonstrates it.** Applied to each fold's own
scored window: **F1 excludes only facility 1; F2 and F3 exclude {1, 8}.** Facility 8 is still healthy
through 14 March and dies inside F2's window. This is exactly why D-018 requires the rule to be applied
to the window being scored rather than the whole frame, and it is measured here rather than asserted.

## 1. Arms — fixed in advance

| arm | city | conditioning axis | scored partitions | purpose |
|---|---|---|---|---|
| **A. folds** | Belgrade, 3 EXP-013 folds | 5 ToD buckets (unchanged) | time_of_day, day_of_week, occupancy_tercile, random_5 | three independent replications of the EXP-022 transfer rule on different train/test windows |
| **B. bham-coarse** | Birmingham t+60 | 5 ToD buckets (unchanged) | day_of_week, occupancy_tercile, random_5 | the **primary D-016 #5 deliverable**: a properly replicated day-of-week test. time_of_day is recorded as DEGENERATE (1 cell) and ToD-ACI is expected to equal ACI exactly, which is a **positive control on P14** |
| **C. bham-hour** | Birmingham t+60 | **hour-of-day, 6 levels (10-15)** | day_of_week, occupancy_tercile, hour_of_day, random_6 | SECONDARY and labelled as such: the only way this city admits a genuine conditional method at all |

**Arm C's axis is prespecified here, with its reason, precisely so it cannot be chosen after seeing a
result.** The reason is (a): the coarse buckets have one level on this city, so a conditional method
requires a finer axis, and the hour within the operating window is the natural analogue of "time of day"
for a daytime-only city. Arm C is reported as secondary throughout; **if arms B and C disagree, arm B is
the one that stands**, because it is the unmodified design.

## 2. Design elements carried over from EXP-022, non-negotiable

- **Matched random-label noise floor (B1).** Every arm carries a `random_k` partition with seeded labels
  and the SAME cell count as that arm's conditioning axis (5 for A and B, 6 for C), so cell sizes match.
  A dispersion comparison without it is not interpretable, and the floor is computed **per method**.
- **Cramer's V measured, not assumed (B2).** Reported per facility against that arm's conditioning axis,
  then averaged, exactly as EXP-022 does.
- **Excess dispersion** `sqrt(max(sd_partition^2 - sd_random^2, 0))`, and structure removed on the
  **variance** basis `1 - excess_m^2 / excess_splitCP^2` — the definitions reconciled against EXP-022's
  logged figures in EXP-027.
- **Occupancy terciles cut on TRAINING-window percentiles only**, never test data.
- **Identical intervals** across partitions within an arm: one fit per unit, all four methods scored on
  the same rows. Seed 42; learner hyperparameters at ARCHIVED values (B6).
- **Report a clipped excess of exactly 0.0 as "at or below the matched noise floor", never as "100% of
  structure removed"** — that is a statement about resolution, and EXP-027 already hit this case.

## 3. Population and exclusions

- `core.low_information_facilities` applied to **each arm's own scored window** (D-018; one definition,
  B9). Expected: F1 -> {1}, F2 -> {1, 8}, F3 -> {1, 8}, Birmingham -> {}.
- `dynamic` computed on **each unit's own training window** at std >= 5.0 — the I05 fix, consistent with
  EXP-026. Every facility is run regardless and tagged; the filter is applied at summary time (D05).
- Cells below `MIN_CELL = 30` observations are flagged and excluded from the summary, as in EXP-022.

## 4. What counts as which outcome — decided before seeing the data

- **Confirms:** the EXP-022 dose-response reproduces in direction on the folds (structure removed falls
  monotonically with Cramer's V), and on Birmingham the adaptive family shows lower day-of-week
  dispersion than split-CP net of the matched noise floor.
- **Weakens but survives:** the ordering holds in some folds and not others, or the Birmingham day-of-week
  margin is inside its noise floor. Then the transfer rule is reported as Belgrade-specific and the
  day-of-week leg is stated as untested rather than negative.
- **Contradicts:** the adaptive family shows *higher* conditional dispersion than split-CP net of noise on
  a properly replicated axis. That would attack EXP-021/EXP-022 directly — stop, write up, lay out
  options, do not re-cut the partitions.
- **Predicted in advance so the outcome is logged either way (C4):** arm B's ToD-ACI rows will be
  **bit-identical** to its ACI rows. If they are not, P14 is wrong or the runner is not using the shared
  core, and that is a code defect to fix before reading any other number in this experiment.

## 5. Forbidden

Re-cutting a partition after seeing its dispersion; dropping a fold, weekday or facility without a
prespecified rule stated on the inputs; quoting arm C where arm B answers the question; reporting a
clipped zero as a perfect result; or using the pooled-across-folds day-of-week cells as though they were
replicates within one fit.
