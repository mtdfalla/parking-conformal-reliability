# PRESPECIFICATION — R-Phase 6, packaging and the clean room (R01–R05, X02, X03)

**Written 2026-09-04, revision 43, BEFORE anything was built or rebuilt.** Seventh prespecification in
this project. Authority: the remediation plan's Phase 6 (D-014), D-015 #2 (the deposit stays halted),
D-018 (the exclusion rule), D-020 (the display-item budget, which R-Phase 6 does not touch), and the
revision-42 record sections 6 and 10 (R-Phase 6 is venue-independent).

**Why a prespecification for a packaging phase.** R-Phase 6 ends in a *gate* — "a from-scratch run
reproduces every manifest hash within tolerance" — and a gate whose tolerance is chosen after seeing the
output is the packaging analogue of changing the evaluation criterion after seeing the result. The
tolerance table in section 4 is therefore fixed here, on a measured floor (section 0h), before the
clean-room run exists.

**What was deliberately NOT done before this document was written:** no file was rebuilt, no lock file
written, no runner authored, no manifest cut, and the retired pre-C01 path was not run. Section 0 contains
only properties of artifacts that already exist, plus one environment measurement that contributes to no
reported number.

---

## 0. FACTS MEASURED ON THE INPUTS FIRST, BECAUSE SIX OF THEM CHANGE THE PLAN

### (a) The shipped package is pre-audit in its DATA as well as its code. It is rebuilt, not repaired.

`06_manuscript/CTR/replication/parking-conformal-reliability.zip` (2026-08-04, 48 entries) ships
`belgrade_features.parquet` and `birmingham_features.parquet` — the **v1** tables carrying the S01 and
S02/X01 leakage — not the v2 tables every current number uses. Its `03_code/src/conformal/` is the August
tree: `run_corrected.py`, the four `2026-08-04-*` scripts, and `conditional_cp.py`, `trust_abstain.py`,
`model_agnostic.py`, all three of which EXP-017 **retired**. **`core.py` is absent entirely.**

**Consequence, and it is larger than the audit's "packaging defect" framing (R03):** every number the
package could produce is a dead number. R-Phase 6 does not patch this zip; it builds a new one from the
corrected tree. The old zip is retired under `_superseded/` with a README (A6), not deleted.

### (b) R03 + X02 confirmed exactly, and X02 is wider than the audit stated.

`05_results/tables/` and `05_results/figures/` in the zip are **empty directories**;
`04_experiments/EXPERIMENTS_LOG.md` is **60 bytes**, a one-line header. `run_all.sh` invokes neither
`model_agnostic.py`/`_ma_delay.py` nor anything under `src/figures/`, while `README.md` line 6 claims the
package "reproduces **every table and figure**". It also runs `2026-08-04-allocation-vignette.py` as its
final step — **an experiment that is dead** (EXP-029, D-019).

### (c) R02 confirmed exactly. There is no runner in the live tree at all.

The zip's `run_all.sh` uses `set -e` with **no `pipefail`** and eight
`until python … | grep -q "ALL DONE"; do :; done` loops: a persistently failing step spins forever and the
traceback is swallowed by the pipe. **`run_all.sh` exists nowhere in the repository** — only inside the
zip — so R02 is "write a runner", not "fix one".

### (d) The package does not merely fail to pin a version — it pins the WRONG one.

`README.md` instructs `pip install mapie==1.4.1`. Every published EnbPI number was computed under
**mapie 1.5.0** (the EXP-025 lock). **A13 measured that this exact package difference already moved a
published number here** (5 of 22 Belgrade facilities by 1–2 coverage indicators). A reader following the
shipped instructions is directed away from the numbers in the paper.

### (e) `requirements.txt` is wrong in both directions, and the true dependency surface is measurable.

It omits `ngboost` entirely, floats `mapie>=0.8`, and lists **`statsmodels>=0.14`, which no script in the
live tree imports** — `2026-09-03-rolling-origin-inference.py` explicitly declines it in a comment and
implements Holm in six lines. Measured import surface of `03_code/src` and `03_code/tests` (excluding
`_retired/`, which adds nothing): **numpy, pandas, pyarrow, scikit-learn, scipy, matplotlib, mapie,
ngboost, holidays** — `holidays` only in the four feature-building scripts — plus **joblib,
threadpoolctl, cloudpickle** as pinned transitives that A14 shows are not optional.

### (f) A LIVE file carries the retired C01 rule and a second definition of the conformal primitives.

`03_code/src/verify_results.py` (June, adversarial checks for EXP-001–003) contains its own local
`split_cp` and `aci`, and its `aci` computes
`np.quantile(pool, lv, method="higher")` — **the C01 defect**, the exact call `core.conformal_quantile`'s
docstring warns against. It is a second definition of "the conformal quantile" sitting in the shipped code
path. **It is retired to `_retired/` or rewritten on `core.py` before anything ships**; it is not left
where a referee can run it. This is the standing "no second definition" rule (B9) applied to a file that
predates the rule.

### (g) The C01 provenance gap is BOTH worse and better than the trackers record.

**Worse.** The attribution is in **EXP-017**'s prose, not EXP-019 as `PROJECT_STATUS.md`, the T6 build note
and the revision-42 record all state — and it reads *"controlled test, **8 Belgrade facilities**, identical
data/seed, only the quantile rule differing"* **without naming which 8**. The population is unrecoverable
from the tree. **Running the retired pre-C01 path therefore cannot reproduce 0.8988 → 0.8858 even in
principle**, so the option the record describes does not do what it was expected to do.

**Better.** Closing it does not need the retired path. C01 is a one-index difference into the *same sorted
score pool*; the base learners are shared and are not refitted. The delta can be measured **paired inside
one fit** on the published base — D-017's own pattern, and A13's prescribed remedy — yielding a traceable
current number. Note the adaptive arms are not free: the ACI/ACQR streams diverge after the first
disagreement, so the conformal layer is re-run while the fit is shared. **Four options go to the author
(section 7). Nothing here is run without that answer.**

### (h) The determinism floor is MEASURED, so the tolerance table is not invented.

`03_code/tests/2026-09-04-determinism-probe.py` → `05_results/tables/2026-09-04-determinism-probe.csv`.
Three Belgrade facilities (2, 3, 4 — the first three dynamic facilities after
`core.low_information_facilities` removes 1 and 8), horizon t+15, level 0.90, four methods, everything
else held at the canonical runner's configuration (B6). Three arms: `n_jobs=-1` twice, then `n_jobs=1`.
Varying the thread count is a direct handle on A8's mechanism (thread reduction order), which is the
component that differs across machines.

| quantity | max abs, repeat at same thread count | max abs, all-threads vs single-thread | max relative |
|---|---|---|---|
| **PICP** | **0.0** | **0.0** | **0.0** |
| MPIW | 0.0 | 3.6e-15 | 2.1e-16 |
| Winkler | 7.1e-15 | 7.1e-15 | 2.2e-16 |

The calibration-selected gamma is **identical in every arm**. Only **ACI** shows any movement at all —
split-CP, CQR and ACQR are bit-identical across all three arms — which is consistent with the sequential
stream accumulating a difference that the one-shot methods do not.

**Stated with its limit, because this is the number the gate rests on:** this bounds the
**thread-reduction** term only. It does not bound a different BLAS build or a different library version,
and **A13's cross-version term is ~1e-3 in PICP — six orders of magnitude larger.** The tolerance in
section 4 is therefore *not* what makes the clean room reproduce; the **exact `==` lock is**, and the
tolerance covers only the residual that no lock can remove.

### (i) The manifest cannot be final in R-Phase 6, and this is decided here rather than discovered later.

D-020 requires **F1' and F2' to be regenerated on the X08-excluded base**, and that is an **R-Phase 7**
item. `05_results/figures/` contains no post-audit figure: the newest are `2026-08-05-frontier-figure.*`
and `2026-08-05-graphical-abstract.png`, both pre-audit, plus one vignette figure from a dead experiment.

**Decision taken here, under the standing delegation:** the manifest is cut now over the artifacts
that exist, every entry carries a `phase` column, and **`verify.py` fails closed on an artifact that is
present in the tree but absent from the manifest** — so a stale manifest is detected rather than assumed
away. The manifest is **re-cut at the end of R-Phase 7**, and that re-cut is written into R-Phase 7's task
list in `PROJECT_STATUS.md` in the same session that cuts the first one. The alternative — pulling figure
regeneration forward into R-Phase 6 — is rejected because F1'/F2' depend on D-020 typesetting decisions
that R-Phase 7 owns, and building them twice is the waste C1 exists to prevent.

### (j) `REPLICATION.md`'s verification targets are a list of numbers that are all dead.

Section 5 of the shipped `REPLICATION.md` tells a replicator to expect: *"100% of facilities' bootstrap CIs
contain 0.90"* (dead — I01, EXP-030); ACQR std **0.002** Belgrade and **0.010** Birmingham (published:
**0.0053** and **0.0234**); NGBoost PICP **0.760** and **0.384** (published: **0.7733** and **0.3727**, and
the pre-exclusion pair is on the never-quote list, B17); and *"point policy overflow 14.8%, interval policy
0.0%, mean **detour** +49 m"* — the dead vignette headline **and** the retired word. Section 6 states the
bootstrap as *"moving-block (length 20, 500 resamples)"*, when the logged design is **B = 10,000** with a
cadence-derived 3-hour block (EXP-030). **A replicator following this file today fails every target**, and
that is the single most damaging thing in the package.

### (k) The licence conflict is a two-file text fix. Plan B is already written into the package.

The zip's `LICENSE` **and** `README.md` both already state Belgrade-derived **CC0 1.0** and
Birmingham-derived **CC BY 4.0** with Birmingham City Council / UCI attribution — i.e. plan B, at file
level. The conflict (R05/X03) is exactly two other places: `USER_ACTIONS.md` step 2, which tells the author
to deposit the whole zip under *"License: CC0 (the platform default)"*, and the manuscript's Replication
section, which says both datasets are deposited *"under a CC0 license"*. `REPLICATION.md` §1 also asserts
the package **is** deposited on ETS-Data, which it is not and must not be (D-015 #2).

---

## 1. WHAT R-PHASE 6 DELIVERS

1. **`03_code/2026-09-04-requirements.lock.txt`** — exact `==` pins for the measured surface in 0(e),
   including the off-volume wheels named in the EXP-025 lock and **`ngboost`**, each with the sha256 the
   restore script already verifies; plus `03_code/2026-09-04-environment.yml` and
   `03_code/2026-09-04-Dockerfile`, and `05_results/tables/2026-09-04-environment-recorded.csv` carrying
   Python, OS, glibc, BLAS and thread-count as measured, not as assumed.
2. **`run_all.sh`** at the repository root — `set -euo pipefail`, per-step `tee` logs under `07_logs/`,
   **bounded** retries with a resume flag (never an unbounded `until`), fail-fast with a nonzero exit,
   every step wired in including the figure scripts, and a `--smoke` mode that runs one facility per city.
3. **Shipped outputs + `MANIFEST-outputs-sha256.csv` + `03_code/verify.py`** — the manifest maps
   *manuscript claim → script → input hash → output hash or tolerance class → phase*; `verify.py` exits
   nonzero on any mismatch and on any unlisted artifact (0i).
4. **`CITATION.cff`** and `01_data/DATA_DICTIONARY.md` (every column of both processed tables, units,
   provenance, and the exclusion rule with its measured threshold gap, D-018/B16).
5. **Licence restructure (plan B)** — the two-file fix in 0(k), file-level licences kept as they are, and
   the deposit **halted** regardless of venue (D-015 #2; and at the current target the deposit mandate does not
   apply at all, record section 10).
6. **A rewritten `REPLICATION.md`** whose verification targets are generated *from the current CSVs by
   `verify.py`*, never typed by hand — which is what stops 0(j) recurring.
7. **The C01 options memo** (section 7), and nothing else on C01.

**Not delivered here, and named so it is not forgotten:** F1'/F2' regeneration, the manifest re-cut, the
Elsevier→publisher sweep, and every prose change. All R-Phase 7.

## 2. HELD FIXED, so that nothing here changes a reported number (B6)

No model is refitted. `core.py` and both test suites are **not modified**; if any deliverable appears to
require modifying them, the work stops and the author is asked. The exclusion rule, the capacity proxy,
the gamma-selection rule, the fold geometry and the display-item budget are untouched. `--features v2`,
`--gamma-mode calibrated`, `SEED = 42`. No number currently in a logged CSV is regenerated; where a
shipped output must exist that does not, it is **copied** from `05_results/`, not recomputed.

**Prose stays shut.** `06_manuscript/CTR/ctr_word_prep.tex`, the .docx, the ESM and the cover letter are
not opened in R-Phase 6. The manuscript's Replication section is *listed* as an R-Phase 7 edit (0k), not
made here.

## 3. THE GATE, run before any deliverable is accepted

1. **State gate.** 50 / 48 / 130, zero failures, re-verified after every step that writes into the tree,
   and the frozen manifest re-checked (A9: the exit code and a zero failure count are the gate).
2. **Lock gate.** The lock file's pins must equal the versions `verify-state.sh deps` verifies against the
   EXP-025 lock, checked programmatically rather than by eye. A pin that disagrees is a **failure**, not a
   note — including the `mapie==1.4.1` in 0(d), which the lock corrects to 1.5.0.
3. **Runner gate.** Two negative controls, both required (B11): a deliberately failing step must make
   `run_all.sh` exit **nonzero within one iteration**, and a step whose output already exists must be
   **skipped** by the resume flag. A runner that has only ever been run on a tree that did not need it is
   not verified (C8).
4. **Manifest gate.** `verify.py` run against the **unmodified** tree must report zero mismatches, and
   against a tree with one byte flipped in one CSV must report exactly that file (B11 again).
5. **Clean-room gate.** A from-scratch run in the container built from the Dockerfile reproduces every
   manifest entry within section 4's tolerances.

## 4. THE TOLERANCE TABLE, fixed here, on the measured floor of 0(h)

| class | artifacts | criterion |
|---|---|---|
| **exact hash** | processed parquet, raw inputs, every `.py`, the lock file, the data dictionary | sha256 equality |
| **exact value** | PICP, coverage indicators, facility sets, counts, `n_test`/`n_cal`, selected gamma, crossing counts, any integer | equality |
| **numeric, tight** | MPIW, Winkler, and every derived width/efficiency statistic | relative ≤ **1e-12** |
| **numeric, declared** | bootstrap CI bounds, p-values | relative ≤ **1e-9**, seed pinned |
| **not gated** | figures (PNG/PDF bytes are renderer-dependent) | regenerated, visually checked, never hashed |

**1e-12 is roughly four orders above the measured 2.2e-16 relative floor and eight below any reported
digit.** It is a bound on the reduction-order term only; the exact `==` lock is what carries the rest
(0h). **If the clean-room run exceeds these tolerances, the tolerances are NOT relaxed** — the run is
diagnosed, and the discrepancy is reported at full size with its cause, which is the R-Phase 6 form of
"report it as prespecified and correct the interpretation".

## 5. RESUMABILITY (A1) and the environment (A11/A12/A14/A16)

Every script written in this phase checks its output for completed units, processes to a `--budget`,
flushes after every unit, exits, and prints `REMAINING` or `ALL DONE`. `PYTHONDONTWRITEBYTECODE=1` in every
call while `/sessions` is full (A12, currently 91%). A sudden `ModuleNotFoundError` on a package that
worked earlier is treated as **A16** — re-run `restore-env.sh`, then `verify-state.sh deps` — and is not
debugged as a package problem.

## 6. OUTCOMES — decided now, including the ones that would be unwelcome

- **P — the clean room reproduces within tolerance.** R-Phase 6 closes; the gate is recorded with the
  measured maximum deviation per class, not merely "passed".
- **Q — it reproduces except on ACI-family widths, within a larger but still negligible bound.** Report the
  measured bound and its mechanism (0h), widen **nothing**; the deviation goes in the ESM's reproducibility
  paragraph as a measured property of a threaded ensemble.
- **R — it fails on PICP anywhere.** PICP is bit-exact on this machine across thread counts, so a PICP
  disagreement is **not** noise: it is a version, data or code difference. Stop, attribute it, and report
  it. Do not adjust the tolerance. If it turns out a published number moves, **say so** rather than
  regenerating it silently (working rule 11).
- **S — a shipped output has no generating script.** Then it is the C01 class again: it is **not shipped**
  as a reproducible artifact, it is listed in the manifest with `provenance = unreproducible` and a stated
  reason, and the claim it supports is reviewed. This branch is written now precisely because 0(g) shows
  the class is not a one-off.
- **T — the runner cannot wire in a step because its script is retired or missing.** The step is removed
  from the README's claim rather than faked; the README claim narrows to what the runner actually does
  (the honest half of the X02 fix).

## 7. THE C01 DECISION GOES TO THE AUTHOR. FOUR OPTIONS, NOT TWO.

Recorded here so the choice is made on the evidence in 0(g) and not on the record's framing.

1. **Run the retired pre-C01 path.** Cost: it is v1/archived configuration (B21), and — decisive —
   **the 8 facilities are not named, so 0.8988 → 0.8858 cannot be reproduced even in principle.** It would
   produce a *different* number and invite the reader to compare two bases (B17).
2. **Re-measure C01 on the published base, paired inside one fit.** One dated script, shared base learners,
   the two order-statistic rules only. Produces a traceable current number with a CSV. Cost: it is a new
   measurement, not the archived one, and the T6 row's figures change.
3. **State the C01 row qualitatively in T6** — direction and mechanism, no figures, provenance column
   reading `prose-only, EXP-017, population unrecorded`. Cost: one row loses its numbers; T6 keeps 8 rows.
4. **Drop the C01 row from T6** and record in the trackers that it died for provenance. Cost: T6 loses its
   only row about the order statistic, which is the project's own most-cited code fix.

**Recommendation: (2), with (3) as the fallback if (2) exceeds a two-call budget.** It is the only
option that ends with a number the project's own rule permits printing, it uses the pattern D-017 already
adopted for exactly this attribution problem, and it needs no retired path. **Not run without the author's
answer.**

## 8. FORBIDDEN

Modifying `core.py` or either test suite; regenerating any logged CSV; relaxing a tolerance after seeing
the clean-room output; hashing a figure; shipping `verify_results.py` with its local pre-C01 quantile rule
(0f); running the retired pre-C01 path without the author's answer; depositing anything on ETS-Data
(D-015 #2); baking venue-specific packaging into the deliverables (record section 10); quoting any
number from `REPLICATION.md`'s current section 5 (0j); typing a verification target by hand rather than
generating it from a CSV; deleting the superseded zip rather than retiring it (A6); adding or removing a
display item (D-020); and opening `ctr_word_prep.tex`, the .docx, the ESM or the cover letter.

## 9. DELIVERABLE FILE LIST

`03_code/2026-09-04-requirements.lock.txt`, `03_code/2026-09-04-environment.yml`,
`03_code/2026-09-04-Dockerfile`, `run_all.sh`, `03_code/verify.py`,
`05_results/tables/2026-09-04-environment-recorded.csv`,
`00_admin/2026-09-04-shipped-outputs/MANIFEST-outputs-sha256.csv`, `CITATION.cff`,
`01_data/DATA_DICTIONARY.md`, a rewritten `06_manuscript/CTR/replication/REPLICATION.md`, `README.md` and
`USER_ACTIONS.md`, and the new package zip. EXP-032 is written in `EXPERIMENTS_LOG.md` **as the work
proceeds**, not at session end. Nothing logged is overwritten; the superseded zip and
`verify_results.py` are moved, with READMEs saying why (A6, C7).

---

## 10. AMENDMENT 1 — 2026-09-04, revision 43, written AFTER the lock file was built and BEFORE any runner, manifest or clean-room run exists

Building the lock file (R01) measured two environment facts that were not known when section 0(h) was
written. Neither changes a criterion or a claim; both narrow what the tolerance table may be said to cover,
and they are recorded here rather than folded silently into section 4.

**10.1 The determinism probe ran on a TWO-core machine.** `os.cpu_count() == 2`, so `n_jobs=-1` used two
threads and the probe's arm A-vs-C contrast is **2 threads against 1**. The reduction tree on a many-core
replicator's machine is deeper, so the measured 7.1e-15 is a floor observed at the shallowest possible
non-trivial depth, not a bound over all machines. The 1e-12 tolerance in section 4 keeps four orders of
headroom over it and is retained unchanged; what is **withdrawn** is any claim that the probe bounds
cross-machine behaviour. **The honest statement, and the one that goes in the ESM: PICP was bit-exact
under every arm tested, and width statistics agreed to machine epsilon at this thread count.**

**10.2 The environment loads TWO different OpenBLAS builds at once**, which the Dockerfile must reproduce
rather than tidy up: numpy's bundled `libscipy_openblas64_` **0.3.29** and scipy's bundled
`libscipy_openblas` **0.3.28**, alongside `libgomp` for scikit-learn's OpenMP layer. A Dockerfile that
installs a single system BLAS would be a *different* numerical environment from the one every published
number was computed under — the R01 failure mode one level down. **The Dockerfile therefore installs from
the lock file's wheels, each with its bundled library, and pins no system BLAS.** This is recorded in
`05_results/tables/2026-09-04-environment-recorded.csv` under `threadpool_info`.

**10.3 Consequence for outcome branch R.** Section 6's branch R ("it fails on PICP anywhere") is
**strengthened, not weakened**, by 10.1: a deeper reduction tree perturbs *widths*, and PICP was exact
across every arm because coverage is an indicator function of a comparison, not a sum. A PICP disagreement
in the clean room therefore still means a version, data or code difference, and is still not noise.

---

## 11. AMENDMENT 2 — 2026-09-04, revision 43, written AFTER the author chose option (2) in section 7 and BEFORE the C01 script was written or run

The author selected **option 2 — re-measure C01 paired inside one fit on the published base**. This
amendment fixes that design before any C01 number exists. It changes no criterion elsewhere and makes no
claim about what the result will be.

**11.1 One fact measured on the code first, and it narrows the design.** Reading the archived canonical
runner (`run_corrected.py`) shows **C01 never touched split-CP or CQR**: both take the order statistic
directly (`np.sort(resid)[cq_idx(n,a)-1]`). The defect is confined to the adaptive stream, which converts
the rank to a fraction and calls `np.quantile(pool, lv, method="higher")` with `lv = min(1, k/m)` —
returning the **(k+1)-th** order statistic for k < m. So **C01 is an ACI/ACQR-only effect**, which is
consistent with B7's long-standing use of split-CP as the C01 negative control, and it means split-CP and
CQR are a control this design gets for free rather than one it must construct.

**11.2 Population.** Belgrade, `belgrade_features_v2.parquet`, `use_15`, `y_t+15min`, level 0.90, the
**published base**: train-window sd >= 5 minus `core.low_information_facilities` on the test split —
**21 facilities**. It is explicitly **not** the archived "8 Belgrade facilities", which cannot be
identified (section 0g). The population is stated here, before the run, and is not changed afterwards.

**11.3 The two arms differ in exactly one line.** The legacy arm is produced by scoping the archived
quantile rule over `core.conformal_quantile` **for the duration of the adaptive call only**, so the two
arms share the stream, the release queue, the projection, the score function and the metrics — a
reimplemented legacy stream could drift from the real one and would make the delta unattributable. The
scope excludes `split_conformal_interval` and `cqr_interval`, which the archived code computed correctly.

**11.4 The fit is shared and gamma is held.** One RandomForest delta model and one HistGBR quantile pair
per facility, fitted once and used by both arms (D-017, A13). **Gamma is held at the corrected arm's
calibration-selected value in both arms**, so the delta is attributable to the quantile rule alone (B6);
the gamma the legacy rule *would* have selected is recorded as a diagnostic column and **used for
nothing**.

**11.5 The gate, before any legacy number is read (B17, the EXP-027 pattern).** The corrected arm must
reproduce `05_results/tables/2026-09-02-core-belgrade-gcal-per-facility.csv` — PICP, MPIW and Winkler for
ACI and ACQR at t+15 and level 0.90, on all 21 facilities — to **4 dp**, zero failures. **Built-in
negative control:** split-CP and CQR must be **bit-identical** across the two arms, since neither uses the
patched path. If they are not, the scope leaked and nothing is reported.

**11.6 Outcome branches, all four decided now.**
- **U — the legacy rule over-covers with wider intervals** (the archived direction: higher PICP, higher
  MPIW). Report the measured delta as the C01 row's effect **on the published base**, labelled a
  re-measurement, never as a reproduction.
- **V — the direction differs from the archived prose.** Report as found and say plainly that the archived
  figure pointed the other way. Do **not** reconcile them: they are different bases and different
  populations, and B12 is the standing warning against carrying a predicted direction into a claim.
- **W — the effect is below the reporting precision.** Then T6's C01 row is a null with its bound stated,
  which is still a finding and is still printable.
- **X — the negative control fails.** Stop, diagnose the scope, report nothing.

**11.7 Forbidden, in addition to section 8.** Quoting `0.8988 -> 0.8858`, `MPIW -15.4%` or
`Winkler -7.8%` beside the new figures, or anywhere at all (B17); describing this run as reproducing the
archived attribution; changing the population, horizon or level after seeing any output; and letting the
legacy rule reach split-CP, CQR or any other reported number.

---

## 12. AMENDMENT 3 — 2026-09-04, revision 43, written AFTER the C01 arms returned and BEFORE the fixed-gamma arm was run

**What was known when this was written.** The prespecified C01 run is complete on all 21 facilities. The
negative control is exact (split-CP and CQR differ by **0.0** on PICP, MPIW and Winkler across arms, so the
scope did not leak), the corrected arm passed the 4-dp reproduction gate on every facility, and the
outcome is **branch W**: the legacy rule over-covers with wider intervals at **21 of 21** facilities — the
same *direction* as the archived prose — but by **mean ΔPICP +0.0004** and **MPIW +0.34% (ACI) /
+0.42% (ACQR)**, against the archived prose's **ΔPICP −0.0129 and MPIW −15.4%**. Direction agrees;
magnitude differs by roughly a factor of 40.

**What this amendment adds, and why it is not a rescue.** The claim is not being changed — branch W is
reported as measured, whatever this arm returns. The question is narrower and it is one a referee will ask
of T6 directly: **the published base runs calibration-selected gamma, the archived attribution ran the
retired fixed gamma = 0.05.** A larger step size drives the adaptive state through wider alpha excursions,
and the cost of taking the (k+1)-th order statistic instead of the k-th is not constant across that range.
So the magnitude gap has an obvious candidate explanation inside our own configuration space, and it is
one line to test. This is B24's discipline — apply the treatment at a band of the relevant magnitude, not
at one point — with the gamma regime as the band.

**The arm.** Identical in every other respect: same population, same shared fits, same scoped rule, same
gate. `--gamma-mode fixed` holds gamma at **0.05** in both arms instead of at the calibration-selected
value, writing to `05_results/tables/2026-09-04-c01-attribution-gfixed.csv`. **The calibration-selected
arm remains the primary and its numbers are the ones T6 quotes**; the fixed-gamma arm is a mechanism
check and is labelled as one.

**Branches, fixed before it runs.**
- **W1 — the fixed-gamma arm shows a materially larger C01 effect.** Then the magnitude gap is explained
  by the step size, T6's C01 row says so in one clause, and the archived 15.4% is still not quoted.
- **W2 — the fixed-gamma arm is also small.** Then the step size does **not** explain it, and the honest
  statement is that the archived attribution's magnitude is not reproducible in any configuration we can
  still run, that its population of 8 facilities is unrecorded, and that **EXP-017's prose claim "the
  entire shift is the C01 fix" is not supported by anything now measurable.** That is a claim about a
  retired number and moves no published figure, but it is recorded rather than left implied.
- **W3 — the gate fails on the fixed-gamma arm.** Stop; report nothing from it; the primary arm stands.

**Forbidden here too:** quoting the archived triple; presenting either arm as reproducing it; and letting
the fixed-gamma arm, which is a mechanism check, become the number T6 prints.
