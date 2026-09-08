# PRESPECIFICATION — the X08 batch rerun (EXP-027)

**Written 2026-09-04, revision 39, BEFORE any number in the batch was regenerated.**
Second prespecification in this project, on the revision-38 model
(`2026-09-03-rolling-origin-PRESPECIFICATION.md`). Its purpose is the same: fix the population, the
method and the decision rules in advance, so that the forbidden repairs are unavailable to this session
even in principle.

Authority: **D-018 decision 1** (adopt the exclusion, publish both arms). The decision is NOT reopened
here. What is specified here is only *how* it is applied and *what counts as a surprise*.

---

## 1. The rule, and the one definition of it

`core.low_information_facilities(df)` / `core.is_low_information(occ)` /
`core.MIN_DISTINCT_READINGS = 10`, gated by property checks **P22-P24**. **No second definition is
written anywhere in this batch** (B9, and the `matured_release_end` precedent).

Applied to **the window being SCORED**, never to the whole frame. Facility 8's training window is healthy
(std 18.1); it is the *test* window that carries two distinct values. On the Belgrade main test split the
rule selects facilities **1 and 8**.

## 2. THE EVALUATION BASE — the thing revision 38 got wrong

**Every number in this batch is computed on the base the corresponding published number uses**, namely
`dynamic == True & degenerate != True`, which on Belgrade is **22 facilities** and excludes the degenerate
facility 1 and the non-dynamic facility 10. Applying the exclusion takes that base **22 -> 21**.

**This is recorded here because the revision-38 impact table does not do it.**
`05_results/tables/2026-09-03-stuck-sensor-impact.csv` computes its EXP-025 rows on the **all-24** base,
whose "after" column silently also drops degenerate facility 1 — a facility that appears in no published
number. Its `n_all=24 -> n_excl=22` is therefore "minus facilities 1 and 8", not "minus facility 8".
Consequences, measured before this batch began (read-only, from the logged per-facility CSVs):

| quantity | impact-table base (24 -> 22) | **published base (22 -> 21)** |
|---|---|---|
| ACI-crosscheck across-facility sd | 0.0239 -> 0.0076 (-68%) | **0.0109 -> 0.0077 (-29%)** |
| EnbPI across-facility sd | 0.0609 -> 0.0326 (-46%) | **0.0607 -> 0.0340 (-44%)** |
| **EnbPI / ACI dispersion ratio** | 2.55x -> 4.29x (*stronger*) | **5.58x -> 4.40x (WEAKER)** |

The -68% collapse in ACI's dispersion is mostly the removal of facility 1, whose PICP is *vacuously* 1.0
(B5), not the removal of facility 8. That is what manufactured the apparent strengthening. **The
published-base direction is the opposite one, and it is the one this batch reports.**

## 3. Method — re-aggregation, and why it is exact rather than a shortcut

Every script in scope fits **each facility independently**: its own model, its own calibration split, its
own gamma. No statistic in any of the seven pools rows across facilities. This was verified by reading
each script's own summary writer before this document was finalised:

| experiment | summary writer | aggregation | pooled across facilities? |
|---|---|---|---|
| EXP-017 / 019 core | *(ad hoc, no script in tree)* | mean / std(ddof=1) over facilities | no |
| EXP-020 base learners | `write_summary(per)` | mean over facilities | no |
| EXP-021 ToD | `write_summary(fb, min_cell)` | over facility x bucket cells | no |
| EXP-022 orthogonal | `write_summary(cells)` | over cells; **Cramer's V computed PER FACILITY** then averaged | no |
| EXP-024 trust/abstain | `write_summary(per)` | unweighted mean over facilities | no |
| EXP-025 E3 | *(ad hoc, no script in tree)* | mean / std(ddof=1) over facilities | no |

Therefore **re-aggregating the existing per-facility CSVs under the exclusion is exactly equivalent to
refitting with the exclusion applied**, and is strictly better than refitting, because it carries **zero**
refit noise: no RF thread-reduction drift (A8) and no MAPIE between-fit variation (A13). The delta is
attributable to the exclusion and to nothing else. This is the D-017 pairing principle applied to a
population filter instead of a protocol change.

**Where the batch must NOT re-implement an aggregation**, it reuses the script's own `write_summary` by
importing the module and redirecting its output constant. Two summaries (core headline, E3) have **no
writer in the tree** — they were produced ad hoc in an earlier stage, which is itself a provenance
finding to record — so for those two the aggregation is written here and validated **only** by the
negative control below.

## 4. NEGATIVE CONTROL — the gate on the whole batch (B11)

**Run the aggregator with the filter OFF first.** It must reproduce **every** logged summary number to
4 decimal places. Any discrepancy means the aggregator does not match the original aggregation, and the
filtered output from it is worthless.

- If the control passes: the filtered output is trusted, and the only difference between the two runs is
  the exclusion.
- If the control fails for an experiment: that experiment falls back to a **genuine rerun** of its script
  with the exclusion applied. It does not get patched into agreement.

No filtered number is written to any tracker before this control has passed for its experiment.

## 5. Prespecified expected directions

Stated now so a surprise is recognisable as a surprise rather than narrated afterwards (C4).

**Expected to CONFIRM (from the impact table, base-independent because facility 8 is the minimum):**
- EXP-025 EnbPI worst facility **0.6640 -> 0.8010**
- EXP-025 NGBoost worst facility **0.4867 -> 0.6621**
- Core methods barely move: Belgrade t+15 means shift by <= 0.002 in absolute value.

**Expected on the published base, CORRECTED from the record (section 2):**
- EXP-025 EnbPI / ACI dispersion ratio **5.58x -> ~4.40x (WEAKER, not stronger)**.
- EXP-019 split-CP / ACQR dispersion ratio — the paper's actual spine — **6.20x -> ~7.76x (STRONGER)**.

*(Post-run note, 2026-09-04: the two ratios above were computed here from unrounded per-facility sds with ddof=0. The measured batch values, computed from the summary tables' own 4-dp sds exactly as the published figures are, are **5.57x -> 4.42x** and **6.20x -> 7.76x**. The difference is rounding in the third significant figure and changes no direction or conclusion; recorded so the prespecified and measured values can be reconciled line by line.)*

**Explicitly NOT predicted** (no expectation is recorded, so none can be quietly met): EXP-020, EXP-021,
EXP-022 and EXP-024. Facility 8 is not the worst cell in EXP-021 (that is facility 9, on a healthy
series), so Table 4's headline is expected to be essentially untouched, but no figure is committed to.

## 6. What counts as which outcome — decided before seeing the data

- **Confirms:** directions as in section 5; the qualitative claims survive; the manuscript sentences need
  restatement of magnitude only.
- **Weakens but survives:** a ratio falls further than expected while remaining large, or a worst-facility
  figure moves more than predicted. Report the measured value; narrow the sentence to what the data
  supports; do not switch base, population or criterion to recover the old number.
- **Contradicts:** a core-method dispersion advantage disappears, or the split-CP / ACQR spine ratio
  falls. Then the thesis-threat protocol applies — write up, lay out options, STOP.

**Forbidden in this batch, restated:** changing the base after seeing a result; applying the exclusion to
some experiments and not others; reporting the all-24 figure because it is more flattering; relaxing
P22-P24; or regenerating a logged number without recording that it changed and why.

## 7. Atomicity

One batch, one re-freeze of the manifest at the end, one before/after table covering every changed
number. A half-applied exclusion — some numbers with facility 8, some without — is the one genuinely
dangerous state, and is the reason revision 38 stopped at the gate rather than starting a batch it could
not finish in one sitting. Re-aggregation is what makes finishing in one sitting possible.
