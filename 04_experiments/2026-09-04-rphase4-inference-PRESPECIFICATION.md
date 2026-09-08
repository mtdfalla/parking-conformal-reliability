# PRESPECIFICATION — R-Phase 4, the inference redesign (EXP-030)

**Written 2026-09-04, revision 41, BEFORE any R-Phase 4 number was computed.** Fifth prespecification in
this project. Closes audit issues **I01** (invalid "at target" criterion), **I02** (overstated universal
reliability), **I03** (pooled conditional analysis), **I04** (non-independent rolling-origin inference),
**I06** (multiplicity and block-bootstrap design) and **D04** (selective coverage), and produces display
item **T3'** under D-020. Authority for the estimand: **D-016 decision 3**, unchanged.

---

## 0. FACTS MEASURED ON THE INPUTS FIRST, BECAUSE THREE OF THEM CHANGE THE DESIGN

Measured before anything was computed. None is a result; all are properties of the data or of the
already-logged design (B19, B20).

**(a) I06's bootstrap leg is ALREADY CLOSED, and R-Phase 4 therefore needs no re-fit.** The audit found
`B = 500` with a fixed 20-row block in both cities — 100 minutes at Belgrade's 5-min cadence and 600 at
Birmingham's 30-min cadence, "two very different dependence assumptions wearing the same number". The
logged R-Phase 3 outputs do **not** use that design: `2026-09-02-run-core-methods.py` sets
`BOOT_B = 10_000` and derives the block from cadence via `core.block_length_for_cadence(cadence, 3.0)` —
**36 rows Belgrade, 6 rows Birmingham, 3 hours in both**. So every `picp_ci_lo/hi` in
`2026-09-02-core-{city}-gcal-per-facility.csv` is already on the corrected design. **What remains of I06
is (i) multiplicity — no Holm correction exists anywhere in this project's paired tests — and (ii) blocks
are cadence-aware but not day-aware**, so a 3-hour block can straddle a night gap in Birmingham's
daytime-only record. (i) is Stage 1; (ii) is Stage 2 and is a sensitivity check, not a headline.

**(b) The +/-0.02 band is unreachable at the facility level in BOTH cities. This is decided on the
inputs, not discovered in the output.** Per-facility 90% CI half-widths at the headline configuration:

| city | facilities (dynamic) | median n_test | CI half-width: median | min | max |
|---|---|---|---|---|---|
| Belgrade t+15 | 22 (**21** after D-018) | 1,015 | **0.0327** | 0.0164 | 0.0933 |
| Birmingham t+60 | 28 (exclusion empty) | **135** | **0.0568** | 0.0000 | 0.1026 |

A band of half-width 0.02 cannot contain an interval of half-width 0.033, still less 0.057. **Facility-level
EXACT is therefore not an outcome this design tests.** Reporting it as a failure of the methods would be
reporting a property of `n`, which is precisely the error EXP-017 made and EXP-023 diagnosed (B4). The
two-level estimand exists because of this row, and the prose must say so with these numbers.

**(c) SAFE alone rewards over-coverage, and two Birmingham facilities demonstrate it.** Facilities 20 and
22 reach split-CP PICP **exactly 1.000** at `n_test = 82`, with a degenerate bootstrap CI of **[1.000,
1.000]**. They pass any lower-bound criterion trivially. This is not a defect and they are not excluded —
their series are informative — but it fixes in advance that **SAFE is never reported without the
efficiency leg beside it**, and that "fraction of facilities SAFE" is not by itself a ranking.

**(d) The evaluated base, computed and never hardcoded.** `core.low_information_facilities` on the scored
window: Belgrade **{1, 8}** removed from the 22 dynamic facilities -> **n = 21**; Birmingham **{}** ->
**n = 28**. Per D-018, applied to the window being scored. Facility counts quoted anywhere in R-Phase 4
are 21 / 28.

**(e) What is already delivered and is NOT re-opened here.** I03 is closed by EXP-021 (facility x bucket,
worst cell 0.5160 vs ToD-ACI 0.8421, zero cells below 0.80); I04's fold-level analogue is closed by
EXP-026 (facility-clustered, Holm, B = 10,000, `dynamic_all_folds_x08excl` arm at n = 21); D04 is closed
by EXP-024 with its matched random control. R-Phase 4 consumes those results, computes the **main-split**
analogue that does not yet exist, and adds the multiplicity correction none of them carries.

---

## 1. THE ESTIMAND — two levels, fixed in advance (D-016 #3)

**Unit of analysis at both levels is the FACILITY.** The per-row and pooled-fold-facility units are
retired here and are not reported anywhere in R-Phase 4.

### 1.1 Population level — three legs, epsilon = 0.02 fixed in advance (D-014 #5)

Statistic: **mean PICP across facilities**, facility-clustered, per city and method.

| leg | definition | level |
|---|---|---|
| **SAFE** | one-sided lower confidence bound on mean PICP **>= 0.88** | 95% one-sided |
| **EXACT** | **TOST** equivalence inside [0.88, 0.92] — operationally, the **two-sided 90% CI lies wholly inside the band** (TOST at alpha = 0.05 is exactly this interval inclusion, and both forms are reported so no reader has to take the equivalence on trust) | alpha = 0.05 |
| **EFFICIENCY** | paired **Winkler**, facility-paired | alpha = 0.05 |

Two inference routes are computed for every leg and **both are reported**: a facility-clustered
**t-interval** (n = 21 / 28) and a **facility bootstrap, B = 10,000, seed 42**, resampling facilities with
replacement. **Prespecified tie-break: where they disagree, the bootstrap governs**, because the
t-interval assumes exchangeable, independent facilities and the bootstrap is the check EXP-023 asked for.
Disagreements are reported, never silently resolved.

### 1.2 Facility level — equivalence is NOT claimed, and the reason is stated

Reported, per city and method: across-facility **sd** of PICP (dispersion); the **worst facility**;
the **fraction of facilities whose one-sided lower bound falls below 0.88**; and, carried from EXP-021,
the **worst facility x bucket cell** and the **fraction of cells below 0.80**. No equivalence test is run
at this level and none is reported, with fact (b) given as the reason in the caption and the text.

### 1.3 Multiplicity — the families are fixed HERE and cannot be extended later (I06)

| family | members | correction |
|---|---|---|
| **P — primary** | 4 TOST tests, one per core method (split-CP, CQR, ACI, ACQR) | Holm within city |
| **E — efficiency** | 4 paired Winkler contrasts: ACI vs split-CP, ACI vs CQR, ACQR vs CQR, ACQR vs split-CP | Holm within city |
| **D — dispersion** | the same 4 contrasts on per-facility \|PICP - 0.90\|, the main-split analogue of EXP-026 | Holm within city |
| **exploratory** | EnbPI, AgACI-style, NGBoost, NGBoost-conformal; all horizons other than the headline; the 95% level | **none — labelled exploratory, in no family, and no p-value is quoted for them as evidence** |

Baselines are placed outside the families **now**, so that they cannot be moved inside later if their
p-values turn out to help. Every reported p-value states which family corrected it.

---

## 2. HELD FIXED, so that the delta is attributable (B6)

**No model is re-fitted in Stage 1.** Inputs are the logged per-facility CSVs
`2026-09-02-core-{belgrade,birmingham}-gcal-per-facility.csv` and `2026-09-03-e3-*-per-facility.csv`.
Headline configuration: **Belgrade `y_t+15min`, Birmingham `y_t+60min`, level 0.90**, dynamic facilities,
non-degenerate, minus `core.low_information_facilities`. epsilon = 0.02; alpha = 0.05; B = 10,000;
seed 42; base 21 / 28. The exclusion is applied through `core.py` and nowhere else — **no second
definition of "low information" is written** (B9).

## 3. WHAT CHANGES AGAINST THE ARCHIVED MANUSCRIPT, each with its issue

1. **I01.** "A facility is statistically at target when its bootstrap CI contains 0.90" is **retired**.
   Failing to reject equality is not evidence of equality, and a noisier facility passes more easily. It
   is replaced by the three-leg criterion in 1.1. The "100% of facilities at target" headline dies with it.
2. **I02.** "Universal reliability" is retired as a phrase and as a claim; the facility level is reported
   as a distribution with a worst case, never as a proportion passing a weak test.
3. **I03.** Pooled bucket coverage is replaced by facility x bucket (already built, EXP-021).
4. **I04.** The pooled 66-row Wilcoxon is retired; facility-clustered inference only, on the n = 21 arm.
5. **I06.** Holm correction added over the three fixed families; the bootstrap design is already correct
   (fact (a)); day-awareness is tested in Stage 2.
6. **D04.** Selective coverage reported with the matched random control and the limitation stated (EXP-024).

## 4. THE GATE, run before any new number is read (the EXP-027 pattern, B17)

**Stage 1 gate — a negative control on the whole re-aggregation.** With the exclusion filter **OFF**,
recompute every aggregate the new script produces directly from the logged per-facility CSVs and assert
it equals the corresponding **logged** summary to **4 dp** — sources: `2026-09-04-x08-core-headline-control.csv`,
`2026-09-02-corrected-headline-gcal.csv`, `2026-09-03-e3-summary.csv`. **Zero failures required before any
filtered number is read.** Any "before" value quoted anywhere is asserted equal to the logged number to
4 dp first (B17), and the base of every before/after pair is stated as 22 -> 21 or 28 -> 28.

**Stage 2 gate — separate, and Stage 1 does not depend on it.** Stage 2 re-fits the headline
configuration only (one horizon, one level, four methods, resumable, budget-limited) for the sole purpose
of persisting the **per-row coverage indicator series**, which no logged artifact contains. It must first
reproduce **the logged per-facility PICP to 4 dp** and **the logged `picp_ci_lo/hi` to 4 dp under the
logged bootstrap settings**. If either fails — the A13 hazard, an unpinned dependency having moved a
number, is live here because the core CSVs predate the EXP-025 lock — **Stage 2 is abandoned and reported
as not reproducible; Stage 1 stands unaffected.** Either outcome is logged.

Stage 2, if the gate passes, delivers exactly two things and no headline: (i) the **day-aware block
sensitivity** — CIs recomputed with blocks forbidden from crossing a calendar-day boundary, reported as a
max absolute change in bound across facilities; (ii) **I02's finite-window convergence curves** and
early-window transient coverage, for the ESM.

## 5. OUTCOMES — every branch decided before seeing any of them, including the degenerate one

The branch list is written out in full **because EXP-029's was not** (B20): its outcome set had no branch
for "the event occurs zero times in either arm", the demotion rule fired by arithmetic accident, and the
log had to record a branch that was retrofitted. That does not happen twice.

- **SUPPORTS the two-level argument (the paper's central claim).** At least one method passes population
  EXACT **and** SAFE while the facility level shows a worst cell below 0.80 or a non-zero unsafe fraction.
  Then the paper demonstrates with its own numbers that population equivalence testing conceals the
  failure it exists to expose. Main text, as T3'.
- **DISCRIMINATING at the population level.** Some methods pass EXACT and others do not. Then T3' is
  additionally a method ranking, and the concealment argument rests on whichever method passes population
  while failing facility level. Main text; the ranking is stated with its Holm-corrected p-values.
- **NON-DISCRIMINATING at the population level — and this is a RESULT, not a null.** All four methods pass
  EXACT and SAFE. EXP-023 makes this the most likely branch (7 of 8 configurations EXACT, 8 of 8 SAFE, on
  the pre-exclusion base). The finding is then stated directly: **the instrument the field uses cannot
  tell these four methods apart, while the facility level separates them by 38 coverage points**
  (split-CP worst cell 0.5160 against ToD-ACI 0.8421). This is the strongest form of the paper's argument
  and it is written that way, not apologised for.
- **CONTRADICTS — stop and write up.** The adaptive methods fail population SAFE while split-CP passes,
  or the dispersion contrasts reverse against EXP-026. Then the recommendation flips, work stops, the
  options are laid out, and the author decides (protocol step 8).

**Predictions recorded now so the outcome is logged either way (C4).** All four Belgrade methods pass
population EXACT and SAFE, giving the non-discriminating branch; ACI/ACQR sit at mean 0.8913 / 0.8940 with
facility-clustered SE small enough to fall inside the band; **at the facility level ACI's SAFE fraction is
0.000 post-exclusion** (EXP-027), so the two levels should disagree sharply and in the direction the paper
argues. **No prediction is recorded for Birmingham's TOST**, where the median CI half-width is 0.057 and
the facility-clustered SE is the only thing carrying it. No prediction is recorded for the efficiency
family: CQR keeps a Winkler edge in 5 of 6 archived rows and that must not be pre-judged.

## 6. FORBIDDEN

Changing epsilon, the families, the tie-break rule or the headline configuration after seeing any output;
moving a baseline into a Holm family; adding a fifth family; dropping a facility, horizon or city without
a rule stated on the inputs and shown insensitive to its threshold (B16); quoting a pre-exclusion "before"
value beside a post-exclusion one, or any before/after pair without naming its base (B17); reporting any
p-value without naming the family that corrected it; claiming equivalence at the facility level in any
form of words; using the pooled per-row or 66-row fold-facility test anywhere for any purpose; and
reporting Stage 2 as a headline result under any circumstances.

## 7. DELIVERABLES

`05_results/tables/2026-09-04-phase4-{gate,population,facility,contrasts}.csv`, the T3' display item built
from `-population` and `-facility`, and — only if the Stage 2 gate passes —
`2026-09-04-phase4-{dayblock-sensitivity,convergence}.csv` plus the ESM convergence figure. Scripts are
dated, resumable where they fit, and flush per unit. Nothing logged is overwritten. The full gate
(50 / 48 / 130) is re-verified after any change to `core.py` or the test suite, and the frozen manifest is
re-checked after every result-generating run.
