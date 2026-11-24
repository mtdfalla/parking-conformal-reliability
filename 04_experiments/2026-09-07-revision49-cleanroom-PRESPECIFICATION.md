# PRESPECIFICATION — the revision-49 clean-room run

**Written 2026-09-07 after the build, before the unzip.** Seventeenth prespecification. Authority: C13
(a table change owes a full clean-room run), C18 (the regenerated count is part of the gate), C16 (verify twice).

## 1. Artifact exercised

`06_manuscript/CTR/replication/2026-09-07-parking-conformal-reliability.zip`, sha256 `4e1dc24ff25a16be…`,
**291 files, 259 manifest entries**. Its predecessor (revision-48 build, `885581665211c17e…`, the artifact EXP-039
exercised) is retired byte-intact as `replication/_superseded/2026-09-07-parking-conformal-reliability-S48.zip`.

**What changed since EXP-039:** one new table (`2026-09-07-spatial-statistics-exclusion-base.csv`, D-030), two
new read-only makers (`src/spatial/2026-09-07-spatial-exclusion-base.py`, `src/viz/2026-09-07-figures-esm.py`),
four new figure files, two new `run_all.sh` steps, and the manuscript generators. Nothing that fits a model
changed.

## 2. Per-change gates

- `2026-09-07-spatial-statistics-exclusion-base.csv` regenerates **byte-identical** to the shipped reference.
- The ESM figure step prints `ALL DONE` and writes its four files; the two PNGs byte-identical to the
  repository's (**recorded, not a gate** — figures are `not_gated`).
- `04_experiments/EXPERIMENTS_LOG.md` sha256 **identical before and after** the run (defect 7 stays fixed).

## 3. Predictions

| # | prediction | baseline named (C20) |
|---|---|---|
| P1 | completes, **exit 0**, ~45–60 `device_bash` calls | EXP-039 took ~45 |
| P2 | zero failures; **regenerated 67**; archived 58; **checks 326** | 67 = EXP-039's 66 + the one new table; 326 = 259 manifest entries + 67 regenerated comparisons |
| P3 | the C16 second pass (fresh unzip carrying only the run's outputs) gives the same: PASS, 326 checks, zero failures | EXP-039 P3 |
| P4 | Belgrade delay 147 rows with facility 8 absent; Birmingham 210; e3 164 / 196 | EXP-039 P4, unchanged inputs |
| P5 | no unstable cell drawn, or one named by `00_admin/2026-09-05-unstable-cells.csv` | EXP-039 P5 |
| P6 | the spatial re-aggregation step needs no `--budget` (it fits nothing) and completes in one call | EXP-040: two repository runs, each well inside one call |

**If the machine is slow** (EXP-039's operational note): `BUDGET=75–110`, not the runner's default 150.

**If a count misses**, it is recorded as a prediction error and **not rescored** (A9, C20); the run's number
becomes the next prespecification's baseline (C18).
