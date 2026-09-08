# PRESPECIFICATION — the NGBoost seeding fix and the E3 regeneration

**Written 2026-09-05, revision 44, BEFORE the fix was applied and before any number was regenerated.**
Eighth prespecification in this project. Authority: the author's answer of **option 1** to record
section 7 (2026-09-05), LESSONS_LOG **A18**, and EXP-032's branch **R**, which fired, was followed, and
left the defect attributed and unrepaired pending exactly this answer.

**Why a prespecification for a one-line fix.** The line is one line; what it regenerates is a **published
figure** (M02). A regeneration whose acceptance criterion is chosen after seeing the new numbers is the
forbidden repair wearing a bug-fix costume. Section 4 fixes every criterion and section 6 every outcome
branch, including the branch in which the fix is applied and then **reverted**.

---

## 0. FACTS MEASURED FIRST, BECAUSE FOUR OF THEM CHANGE THE PLAN

### (a) A18 is independently reproduced, and the resume-boundary mechanism is now measured directly

`03_code/tests/2026-09-05-ngboost-determinism-probe.py` -> `05_results/tables/2026-09-05-ngboost-determinism-probe.csv`.
Belgrade facility 2, real training data built exactly as `2026-09-03-e3-baselines.py` builds it
(n_train = 2069, p = 15), predictions compared on the 1,015 test rows.

| arm | max abs delta, predicted `loc` | max abs delta, predicted `scale` |
|---|---|---|
| **A** two `NGBRegressor(random_state=42)` fits, one process, identical data | **1.290 cars** | 0.670 |
| **B** the same, with `np.random.seed(42)` immediately before each fit | **0.000000** | **0.000000** |
| **C** a fit after a **different amount of global-RNG consumption** (a different resume boundary), no fix | **1.895 cars** | 0.706 |
| **C** the same, **with** the fix | **0.000000** | **0.000000** |

Revision 43 measured arm A only. **Arm C is new and it is the arm that matters**, because A18's actual
claim is not "two fits differ" but "*the archived numbers depend on where the resume boundaries fell*".
That is now demonstrated rather than inferred: changing only the process history, with the data, the
estimator and `random_state` all identical, moves the predicted mean by **1.9 cars**. The fix removes it
in both arms, exactly.

### (b) The regeneration is confined to ONE arm of ONE script, and the other arm has no NGBoost in it

`2026-09-03-e3-baselines.py` fits NGBoost only under `--arm A3_v2_daychunk`. The `A12_v1_paired` arm
(row 1 of T6, D-022) computes `EnbPI-oldchunk` and `EnbPI-daychunk` from one shared MAPIE fit and never
touches NGBoost. **`A12_v1_paired` rows are therefore held byte-identical and are a control, not an
output** (section 4.3).

### (c) Nothing else in the affected path reads the GLOBAL numpy RNG — predicted, and then tested

`core.moving_block_bootstrap_ci` uses `np.random.default_rng(seed)` (an isolated generator);
`RandomForestRegressor`, MAPIE's `BlockBootstrap` and `TimeSeriesRegressor` all take an integer
`random_state`, which `check_random_state` turns into a private `RandomState`; `agaci_ewa` and the
`core` conformal streams are deterministic. So seeding the global RNG is predicted to move **no**
non-NGBoost cell. **This prediction is not assumed — it is section 4.3's gate**, and it is the one that
can revert the fix (branch **N4**). Note the clean-room run already supports it from the other side:
every differing cell it found was NGBoost or NGBoost-conformal (EXP-032).

### (d) The downstream chain is four files deep, and one of its links has no generating script

`2026-09-03-e3-{belgrade,birmingham}-per-facility.csv` -> `2026-09-04-x08-reaggregate.py --filter
{off,on}` -> `2026-09-04-x08-e3-summary-{control,excl}.csv`, of which **`-excl` is the source of the
published M02 figures**; then `2026-09-04-x08-before-after.py` (T6) and `2026-09-04-display-items.py`.

**The link with no writer:** `05_results/tables/2026-09-03-e3-summary.csv` is produced by no script in
the tree (recorded in `2026-09-04-x08-reaggregate.py`'s own header as a provenance finding, and it is the
R-Phase 6 prespecification's branch **S** class). Measured here: its sha256 is
`6ec70341608e8c35e2a05b50624136b26c0ea6b5676d2249c49f809cf4da7dda` — **byte-identical to
`2026-09-04-x08-e3-summary-control.csv`** (manifest rows 128 and 177). The archived ad-hoc aggregation
and the re-aggregator's local aggregation therefore agree **exactly**, not merely to the control's 4 dp.

**Consequence, stated before the run rather than discovered after it.** `03_code/tests/2026-09-04-x08-control-check.py`
compares the recomputed `control` summary against that archived file. Once the per-facility inputs change,
that comparison becomes a comparison against a **stale** file and **will fail** — legitimately, and by
roughly 0.0001-0.0006 in `mean_PICP`, against its 5e-5 tolerance. Section 3.4 fixes what is done about it,
**and it is not editing the test.**

---

## 1. WHAT THIS DELIVERS

1. The fix: `np.random.seed(SEED)` immediately before each NGBoost fit in
   `03_code/src/conformal/2026-09-03-e3-baselines.py`, inside `fit_ngboost`, so it cannot be separated
   from the fit it protects, with a dated comment block naming A18 and this document.
2. Regenerated `05_results/tables/2026-09-03-e3-{belgrade,birmingham}-per-facility.csv`, arm
   `A3_v2_daychunk` only.
3. Regenerated `2026-09-03-e3-summary.csv`, `2026-09-04-x08-e3-summary-{control,excl}.csv`, and every
   T6/display artifact that reads them.
4. `05_results/tables/2026-09-05-ngboost-reseed-before-after.csv` — every changed cell, per facility and
   per method, with the superseded value beside it. **B25's rule: the number gets a CSV naming its
   population at the moment it is computed.**
5. The superseded CSVs retired under `05_results/tables/_superseded/` with a README carrying the sha256
   on both sides (A6, and the A17 register pattern).
6. A re-cut `MANIFEST-outputs.csv`, a passing `verify.py`, and a rebuilt package.

## 2. HELD FIXED (B6)

`core.py` and both test suites are **not modified**. No hyperparameter, no feature set, no split, no
gamma rule, no exclusion rule, no horizon, no level, no facility set. `SEED = 42`. The NGBoost
configuration (`Normal`, `n_estimators=300`, `learning_rate=0.03`) is unchanged. The A12 arm is not
re-run. `E3_ARCHIVED` in the re-aggregator holds **2026-08-04 pre-audit** values as a diagnostic column
and is not touched. Prose stays shut: no manuscript, ESM or cover-letter file is opened.

**One seed for every facility, not `SEED + facility_id`.** Considered and rejected: the facilities carry
different data, so a shared RNG stream produces different fits anyway, and a per-unit seed would be a new
convention to document and defend for no measured gain. The requirement is only that the fit not depend
on process history, which section 0(a) arm C shows a constant seed satisfies.

## 3. THE GATE, in order, and the order is part of the gate

1. **State gate BEFORE anything is touched:** 50 / 48 / 129-of-130, zero failures, and `verify.py` PASS
   at 225 entries. *(Recorded 2026-09-05, before the fix: all four phases passed.)*
2. **The probe (0a) must PASS before the fix is applied.** It did.
3. **The B17 base check.** Before regenerating, assert that the superseded per-facility CSVs still hash
   to the manifest — i.e. that the "before" column of every delta this experiment quotes is the number
   actually logged and shipped, not a number recomputed for the occasion.
4. **The stale-summary problem is closed by REGENERATION, not by editing the test.**
   `2026-09-03-e3-summary.csv` is regenerated from the post-fix `--filter off` output, which section 0(d)
   proves is byte-identical to it on the pre-fix inputs. **Stated plainly and not buried:** after that
   substitution, the E3 pair of `2026-09-04-x08-control-check.py` compares a file against its own source
   and is a **tautology**. Its evidential value is the **pre-fix** run, which is recorded with its
   measured check count in EXP-033 and stands as the proof that the re-aggregator reproduces the original
   ad-hoc aggregation. The test is **not** edited, **no tolerance is touched**, and the five non-E3 pairs
   remain live checks. Any other course — pointing the test at a new filename, or relaxing its 5e-5 —
   would be worse: the first hides the tautology, the second is the forbidden repair.
5. **State gate after the regeneration**, plus a re-cut manifest and a `verify.py` PASS.

## 4. THE ACCEPTANCE CRITERIA, fixed here

**4.1 Tolerance classes** are the R-Phase 6 table, unchanged and not re-derived: PICP, every count,
`n_test`, facility sets and integers **exact**; MPIW, Winkler and derived width statistics **relative
1e-12**; bootstrap CI bounds **relative 1e-9**.

**4.2 What is allowed to move:** rows with `method` in {`NGBoost`, `NGBoost-conformal`} in the two
per-facility CSVs, and the summary/T6/display cells computed from them. Nothing else.

**4.3 NEGATIVE CONTROL, and it is the gate that can revert the fix.** Every row with `method` in
{`EnbPI`, `AgACI-style`, `ACI-crosscheck`, `EnbPI-oldchunk`, `EnbPI-daychunk`}, and every `SKIPPED-*`
row, must reproduce its superseded value **within 4.1** — PICP exact, widths to 1e-12, CI bounds to
1e-9 — and `n_test`, `dynamic`, `degenerate` and `cal_score_max` must be **exact**. A single failure
means the seeding leaked out of the NGBoost fit, and the fix is **reverted**, not accommodated
(branch N4).

**4.4 RESUME-BOUNDARY CONTROL, on the real pipeline and not on the probe.** After the regeneration,
three Belgrade facilities are re-run from a wiped state with `--budget` small enough to force **one
facility per process** — a deliberately different resume boundary from the one that produced the
regenerated file. Their NGBoost and NGBoost-conformal cells must match under 4.1. This is the check that
actually closes A18: it tests the *resumability contract*, which the probe can only simulate. If it
fails, the fix does not do what it was authorised to do and the result is reported as such.

**4.5 The M02 movement branches are fixed BEFORE the number is seen.** M02 published on the excluded
base: Belgrade **0.7733 -> 0.8921**, Winkler **-9.93%**; Birmingham **0.3727 -> 0.9011**, **-57.05%**.
The clean room measured aggregate drift of 0.0001 (NGBoost) and 0.0006 (NGBoost-conformal) on the
all-facility Belgrade base, so the expectation is a third-to-fourth-decimal move. See section 6.

## 5. RESUMABILITY AND ENVIRONMENT

The regeneration uses the existing script's own resume logic (A1): it flushes after every facility and
prints `REMAINING` / `ALL DONE`. `PYTHONDONTWRITEBYTECODE=1` in every call (A12). A sudden
`ModuleNotFoundError` is treated as **A16** — re-run `restore-env.sh`, then `verify-state.sh deps` — and
is not debugged as a package problem.

## 6. OUTCOMES — every branch decided now, including the unwelcome ones

- **N1 — every changed cell is NGBoost-family and M02 moves by <= 0.002 in PICP and <= 0.5% relative in
  Winkler.** *(Expected.)* Publish the regenerated figures; the superseded M02 pair goes on the
  never-quote list beside the pre-exclusion pair; the defect and its fix are recorded as a **measured**
  reproducibility finding and become one sentence in the reproducibility paragraph. **Not** a ninth
  display item — D-020 is not reopened for it (a T6 row would need something to leave, and the finding is
  about the package rather than about the evaluation protocol of the literature).
- **N2 — M02 moves by more than that, but the claim's direction and magnitude survive** (a conformalized
  NGBoost still goes from badly under-covering to near-nominal, Winkler still improves by tens of
  percent). Publish the regenerated figures and state the size of the move explicitly in the ESM rather
  than letting it read as a rounding change. Tell the author before the trackers are written, because the
  size is then a fact about the paper and not only about the package.
- **N3 — the claim changes qualitatively.** STOP. Nothing is published, the trackers record what was
  found, and the options go to the author. This is working rule 11 and it is written here so that it is
  not a judgement call made at the moment it would be inconvenient.
- **N4 — a non-NGBoost cell moves beyond 4.1.** The fix has leaked. **Revert it**, restore the superseded
  CSVs from `_superseded/`, and report. Do not accommodate it by widening 4.3.
- **N5 — the resume-boundary control (4.4) fails.** The fix does not close A18. Report at full size,
  keep the regenerated numbers only if 4.3 passed, and reopen the question with the author.
- **N6 — a facility that previously fitted now fails to fit, or vice versa** (the B5/facility-1 case).
  Record it as a change in the `FAILED` rows, do not suppress it, and check it against the `status`
  column of the superseded file before writing any sentence about it.

## 7. FORBIDDEN

Modifying `core.py` or either test suite; editing `2026-09-04-x08-control-check.py` or any tolerance in
it; widening 4.1 or 4.3 after seeing an output; regenerating the `A12_v1_paired` arm; refitting any
forecaster outside the E3 arm; quoting the superseded M02 pair beside the regenerated one, or anywhere,
once N1/N2 fires; deleting a superseded CSV rather than retiring it (A6); describing the regenerated
numbers as reproducing the archived ones; presenting the seeding defect as a defect of the paper's
methods rather than of its packaging; touching the manuscript, the ESM or the cover letter; and starting
D-019 (C) or the clean-room run before this experiment's gate has passed.

## 8. DELIVERABLE FILE LIST

`03_code/tests/2026-09-05-ngboost-determinism-probe.py`,
`05_results/tables/2026-09-05-ngboost-determinism-probe.csv`,
`05_results/tables/2026-09-05-ngboost-reseed-before-after.csv`,
`05_results/tables/_superseded/2026-09-05-pre-reseed/` (+ README with sha256 on both sides),
the edited `03_code/src/conformal/2026-09-03-e3-baselines.py`, the regenerated tables of section 1.3,
a re-cut `00_admin/2026-09-04-shipped-outputs/MANIFEST-outputs.csv`, and a rebuilt package.
**EXP-033 is written in `EXPERIMENTS_LOG.md` as the work proceeds, not at session end.**
