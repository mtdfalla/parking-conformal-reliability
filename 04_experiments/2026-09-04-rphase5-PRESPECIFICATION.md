# PRESPECIFICATION — R-Phase 5, the secondary claims (EXP-031)

**Written 2026-09-04, revision 42, BEFORE any R-Phase 5 outcome was computed.** Sixth prespecification in
this project. Executes **D-019 (A) + (D')**, and closes **D05** and **M02**. Authority: D-019's resolution
block, D-020 (neither deliverable takes a main-text display item), and the record's section 6.

**What was deliberately NOT looked at before this document was written:** facility 8's conformal upper
bound `U`, the withdrawal step, and any POINT-vs-INTERVAL request count on the corrected pipeline. Those
are the OUTCOMES of (D'). Section 0 below contains only properties of the raw data and of already-logged
artifacts — the B19/B20 class of check — and every one of them is reproducible from the inputs alone.

---

## 0. FACTS MEASURED ON THE INPUTS FIRST, BECAUSE FOUR OF THEM CHANGE THE DESIGN

### (a) Facility 8's feed was ALREADY anomalous during CALIBRATION. The onset is not where the plan assumed.

Belgrade facility 8, `belgrade_features_v2.parquet`, `use_15`:

| split | n | distinct occupancy values | std | span |
|---|---|---|---|---|
| train | 2,069 | 215 | 17.74 | 2017-03-04 16:00 → 03-13 23:55 |
| calibration | 760 | 80 | 14.30 | 2017-03-14 00:00 → 03-17 23:55 |
| test | 1,015 | **2** | 54.22 | 2017-03-18 00:00 → 03-21 18:50 |

The two test values are **0.0 (455 rows)** and **109.0 (563 rows)**, and the run structure over the whole
record is:

| run | value | from | to | splits crossed |
|---|---|---|---|---|
| 921 rows | **0.0** | 2017-03-14 **23:00** | 2017-03-19 17:55 | calibration → test |
| 563 rows | **109.0** | 2017-03-19 **18:00** | 2017-03-21 16:50 | test → test |
| 24 rows | 0.0 | 2017-03-21 16:55 | 2017-03-21 18:50 | test |

**Consequences that the claim wording must respect:**

1. **The feed did not "become anomalous" inside the test window — it changed ANOMALY MODE.** It goes flat
   at 0 on **14 March 23:00**, which is inside the calibration split, and the observable event inside the
   test window is a **regime change 0 → 109 at 2017-03-19 18:00**. "A facility whose feed has become
   anomalous" is therefore not a description this record supports; "a facility whose anomalous feed
   changes level" is.
2. **64.1% of facility 8's calibration rows (487 of 760) lie inside the constant-0 run.** Its conformal
   score pool, and the gamma selected on it, were calibrated largely ON the anomaly. Whatever leg 1
   measures, it is not the response of a cleanly calibrated interval to a first anomaly.
3. **The archived weekday window contains no transition at all.** Of facility 8's 167 weekday-window
   slots (Mar 20–21, 12:00–19:00), **167 are post-onset** — the window opens ~42 h after the regime
   change. The archived "POINT sent 105, INTERVAL sent 14" is therefore a **steady-state** contrast, not
   a demonstration that anything was withdrawn *within a few steps*. The published sentence could never
   have shown what D-019 (D) claimed it showed, independently of B21's configuration objection.
4. **The weekend window straddles the transition**: 135 of its 147 facility-8 slots are pre-onset and
   **only 12** are post-onset. A withdrawal taking more than 12 steps is not observable inside that
   window. It IS observable on the continuous test stream, which is where leg 1 measures it.

### (b) The (A) capability numbers reproduce exactly, and the gap is provenance, not correctness.

Recomputed from the inputs on the same base (20 healthy facilities; 3,340 weekday and 2,940 weekend
facility-slots), scoring the same quantity the vignette scores (`y_t+15min`, the realised target, not the
contemporaneous reading):

| window | population | slots | peak % of `cap_train` | at `ratio >= 1.0` | at the design's own event, `cap - y < 1` |
|---|---|---|---|---|---|
| weekday | healthy base | 3,340 | **98.74%** (facility 9) | 0 | **0** |
| weekend | healthy base | 2,940 | **99.83%** (facility 9) | 0 | **0** |
| weekday | facility 8 only | 167 | 167.69% | 140 | 140 |
| weekend | facility 8 only | 147 | 167.69% | 15 | 15 |

Every logged figure reproduces (98.7% / 99.8% / 0 / 0). **Two provenance gaps, both one column wide:**
`2026-09-04-vignette-overflow-capability.csv` carries neither the **peak** nor the count under the
**design's own definition** (`cap - y < 1`), which is the number the ESM sentence actually asserts; it
carries only `ratio >= 1.0`. Under the project's rule that every manuscript number traces to a CSV, (A)
cannot be written from the existing table as it stands. *(Recorded so the record is complete: a first pass
computed this on contemporaneous `occupancy` instead of `y_t+15min` and got 1 weekend slot rather than 0.
That was the wrong column, not a defect in the logged number; the logged numbers stand.)*

### (c) D05 is very nearly vacuous, and this is decided on the inputs.

Training-window occupancy std per facility, the quantity the `sigma > 5` dynamic-facility rule thresholds:

| city | facilities | sorted sigma (lowest five) | sets selected at sigma = 0 / 2 / 5 / 10 |
|---|---|---|---|
| Belgrade | 24 | **0.00, 3.34, 11.51**, 14.70, 17.75 | 24 / 23 / **22** / 22 |
| Birmingham | 28 | 33.18, 36.73, 43.49, 52.72, 63.96 | 28 / 28 / **28** / 28 |

1. **Birmingham's sweep cannot change anything.** Its lowest sigma is **33.18**, so every threshold in
   [0, 33] selects all 28 facilities. D05 is answered on Birmingham by this row and requires **no run**.
2. **Belgrade's sweep can add at most two facilities**, and there is a **gap of the B16 kind**: sigma
   values jump 0.00 → 3.34 → **11.51**, so **every threshold in (3.34, 11.51] selects exactly the same 22
   facilities**, and the prespecified `sigma > 5` sits in the middle of that band. Only sigma <= 3.34
   admits facility **10**, and only sigma = 0 admits facility **1** — which `core.low_information_facilities`
   removes anyway (1 distinct reading), so facility 1 can never enter a reported number at any threshold.
3. **D05 therefore reduces to fitting ONE facility** (Belgrade **10**) at the headline configuration and
   publishing the threshold table with its gap. It is not a four-way rerun of both cities.

### (d) M02 needs no run, and it needs one correction that is already half-recorded.

`2026-09-04-x08-e3-summary-excl.csv` already carries the conformalized-NGBoost result on the published
(X08-excluded) base: Belgrade **0.7733 → 0.8921** (n = 21), Birmingham **0.3727 → 0.9011** (n = 28,
unchanged because Birmingham excludes nothing). Winkler improves **9.93%** (Belgrade, excluded base) and
**57.05%** (Birmingham). The widely quoted Belgrade pair **0.7602 → 0.8909** and **"11.2%"** are
**pre-exclusion** figures (n = 22). EXP-027 recorded the correction and the display-item ranking carries
the base note, but `PROJECT_STATUS.md` still states the pre-exclusion pair inside a live checklist entry.
M02's remaining work is therefore a **consistency fix, not an experiment** (B17).

---

## 1. THE CLAIMS, FIXED IN ADVANCE

### 1.1 (A) — the ESM null. No new experiment; an assembly with a reproduction gate.

Reported in the ESM, not the main text (D-020). The sentence is fixed now:

> Under a training-window capacity proxy and the low-information exclusion, the allocation contrast
> vanishes: all three policies overflow 0.0% of requests on all 20 seeds in both windows. The reason is
> structural rather than incidental — "full" was defined as an **absolute** one-space margin applied
> across facilities of **53 to 1,549** spaces, so **0 of 3,340** weekday and **0 of 2,940** weekend
> healthy facility-slots can trigger the outcome event at all, against a peak healthy occupancy of
> **98.7%** and **99.8%** of capacity.

Every number in it must trace to a CSV, which fact (b) says two of them currently do not.

### 1.2 (D') — the corrected failure-case arm. TWO legs, and leg 2 is what makes it a result.

**The claim is fixed here and is narrower than the record's wording, for the reason in fact (a):**

> Interval-based abstention **withdraws a facility whose feed has gone to a constant level inconsistent
> with its training capacity, within a bounded number of steps of that change, with no anomaly detector
> attached.** It does not detect, diagnose or report a sensor failure; it says nothing about what any
> driver found on arrival; and on the real facility it is measured on a feed that was **already anomalous
> during calibration**, which is stated wherever the leg-1 number appears.

- **Leg 1 — the real case (facility 8), n = 1.** Corrected pipeline throughout. The outcome is the
  **withdrawal step**: the first test slot at or after the observed regime change (2017-03-19 18:00) at
  which `cap_train - U < SAFETY`, expressed in 5-minute steps from that change, together with whether
  withdrawal persists to the end of the window. **The pre-onset state is reported first and governs
  whether the leg is deliverable at all** (branch B in section 5).
- **Leg 2 — the prespecified synthetic level-shift probe, n = 20 healthy facilities.** The same anomaly
  class is injected into each healthy facility's test stream at a matched clock position and the
  withdrawal step is measured, giving a **distribution** rather than an anecdote and requiring **no trust
  in any dead sensor**. Injection is **relative, never absolute** (B20): the feed is pinned at
  **167.69% of that facility's own `cap_train`** — facility 8's observed overshoot — from the injection
  slot onward. Facility 8 is excluded from leg 2 (it is leg 1).
  **Matched control, without which leg 2 means nothing (B3, B7):** the same injection pinned at the
  facility's own **training median occupancy** — a stuck but *plausible* sensor. If withdrawal fires
  there at a similar step, the mechanism is reacting to constancy rather than to implausibility, and the
  claim weakens to that. Both arms are reported side by side whatever they show.

### 1.3 The quantity that varies with the demand seeds is NOT the withdrawal step

The record asks for the withdrawal step "as a distribution across seeds". **It has no distribution
across seeds**: the withdrawal step is a deterministic function of the fitted panel, and the demand seeds
vary only which requests arrive where. Reporting a constant as a distribution would be a B22-shaped error
— quoting a spread the design cannot produce. Fixed instead:

| quantity | what varies it | how it is reported |
|---|---|---|
| withdrawal step, facility 8 | nothing (deterministic) | a single measured value, with the persistence flag |
| withdrawal step, healthy facilities | the facility | a distribution over **n = 20**, median and range |
| requests routed to the anomalous facility before withdrawal, POINT vs INTERVAL | the demand seed | a paired distribution over **>= 20 seeds**, with a CI |

### 1.4 D05 and M02

D05: the threshold table (sigma = 0 / 2 / 5 / 10, both cities) with the selected sets, the measured gap,
and the headline numbers recomputed on Belgrade's 23-facility set (sigma >= 2, adding facility 10 only).
`sigma > 5` remains the prespecified primary population and is not changed. M02: a consistency fix, with
the published-base figures asserted against `2026-09-04-x08-e3-summary-excl.csv` to 4 dp.

## 2. HELD FIXED, so that nothing here is attributable to a configuration change (B6)

Belgrade, `belgrade_features_v2.parquet`, `use_15`, `y_t+15min`, level 0.90, `SAFETY = 1` space,
`HOURS = [12, 19)`, windows weekday Mar 20–21 / weekend Mar 18–19, RandomForest + HistGBR quantile
learners at the archived hyperparameters, `SEED_FIT = 42`, `R_REQ = 600`, `HOT = 0.65`, `SIG = 0.0035`,
`ANCHOR_K = 4`, 20 demand seeds. Intervals come from `core.adaptive_conformal_stream` with gamma from
`core.select_gamma_on_calibration`; capacity is `max(occupancy)` on the **training split only**;
exclusion is `core.low_information_facilities` and nothing else. **No second definition of "matured",
"low information" or "capacity" is written anywhere in R-Phase 5** (B9).

**Facility 8's standing, restated because it is the one place this can go wrong:** it is reinstated as a
**candidate destination and as the subject of leg 1 only**. It contributes to **no** forecast-evaluation
number — no PICP, MPIW, Winkler, dispersion, worst-cell, contrast or coverage figure anywhere in the
paper — and **no outcome is computed from its occupancy readings**, because those are the dead feed. Its
`y_true` is used for nothing. This is the D-018 boundary and it is not moved.

## 3. THE GATE, run before any new number is read (the EXP-027 pattern, B17)

1. **(A) gate.** The new capability table must reproduce **every cell** of
   `2026-09-04-vignette-overflow-capability.csv` to 4 dp before its two new columns are read. Zero
   failures required. The 2026-09-04 file is **not overwritten**; the new file supersedes it by date.
2. **(D') gate.** Facility 8's fitted panel must reproduce `cap_train = 65.0` and the `cap_fullrecord =
   109.0` pair in `2026-09-04-vignette-capacity-proxy.csv` exactly, and the healthy-base assignment
   totals must reproduce `2026-09-04-vignette-seeds.csv` for the seeds already logged, before any
   facility-8 request count is read. A leg-2 injection at **zero shift** must reproduce the un-injected
   panel bit-for-bit (the null-injection control).
3. **D05 gate.** The sigma >= 5 arm of the sweep must reproduce
   `2026-09-04-x08-core-headline-excl.csv` to 4 dp before the sigma >= 2 arm is read.
4. **The full state gate (50 / 48 / 130) is re-verified after every result-generating run**, and the
   frozen manifest re-checked. Any change to `core.py` or the suite re-runs the whole gate.

## 4. RESUMABILITY (A1)

Every result-generating script checks its output CSV for completed units, processes until `--budget`,
**flushes after every unit**, exits, and prints `REMAINING` or `ALL DONE`. Units: (leg, facility) for
(D') leg 2; (window, seed) for the demand simulation; facility for D05. A facility that yields no rows
writes a `SKIPPED-*` marker (A2).

## 5. OUTCOMES — every branch decided now, including the degenerate ones (B20, and because EXP-029's list was incomplete)

**(D') leg 1, checked in this order:**

- **A — DELIVERABLE.** Facility 8 is *not* withdrawn during the pre-onset stream, and is withdrawn at a
  finite step after 2017-03-19 18:00 that persists. Report the step; the claim in 1.2 stands as written,
  with the calibration-contamination caveat attached.
- **B — VACUOUS, and this is a real possibility given fact (a2).** Facility 8 is *already* withdrawn
  before the onset, because a calibration pool 64% contaminated by the constant-0 run already yields an
  upper bound above `cap_train - 1`. Then **there is no withdrawal event to report**, the mechanism
  narrative is **not deliverable on the real facility**, and leg 1 is written up as a null with that
  explanation. Leg 2 still runs and carries the claim; (A) is unaffected. **This outcome is reported, not
  engineered around** — in particular the pre-onset window is not trimmed, the onset is not redefined,
  and no other facility is substituted for facility 8.
- **C — NEVER WITHDRAWN.** The upper bound never crosses the capacity line even at a reported 109 against
  a training capacity of 65. Then the abstention claim is **false on the real case** and is dropped from
  the paper entirely; leg 2 decides whether anything survives.
- **D — INTERMITTENT.** Withdrawal fires and unfires. Report the duty cycle rather than a step, and the
  claim narrows to "withdraws intermittently", which is materially weaker and is written that way.

**(D') leg 2:**

- **E — the mechanism is a property of the method.** Withdrawal fires at a bounded step at most healthy
  facilities under the implausible-level injection, and materially later or not at all under the
  plausible-level control. This is the strongest available outcome and makes leg 1 an illustration rather
  than the evidence.
- **F — the control also fires.** Then abstention is responding to *constancy*, not to implausibility.
  Reported as such; the claim narrows to "withdraws a facility whose feed goes constant", which is still
  true and still useful, and the paper says which of the two it is.
- **G — nothing fires anywhere.** The abstention claim dies completely and D-019 (D') is recorded as
  not deliverable, alongside (D). (A) stands alone and the ESM says so.

**D05:** **H — insensitive** (the 23-facility Belgrade headline moves less than the reporting precision):
publish the table and the gap, `sigma > 5` stands. **I — sensitive**: the threshold is doing work, which
is a finding against a disclosed-but-unvaried rule, and it is reported at full size in the ESM with the
direction stated even if it is against us.

**Predictions recorded now so the outcome is logged either way (C4).** Leg 1 lands in **branch B** — a
pool 64% contaminated by the constant-0 run should already have widened the interval past a 65-space
capacity before the onset. Leg 2 lands in **branch E**, with the plausible-level control not firing.
D05 lands in **H**, because facility 10 (sigma 3.34) is one facility of 23 and near-degenerate.
**No prediction is recorded for the seed-level request counts.**

## 6. FORBIDDEN

Quoting any number from the archived EXP-015 run, including 105 / 84.8% / 14 (B21); using facility 8's
occupancy as ground truth for any outcome; letting facility 8 enter any forecast-evaluation statistic;
trimming the pre-onset window, redefining the onset, or substituting a different facility after seeing a
leg-1 outcome; changing the injection level, the control, the safety margin or the windows after seeing
any output; using an absolute threshold across facilities of 53–1,549 spaces (B20); reporting the
withdrawal step as a distribution across demand seeds (1.3); relaxing `MIN_CELL`, the exclusion rule or
any property test to make something reportable (B19); quoting a pre-exclusion value beside a
post-exclusion one, or any before/after pair without naming its base (B17); giving either deliverable a
main-text display item (D-020); and opening `06_manuscript/CTR/ctr_word_prep.tex`, the .docx or the cover
letter during R-Phase 5.

## 7. DELIVERABLES

`05_results/tables/2026-09-04-esm-overflow-capability.csv` (A, superseding by date, not overwriting);
`2026-09-04-failure-case-{panel,withdrawal,requests}.csv` and `2026-09-04-failure-case-injection.csv`
(D' legs 1 and 2); `2026-09-04-d05-threshold-sweep.csv`; and the M02 consistency note in the trackers.
Scripts are dated, resumable, flush per unit, and overwrite nothing logged. EXP-031 is written in
`EXPERIMENTS_LOG.md` as the work proceeds, not at session end (protocol step 11).

---

## 8. AMENDMENT — 2026-09-04, revision 42, written BEFORE any (D') outcome was computed

**Trigger.** While checking the feature structure for leg 2's injection (an input check), an arithmetic
consequence of the corrected capacity proxy surfaced that section 5's branch list does not cover, and
EXP-029's incomplete branch list is exactly the mistake B20 exists to prevent. This amendment is written
**before the leg-1 or leg-2 script was run**; no `U`, no withdrawal step and no request count had been
computed when it was written.

### 8.1 The consequence

The corrected pipeline predicts `yhat = occupancy + RF(delta)`, and `cap_train` for facility 8 is **65**
against a reported feed of **109**. Once the lag features carry the new level, `yhat` approaches 109 and
`cap_train - yhat` is about **-44**, which is below `SAFETY`. **The POINT policy therefore also stops
assigning to the facility.** The archived contrast — POINT sends 105 requests, INTERVAL sends 14 —
existed partly because the archived capacity proxy was **109**, the dead sensor's own constant, making
`cap - yhat` positive whenever `yhat` sat below 109. Under a training-only proxy that gap closes for both
policies.

**This is not a reason to keep the archived proxy.** It means the honest estimand is not *whether* the
interval policy withdraws while the point policy does not, but **how much earlier** it does so.

### 8.2 New branch B'

- **B' — BOTH POLICIES WITHDRAW.** Both `cap_train - U < SAFETY` and `cap_train - yhat < SAFETY` become
  true. Then there is no presence/absence contrast and none may be claimed. The reported quantity is the
  **withdrawal lead time**, defined in 8.3. If the lead time is zero, the interval adds nothing here and
  that is the finding.

### 8.3 The estimand this adds, and the part of it that is guaranteed rather than measured

> **Withdrawal lead time L** = (first step at which the POINT policy stops assigning) minus (first step at
> which the INTERVAL policy stops assigning), in 5-minute steps from the injected or observed level change.

**L >= 0 by construction, and the paper must say so.** The conformal upper bound satisfies `U >= yhat` at
every step, so `cap - U <= cap - yhat`, so the interval policy can never withdraw *later* than the point
policy. **The sign of L is arithmetic, not evidence.** Only its **magnitude** is empirical, and only the
magnitude may be reported as a result. Any sentence that presents "the interval policy withdrew first" as
a finding is forbidden by this amendment.

### 8.4 Leg 2's feature handling, fixed here

Injecting a level into a facility's feed must also move the **lag and rolling features**, or the
forecaster never learns the new level, the point policy never withdraws, and the lead time is inflated in
our own favour. Features are therefore **rebuilt from the injected occupancy series** by the conventions
measured on the inputs (`lag_{5,10,15,30,45,60}min` = positional shifts of 1/2/3/6/9/12;
`roll_mean_{30,60}min` = `shift(1).rolling(6 or 12).mean()`; `roll_std` likewise), and **both arms of
leg 2 use rebuilt features**, so the comparison is internally consistent and the null injection is
bit-identical by construction. Models are trained on the untouched parquet features (the training split
is never injected). The rebuilt-vs-parquet agreement on the un-injected test series is reported as a
fidelity diagnostic, not hidden.

### 8.5 Added to the forbidden list

Presenting the **sign** of the withdrawal lead time as an empirical result; injecting a level into the
target without also rebuilding the lag and rolling features; and reverting to the `cap_fullrecord` proxy
for any policy comparison for any reason.

---

## 9. AMENDMENT 2 — 2026-09-04, revision 42, written AFTER leg 1 and leg 2 returned and BEFORE the two checks below were run

**This amendment is written with the leg-1 and leg-2 outcomes in hand and says so.** It adds two checks
and changes **no criterion, no threshold and no claim** — sections 1.2, 8.3 and the branch list stand
exactly as written. Both checks exist to attack the result just obtained, not to rescue it.

**The outcome being attacked.** Branch **B'** fired, with a **lead time of exactly 0 steps**: at facility 8
both policies withdraw at the first post-onset slot, and under the implausible injection all 20 healthy
facilities give `step_interval = step_point = 0`. Mechanism: the forecaster is **delta-modelled**
(`yhat = occupancy_t + RF(features)`), so it is anchored on the **currently reported** occupancy; a
reported level above the training capacity proxy is therefore visible to the **point** forecast
immediately, and there is no learning lag for abstention to beat.

### 9.1 Sensitivity control — can this design produce a NON-zero lead time at all? (B11, B13)

A zero from an instrument that cannot register anything else is not a finding. The un-injected (`none`)
arm and the plausible control already produced lead times spanning **0 to 304 steps**, so the measurement
demonstrably registers non-zero leads on the same code path. **This is recorded as the sensitivity
control and no new run is needed for it.** Had every arm returned 0, the correct conclusion would have
been that the instrument was broken, not that the effect was absent.

### 9.2 Injection-level sweep — is there ANY regime with a positive lead time?

`step_interval = step_point = 0` is expected whenever the injected level exceeds `cap_train`, because both
`cap - U` and `cap - yhat` go negative at the same slot. The open question is whether a lead time exists
**below** capacity, where the point forecast does not trip but the widening interval does. Prespecified
now, before running:

- **Sweep the injected level over `{0.80, 0.90, 0.95, 0.98, 1.00, 1.05, 1.20, 1.6769} x cap_train`**, all
  20 healthy facilities, everything else held exactly as in section 2 and 8.4.
- **Every level is reported**, including those where the lead time is zero or where nothing withdraws.
  **No level may be selected as a headline**, and the 1.6769 level remains the prespecified primary
  because it is facility 8's observed overshoot (B16: publish the band, not the favourable point).
- **The interpretation is fixed in advance:** a positive lead time found only at levels **below**
  capacity is a statement about a regime, and it is reportable **only** alongside how often the healthy
  record actually reaches that regime — which `2026-09-04-esm-overflow-capability.csv` already answers
  (peak healthy occupancy 98.74% / 99.83% of capacity, and **0** slots at or above capacity). A lead time
  in a regime the data never exhibits is **not** an operational finding and must not be written as one.

### 9.3 Mask-identity check, which replaces the >= 20-seed request simulation

Section 1.3 assigned the paired request counts to the demand seeds. If the two policies' **availability
masks** for facility 8 are identical at every post-onset slot, then their request counts are identical for
**every** seed by construction, and simulating 20 of them measures a difference that is zero by
arithmetic. **Prespecified:** assert mask identity slot by slot. If it holds, the seed simulation is not
run and the reason is recorded; if it fails at any slot, the seed simulation runs as originally specified.

### 9.4 What this does NOT do

It does not search for a configuration in which interval-based abstention wins. If the sweep finds a
positive lead time only below capacity, the ESM says exactly that, with the frequency of that regime
beside it, and **(D') remains not deliverable as an operational claim** (branch G). Reversing that
judgement would require reopening D-019, not reinterpreting this sweep.
