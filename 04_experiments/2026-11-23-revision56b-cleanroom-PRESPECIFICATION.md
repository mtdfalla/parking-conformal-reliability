# PRESPECIFICATION — EXP-043: promotion of the v3 batch and the clean-room run that regenerates every table

**Written 2026-11-23, revision 56b, BEFORE the promotion, before any successor file was written, and before any population-level number from the v3 runner was read.** Eighteenth prespecification.
Authority: D-036, D-038, the "Fixed decisions" table of `00_admin/2026-11-22-audit-remediation-implementation-plan.md`, EXP-042 (sections 8 to 11).
Measured before writing (scratch builds outside the project, nothing promoted): the staged v3 builder is byte-deterministic (two builds, parquet sha256 `3adad011379fa07a...`, report `3b53920c58c2b931...`, representativeness table `b5130afe5cb78f01...` on both). Every count below names its baseline and its row filter (C20, C41).

## 1. What this experiment is

Three gated stages, in this order. No stage starts until the previous one's gates are green.

| Stage | What | Where | Ends when |
|---|---|---|---|
| **P** promotion | the staged batch and every successor go into place; retirements by moving (A19); manifest re-cut | repository, after a rehearsal on a scratch copy | section 5 gates green in the repository |
| **R** run | every `run_all.sh` step from an empty `05_results/tables/` | `~/cleanroom`, a fresh unzip of the package built after P | `run_all.sh` exit 0, section 6 gates green |
| **F** refresh | reference refresh (C13), archived list regenerated, manifest re-cut, package rebuilt, `verify.py` in the package that ran and in a fresh unzip (C16) | repository, then the clean room | package sha recorded |

## 2. Promotion: every move and every successor, fixed now

**Rule for a changed file (D-039 item 1, decided here):** a file whose NAME is an interface (imported by name, called by `run_all.sh` by name, listed by name in `verify.py`) is retired by moving its bytes to `_retired/` with a `.pre-v3` name, and its successor takes the same path. A file whose name is not an interface keeps the dated-successor rule. This is the pattern the plan already fixed for `core.py`. It keeps `run_all.sh` lines and `load_script` imports unchanged, so no consumer cascade is created to re-point a consumer. Every successor of an existing file is produced by a generator, `03_code/2026-11-23-make-promotion-successors.py`, as exact old-string to new-string replacements with an expected count per replacement. A count that does not match stops the generator. No successor is typed by hand.

**Moves (byte-identical; sha256 recorded on both sides in `00_admin/2026-11-23-promotion-register.csv`):**

| From | To |
|---|---|
| `03_code/src/conformal/core.py` | `03_code/src/conformal/_retired/2026-09-02-core-pre-v3.py` (the name the V-suite looks for) |
| `03_code/src/conformal/2026-09-02-run-core-methods.py` | `03_code/src/conformal/_retired/` (same name) |
| `03_code/src/conformal/2026-09-04-display-items.py` | `03_code/src/conformal/_retired/` (same name) |
| `03_code/src/features/2026-09-02-build_features_birmingham_v2.py` | `03_code/_retired/features/` (same name). The causality controls point here. Not `src/features/_retired/`: the builder finds the data as `parents[3]` of its own path, so it must keep its depth (found in the rehearsal, before promotion) |
| `03_code/tests/2026-09-02-test_split_integrity.py` | `03_code/tests/_superseded/` (same name) |
| `01_data/processed/birmingham_features_v2.parquet`, `..._v2_report.json` | `01_data/processed/archived-v2/` (D-039 item 2) |
| each re-pointed consumer below | its own folder's `_retired/` as `<name>.pre-v3.py` (or `.sh`) |
| `00_admin/2026-09-04-shipped-outputs/MANIFEST-outputs.csv` | `.../_superseded/2026-11-23-MANIFEST-outputs-pre-promotion.csv` (`verify.py --build` refuses to overwrite) |

**D-039 item 2, decided here, departing from the revision 56 brief, with the reason.** The brief says the v2 parquet leaves `01_data/processed/`. S1 needs it in the shipped package and in the clean room, and `build-package.py` ships only `01_data/processed/`, while `_retired` is ignored by `verify.py` and excluded by the package. Outside `processed/`, S1 could not be reproduced by a replicator or by stage R. A non-ignored subfolder `archived-v2/` keeps it hash-locked as an input, shipped, and out of the top-level namespace that every `*_v2.parquet` pattern reads. The brief's concern (a consumer reading v2 as current) is met because no live consumer will name that path except S1's `--s1-keys`.

**Staged batch placed as is** (shas as in the revision 56 brief): `core.py`, `2026-11-22-run-core-methods.py`, `2026-11-22-block-bootstrap-belgrade.py`, `2026-11-22-build_features_birmingham_v3.py`, the three `2026-11-22-test*` files. `2026-11-22-display-items.py` is placed **with one re-point** (it still names the 2026-09-02 core outputs), produced by the generator.

**Re-pointed consumers (lists A and B of the consumer enumeration):** the Birmingham table becomes `birmingham_features_v3.parquet`, Belgrade stays `belgrade_features_v2.parquet`, and `2026-09-02-core-{city}[-gcal]-*` becomes `2026-11-22-core-{city}-v3[-gcal]-*`.

| File | Change |
|---|---|
| `2026-09-03-e3-baselines.py` | arm A3 reads v3 for Birmingham. Arm names unchanged. A12 still reads v1 (the attribution arm) |
| `2026-09-02-delay-sensitivity.py`, `2026-09-04-orthogonal-folds-birmingham.py`, `2026-09-04-rphase5-d05-sweep.py`, `2026-09-06-exp037-pooled-vs-worst.py`, `viz/2026-09-06-figures-f1-f2.py` | feature table and core output names |
| `2026-09-04-x08-reaggregate.py` | feature table; core output name; the two writerless summaries are compared against the new writer (below) |
| `2026-09-04-phase4-inference.py` | core output name; its gate compares against the new writer's headline table instead of `2026-09-02-corrected-headline-gcal.csv` |
| `2026-09-04-c01-attribution.py` | gate reference re-pointed to the new core output |
| `tests/2026-09-04-x08-control-check.py` | the two writerless pairs re-pointed to the new writer |
| `tests/2026-09-03-verify-state.sh` | artifact list, the successor split test, phases `causality`, `pipeline-single`, `pipeline-cuts` added |
| `run_all.sh` | section 4 |

**Not re-pointed, recorded:** `2026-09-05-ngboost-reseed-before-after.py` (a historical v2 before-and-after; re-pointing would make its "before" false), `2026-09-03-stuck-sensor-diagnostic.py`, `2026-09-04-daily-coverage-diagnostic.py`, the two determinism probes (Belgrade only or historical, not `run_all` steps). `2026-09-04-build-package.py` and `2026-11-22-build-public-repo.py` are changed in stage F and revision 58, where they run.

**New files:**
1. `tests/2026-11-23-test_split_integrity_v3.py`, the successor suite. Same 50 checks. Birmingham reads v3. T9 for Birmingham becomes "v3 carries no interpolated anchor or target, and every usable row's target is observed" (one check, as before). T10's documented Birmingham set is counted on v3 before the file is written. The report JSON is written under the old name, so its reference copy is refreshed in stage F like any changed table.
2. `src/conformal/2026-11-23-headline-summaries.py`, the writer the two gates lacked. It writes `2026-11-23-core-headline-gcal.csv`, `2026-11-23-e3-summary.csv` and `2026-11-23-phase4-safe-mechanism.csv` (a third writerless input, read by display row G, found while enumerating). It is an implementation independent of `x08-reaggregate.py`. **Bridge control, run once in stage P on the v2-era tables:** pointed at the 2026-09-02 core outputs and the current e3 table, it must reproduce the three archived CSVs to 4 dp. If it does not, it is not the same aggregation and the gates do not move to it.
3. `src/conformal/2026-11-23-birmingham-sensitivities.py`. Writes `2026-11-23-birmingham-s1-s2.csv` (S1 beside the main result at t+60; S2 by `occ_carried` at every horizon, from the per-row file, no refit) and `2026-11-23-core-counters.csv` (`n_inverted`, `n_alpha_clipped`, `n_q_saturated` summed by city, horizon, level and method, with their denominators). It refuses to run if a counter column is missing or if the per-row coverage does not reproduce the per-facility PICP exactly.

**Superseding outputs:** stage R starts from an empty `05_results/tables/`, so no resumable step can reuse a v2 row there. In the repository, when stage R's tables come back in stage F, every table it regenerates replaces its predecessor only after the predecessor is moved to `05_results/tables/_superseded/2026-11-23-pre-v3/`.

## 3. Counts fixed before the run

| # | Quantity | Expected | Baseline and row filter |
|---|---|---|---|
| N1 | Birmingham v3 table | 21,438 rows, 28 facilities, 1,974 sessions | scratch build of the staged builder (above). v2 had 17,487 rows and 1,973 sessions |
| N2 | usable rows t+30 / t+60 / t+90 (train, calibration, test) | 15,961 (8,870 / 3,763 / 3,328); 14,770 (8,298 / 3,487 / 2,985); 13,082 (7,313 / 3,105 / 2,664) | same build, filter `use_H`, which requires an observed target |
| N3 | carried-anchor share of usable rows | 36.01 / 16.29 / 33.69 % | same build, `occ_carried` among `use_H` rows |
| N4 | S1 rows at t+60 | 12,797 (7,196 / 3,015 / 2,586), all 28 facilities evaluable | D-038 item 2: v3 rows usable at t+60 whose (facility, timestamp) were `use_60` in the v2 table |
| N5 | facilities evaluated | Belgrade 24 at every horizon (21 after X08 at t+15); Birmingham 28 at every horizon, none `SKIPPED-thin` | the shipped core tables; the thin guard is 100 / 50 / 50, smallest v3 t+60 counts read in EXP-042 |
| N6 | split-integrity / core / core-v3 checks | 50 / 48 / 0 failed | revision 56 gates |
| N7 | `run_all.sh` steps | 25: the old runner's 21 plus `features`, `summaries`, `bootstrap`, `sens` | `bash run_all.sh --list` on the successor, printed in stage P |
| N8 | new reference tables | 22, enumerated in section 4 | the list in section 4, nothing else |
| N9 | regenerated reference tables | 85 = 67 (EXP-041) − 4 (the 2026-09-02 core gcal per-facility and basemodel names, no longer written) + 22 (N8) + 0 | EXP-041's 67, the last clean-room count |
| N10 | archived reference tables | 62 = 58 (EXP-041) + 4 | the four old core names join the archived list. The archived list is regenerated from stage R's run (it is generated, never typed) |
| N11 | manifest entries and checks | entries = the stage P re-cut's count + 22; checks = entries + 85 | C20's rule: checks = entries + regenerated |

N9 to N11 are revised only by a dated note written before step `core` of stage R starts, if the rehearsal shows the runner writes a different file set. After `core` starts, a miss is a miss (A9).

## 4. The run: steps, budgets, outputs

Budgets from the SLOWEST recent run, EXP-041 (A23): Belgrade `e3` at 45 to 50 s per facility, core at about 16 s per facility in EXP-039 and taken here as 25 s. `BUDGET` 60 to 140, never 150. Every call wrapped in `timeout 172`. One phase per call.

| Step | What runs | New output tables | Calls predicted |
|---|---|---|---|
| env | `verify-state.sh deps` | | 1 |
| **features** | v3 builder into `01_data/processed/` and `05_results/tables/` | `2026-11-22-v3-representativeness.csv` (1) | 1 |
| core | the 2026-11-22 runner: belgrade and birmingham, calibrated gamma; belgrade and birmingham, fixed gamma (display row on gamma calibration had no live writer); birmingham S1 at t+60 (`--row-filter v2-rows --s1-keys 01_data/processed/archived-v2/birmingham_features_v2.parquet --horizon y_t+60min`) | `2026-11-22-core-{belgrade,birmingham}-v3[-gcal]-{per-facility,basemodel,rows-L90}.csv` (12) and `2026-11-22-core-birmingham-v3-S1-gcal-*` (3) | 8 to 12 |
| **summaries** | `2026-11-23-headline-summaries.py` | 3 | 1 |
| e3 | as before (both arms, both cities) | | 18 to 24 |
| tod, trust, baselearner, orthogonal, folds, rolling, delay, x08, inference, vignette, rphase5, c01, relalloc | as before | | 15 to 20 |
| display | `2026-11-22-display-items.py` | | 1 |
| **bootstrap** | `2026-11-22-block-bootstrap-belgrade.py` | 1 | 1 |
| **sens** | `2026-11-23-birmingham-sensitivities.py` | 2 | 1 |
| exp037, spatial, figures, verify | as before | | 4 |

`summaries` runs after `e3` in the runner (it reads the e3 per-facility table). Total 50 to 70 calls. Stage R may span two sessions (A23).

## 5. Gates of stage P, and what each must print

1. Rehearsal first, on `~/s56b/rehearsal` (a copy of `01_data`, `03_code`, `05_results`, `00_admin/2026-09-04-shipped-outputs`, `04_experiments`, `run_all.sh`): the promotion script with `--apply`, then gates 2 to 8 there. Only then on the repository.
2. Promotion register: every move byte-identical (sha equal on both sides), every successor's generator replacement counts as expected.
3. `verify-state.sh deps | artifacts | tests | freeze`: 50 and 48 checks, 0 failed; freeze **117 of 130** (none of the moved files is frozen, checked before writing this).
4. `test_conformal_core_v3.py` PASS; feature causality v3 0 of 1,612 and control on the retired v2 builder 478 of 1,612; pipeline causality v3 0 of 6,770 and 0 of 6 cuts at 21,438 rows.
5. Bridge control of the headline writer: three archived CSVs reproduced to 4 dp.
6. `bash run_all.sh --list` prints N7's 25 steps.
7. `verify.py --build` after the manifest is moved aside, then `verify.py`: **PASS, zero unlisted**. Entries printed and recorded as the stage P count of N11.
8. Zero-mismatch audit PASS (Q1, Q1a IDENTICAL, Q3 YES) and bundle sha `7bc380b8...` unchanged: no manuscript file moves in 56b.

## 6. Gates of stage R

1. `run_all.sh` exits 0 with every step printing its own success line.
2. `verify.py` in the run tree: phase A PASS; phase B differences only in tables N9 lists as regenerated with changed content; phase C zero unlisted. Phase B is read as a list of differences to classify, not as a pass or fail, because the references are still v2-era until stage F.
3. Counters present in every core row; `n_inverted`, `n_alpha_clipped`, `n_q_saturated` summed into `2026-11-23-core-counters.csv`.
4. N1 to N5 as predicted, read from the run's own tables.
5. Belgrade identity check: split-CP and CQR per-facility PICP in the new gcal table equal to the shipped `2026-09-02-core-belgrade-gcal-per-facility.csv` in every cell where `n_inverted` is 0 (nothing in v3 changes them: same features, seed, splits and conformal score). ACI and ACQR at t+5 identical too (V8: at horizon 1 the gamma selection is unchanged). ACI and ACQR at t+15 and t+30 may move through the gamma gap (item 2.7) and are reported as moved.
6. The c01 gate PASS (its corrected arm and the runner share `core.py`).
7. The block-bootstrap row, reported by EXP-042 section 8's rule, whichever way it falls.

## 7. Branch rules

- **A gate of stage P fails.** Fix it in the generator or the promotion script, rehearse again, never in the repository by hand. If it fails in the repository after passing in the rehearsal, move every promoted file back from the register (the register is the undo list) and report.
- **Stage R, Birmingham t+60 canonical result.** EXP-042's branch stands: it was decided on the decisive check. The canonical run differs from it by the gamma gap fix only. If on the canonical run any Branch N condition of EXP-042 section 7 holds (sd ratio below 1.25, ACI worst at or below split-CP worst, ACI mean outside [0.86, 0.94], fewer than 20 facilities), **STOP and report to the author** before stage F. If only a Branch R condition fails, proceed, and the revision 57 edit table carries it.
- **Stage R, gate 5 fails** (a Belgrade split-CP or CQR cell moves with 0 inverted bands). Stop and reproduce. That is a code change nobody intended.
- **A step fails in stage R.** Reproduce in the clean room. A defect in a successor is fixed by the generator, the package rebuilt, and the run restarted from that step. Never patched in the clean room.
- **Phase B difference in a table N9 does not list.** Stop and classify before stage F (C13).

## 8. Forbidden moves

1. Changing the Birmingham rule, the guard, the gamma grid, the seed, the level, S1's definition or the bootstrap rule after any stage R number is seen (EXP-042 section 9).
2. Typing a successor by hand, editing a manifest-listed file in place, or editing anything in the clean room.
3. Re-running a step with a different setting and keeping the better run.
4. Any manuscript edit in revision 56b.
5. Reading a population-level Birmingham verdict before stage R gate 4 has passed.
6. Treating a missed count as anything other than a miss (C20).

## 9. Count note, written 2026-11-23 after stage P and BEFORE step `core` of stage R (section 3 allows it)

Stage P is done in the repository: 21 moves byte-identical, 24 writes, register `00_admin/2026-11-23-promotion-register.csv`. Gates: split integrity 50, core 48, core v3 PASS, feature causality 0 of 1,612 (control 478), pipeline 0 of 6,770 and 0 of 6 cuts at 21,438 rows, freeze 117 of 130, `run_all.sh --list` 25 steps, bridge PASS, zero-mismatch PASS, bundle `7bc380b8...` unchanged. Manifest re-cut twice (after promotion, and after the package build regenerated two listed documents, C13): **266 entries**, `verify.py` PASS. Package `06_manuscript/CTR/replication/2026-11-23-parking-conformal-reliability.zip`, sha256 `3ef3b410febafd4b...`, verifies against its own manifest.

One of the 22 new tables (`2026-11-22-v3-representativeness.csv`) became a reference in stage P, so N11 is now exact: **entries after stage F = 266 + 21 = 287; checks = 287 + 85 = 372.** N9 (85 regenerated) and N10 (62 archived) are unchanged. The rehearsal ran no model, so the runner's file set is as section 4 lists it. No population-level number has been read.
