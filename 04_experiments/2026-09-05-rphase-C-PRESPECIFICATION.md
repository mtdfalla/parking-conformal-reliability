# PRESPECIFICATION — D-019 option (C), the relative-threshold allocation demonstration

**Written 2026-09-05, revision 44, AFTER section 0 was measured on the inputs and BEFORE any policy was
scored.** Ninth prespecification. Authority: **D-023** (which promotes (C) and states the constraint that
decides whether it is publishable), the author's confirmation of D-023 on 2026-09-05, D-016 (no new data,
no third city), D-018 (the exclusion), D01 (training-only capacity), D02 ("detour" is retired), D03 (>= 20
demand seeds), D-020 (the display-item budget is closed and is **not** reopened here).

**theta's provenance is a separate, earlier document:** `04_experiments/2026-09-05-theta-LITERATURE-ANCHOR.md`,
written before this file and before any (C) code existed. **theta = 0.90 primary, band [0.90, 0.95], 0.85
as an outside endpoint**, from Caicedo (2009, TR-C: deployed PARC systems display "no free spaces" above
**90% and 95%**), Levy et al. (2013, Transportmetrica A: breakdown above **92-93%**) and Millard-Ball et
al. (2014, TR-A: the probability of finding a space breaks down at **85-90%**). **EXP-031's sweep is
corroboration and is never the source; 0.98 — the value the sweep preferred — is deliberately not adopted.**

---

## 0. FACTS MEASURED ON THE INPUTS FIRST. All four checks pass, and one of them constrains the claim.

`05_results/tables/2026-09-05-rel-alloc-section0.csv`, produced by `--phase s0`, which scores **no policy**
and computes **no outcome**. Base: the EXP-029 machinery's own dynamic, coordinate-matched, low-information-
excluded set (**n = 20**; facility 8 excluded on both windows by `core.low_information_facilities`).

| window | theta | facility-slots | event slots | event rate | facilities with >= 1 event | POINT withdraws | INTERVAL withdraws | **INTERVAL-only withdrawn** | POINT-only |
|---|---|---|---|---|---|---|---|---|---|
| weekday | 0.850 | 3,340 | 240 | 7.19% | 5 | 7.43% | 9.82% | 80 | 0 |
| weekday | 0.900 | 3,340 | 183 | 5.48% | **3** | 5.42% | 6.89% | 49 | 0 |
| weekday | 0.925 | 3,340 | 175 | 5.24% | **3** | 4.88% | 5.69% | 27 | 0 |
| weekday | 0.950 | 3,340 | 121 | 3.62% | **1** | 3.65% | 4.37% | 24 | 0 |
| **weekend** | 0.850 | 2,940 | 985 | 33.50% | 14 | 33.44% | 40.20% | 199 | 0 |
| **weekend** | **0.900** | 2,940 | **610** | **20.75%** | **12** | 20.88% | 29.25% | **246** | 0 |
| weekend | 0.925 | 2,940 | 413 | 14.05% | 8 | 13.84% | 20.65% | 200 | 0 |
| weekend | 0.950 | 2,940 | 304 | 10.34% | 6 | 9.73% | 14.22% | 132 | 0 |

**(a) B20 — does the outcome event occur on the population that will actually be scored?** On the weekend
window, **yes and by a wide margin**: 20.75% of healthy facility-slots at theta = 0.90, across **12 of 20**
facilities, and still 10.34% across 6 facilities at 0.95. This is the check the dead vignette failed 0-for-
3,340 (EXP-029), and it is why the absolute one-space bar was replaced rather than the experiment repeated.
It independently reproduces D-019 #4's recorded 20.8%.

**(b) B23 — what does the COMPARATOR do at the outcome step?** This is what killed (D'). Here the two
policies **genuinely diverge**: at the primary cell there are **246 facility-slots withdrawn by INTERVAL
and offered by POINT**, and 132-246 across the whole band. `point_only_withdrawn_slots = 0` everywhere,
which is arithmetic (`U >= yhat` always) and is reported as arithmetic, never as a finding. **The contrast
is therefore not zero by construction** — the failure mode that ended R-Phase 5 does not apply in this
regime.

**(c) B24 — does the record exhibit the favourable band?** Yes: the event rate is non-trivial at every
theta in [0.90, 0.95]. Unlike (D'), whose only real anomaly sat at 167.7% of capacity where the lead is
identically zero, this regime is one the data exhibits on 20.75% of slots.

**(d) THE CONSTRAINT SECTION 0 IMPOSES, and it is fixed here rather than discovered later.** The **weekday
window is thin**: 3 facilities carry the event at theta = 0.90 and **1** at theta = 0.95. This project has
been burned three times by an aggregate dominated by one facility (B14, B18, B20). **Therefore: the
weekend window is the PRIMARY and the weekday window is reported beside it with its facility count
attached; and NO claim of any kind is made from a window x theta cell in which fewer than 3 facilities
carry the event.** That rules out weekday theta = 0.95 in advance, before its number exists.

## 1. WHAT IS RUN

`03_code/src/conformal/2026-09-05-relative-threshold-allocation.py`. Every component is **imported** from
`2026-09-04-allocation-vignette.py` (B9): the panel build, the RF delta model, the HistGBR quantile pair,
`core.select_gamma_on_calibration`, `core.adaptive_conformal_stream`, the **training-only** capacity
proxy, the demand model (600 requests, 0.65 hot mixture, ~350 m concentration, the recomputed training-only
anchor), the 20 seeds, and the **MARGIN** negative control at INTERVAL's own mean conservativeness. This
file adds exactly two things:

1. **The availability rule.** A facility is offered iff **predicted occupancy <= theta x its own
   training-window capacity proxy**. POINT uses `yhat`, INTERVAL uses the ACQR upper bound `U`, MARGIN uses
   `yhat + margin`, where `margin` is the mean of `U - yhat` over the window (9.01 spaces weekend, 9.78
   weekday) — so MARGIN is matched to INTERVAL's average conservativeness and separates *calibrated
   intervals* from *any conservatism* (B3).
2. **The outcome.** A **BAD ASSIGNMENT** is a request routed to a facility whose **TRUE** occupancy at
   that slot is at or above the same bar — the driver was sent to a practically full car park.

No new data, no third city, no refit of any forecaster, no second definition of capacity, "matured" or
"low information". `SEED_FIT = 42`; the fit is done once and the 20 seeds vary **only the requests**, so
the three policies are scored on **identical requests within a seed** and every per-seed contrast is
paired.

## 2. THE PRIMARY STATISTIC, fixed before any of it is computed

**Primary cell: weekend, theta = 0.90.**

**Primary statistic: BAD ASSIGNMENTS PER REQUEST** (`bad_assignments_per_request`), not per *assigned*
request. Stated with the reason, because the choice is not innocent: a policy that abstains more has a
smaller denominator, so "bad assignments as a share of assignments" flatters the more conservative policy
by construction. Per-request is the quantity a city would care about and it cannot be improved by
abstaining alone.

**Reported beside it, always, in the same sentence and the same table:** the **abstention rate**
(`1 - assigned_rate`), the mean straight-line distance, and the **MARGIN** control's values.

**Uncertainty:** 20 paired seeds. Report the mean paired difference, its range across seeds, and the
**number of seeds in which the sign holds** (e.g. "19 of 20"). No p-value is computed on 20 seeds of a
shared panel; the seeds vary the requests only and are not independent replicates of the world, and
saying so is more honest than a test that would imply they are.

## 3. THE GATE

1. State gate 50 / 48 / 129-of-130, zero failures, before and after.
2. `--phase s0` must have been run and recorded **before** `--phase run` — done, section 0 above.
3. The imported machinery must be the EXP-029 machinery: the capacity proxy written by this run must equal
   `2026-09-04-vignette-capacity-proxy.csv` for every facility (a reproduction check on the import, so a
   silent divergence in the panel build is caught before any outcome is read).
4. `point_only_withdrawn_slots` must be **0** in every cell. It is arithmetic; a non-zero value means the
   panel is inconsistent and the run is void.
5. Manifest re-cut and `verify.py` PASS at the end.

## 4. OUTCOME BRANCHES — every one fixed now, including the ones nobody wants

- **F — FRONTIER (the expected outcome, per D-023).** INTERVAL makes **fewer bad assignments per request**
  than POINT and abstains **materially more**. Reported as a **trade, not a victory**: both numbers in the
  same sentence, the abstention cost first if it is the larger movement. This is an operational
  demonstration because it shows the **decision** consequence — which is precisely what D-021 records the
  paper as lacking.
- **W — DOMINANCE OVER THE CONTROL.** If INTERVAL beats **MARGIN** at matched conservativeness — fewer bad
  assignments at the same or lower abstention — then the claim is about *calibration*, not about caution,
  and may be stated as such. **If MARGIN matches INTERVAL within the seed spread, the honest finding is
  "conservatism helps, and calibrated intervals are one way to get it"**, and the sentence says that.
- **N — NULL.** The paired mean difference in bad assignments per request is smaller than the seed-to-seed
  spread. Reported as a null, in the ESM, with the section-0 table beside it so the reader can see the
  experiment *could* have detected an effect. A null here is a legitimate outcome and does not reopen (C).
- **A — ADVERSE.** INTERVAL makes **more** bad assignments per request than POINT. This is possible and is
  not a bug: withdrawing the nearest facility can push a request to a further one that is also full.
  Reported as found, with the mechanism opened before any sentence is written.
- **T — THRESHOLD-DEPENDENT.** The qualitative ordering flips inside the band [0.90, 0.95]. Then **the
  demonstration is not claimed**: the honest report is that the result depends on a threshold the
  literature does not pin down (section 4 of the theta memo already concedes this is the weak point), and
  the band is published in full. **theta is NOT re-chosen to the value that works.**
- **D — DEGENERATE CELL.** Fewer than 3 facilities carry the event (weekday 0.95, known in advance). No
  claim from that cell; the number is published with its facility count.
- **X — the import check (gate 3) fails.** Stop, diagnose, report nothing.

**What happens to whichever branch fires.** It goes to the **ESM** with one main-text sentence, exactly as
(A) and (D') did. **D-020 is not reopened here.** Whether the result earns a main-text display item is a
separate decision, taken only once the result exists and its size is known, and it requires something else
to leave (D-023's accepted cost 2).

## 5. FORBIDDEN

Taking theta from EXP-031's sweep, or adopting **0.98** at any point; changing theta, the window, the
primary statistic or the primary cell after seeing any output; quoting the per-**assigned** bad-assignment
rate as the headline; reporting the frontier as a win; claiming an operational benefit without the MARGIN
comparison beside it; dropping the weekday window because it is thin (it is reported, with its counts);
dropping a facility, a seed or a slot without a rule stated on the inputs (B16); using the word "detour"
(D02); quoting any archived vignette number (105 / 84.8% / 14 / 14.8% / +49 m — all dead, B21); refitting
any forecaster; adding a display item (D-020); reading the capacity proxy off the test window (D01);
touching `core.py`, either test suite, the manuscript, the ESM or the cover letter; and running the
clean-room gate before this experiment is logged.

## 6. DELIVERABLES

`03_code/src/conformal/2026-09-05-relative-threshold-allocation.py`,
`05_results/tables/2026-09-05-rel-alloc-section0.csv`,
`05_results/tables/2026-09-05-rel-alloc-seeds.csv`,
`05_results/tables/2026-09-05-rel-alloc-summary.csv`, and **EXP-034** written in `EXPERIMENTS_LOG.md` as
the work proceeds.
