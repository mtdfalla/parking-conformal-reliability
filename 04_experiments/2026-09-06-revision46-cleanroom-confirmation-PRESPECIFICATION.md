# PRESPECIFICATION — revision 46, the confirmation clean-room run from the NEWLY REBUILT package

**Written 2026-09-06, revision 46, AFTER section 0 was measured on the shipped package and BEFORE the
package was unzipped or any step was run.** Eleventh prespecification. Authority: revision-45 record
section 11 item 1, and PROJECT_STATUS "NEXT ACTIONS" item 0(i). Constrained by **rule 11** (a reproduction
tolerance does not move after a clean-room run), **C16** (verify in the tree you actually ran, not only in
a fresh unzip), **C14** (an archived input must never be copied into the run's output directory),
**A9** (the gate is the exit code and a zero failure count, never a check count), **A10/A16** (an
infrastructure failure is classified before it is debugged) and **C13** (the manifest is re-cut LAST).

**Why this run exists.** Revision 45's confirmation run (EXP-036) was executed against the package as it
stood *before* three code changes landed: the D-024 edit to `2026-09-02-delay-sensitivity.py`, the
unstable-cell registry in `verify.py`, and the two retired spatial scripts replaced by dated files. The
package that now ships has therefore **never itself been run end to end**. This run closes that gap and
nothing else.

**What this session is NOT allowed to do, fixed here before any output exists:**

1. Relax, scope or special-case any reproduction tolerance. PICP is exact; widths 1e-12; CI bounds and
   p-values 1e-9.
2. Add a cell to `00_admin/2026-09-05-unstable-cells.csv`. The registry pins **values, not cells**, and
   revision 45 earned each of its two entries with nine measured observations and four negative controls.
   A newly unstable cell is a **finding to report**, not a row to append.
3. Edit any tracker, reference table or manifest so that a hash matches. If the run mutates a
   manifest-listed document, that is defect 7 recurring and it is reported, not absorbed.
4. Change a population, a facility set, a `--facilities` value or a seed to make a step agree.
5. Pre-seed `05_results/tables/` from `05_results/reference/` (C14) — a run must not "reproduce" a file
   it was handed.
6. Describe the result as a container-verified clean room. No container runtime exists on this machine;
   the Dockerfile remains **UNTESTED** and building it once is an author action.

---

## 0. FACTS MEASURED ON THE SHIPPED PACKAGE FIRST. Six checks, all measured before the unzip.

Measured on `06_manuscript/CTR/replication/2026-09-05-parking-conformal-reliability.zip` and a throwaway
probe extraction outside the project tree.

**(a) Package identity, pinned here so the run cannot be attributed to a different artifact.**

| property | measured |
|---|---|
| sha256 | `6d7c413bbfe08ab0303544953f08f228517443b9dd2fd005e82f3c95a5ad3daa` |
| size | 13,117,143 bytes |
| files | **269** |
| manifest entries (`00_admin/2026-09-04-shipped-outputs/MANIFEST-outputs.csv`) | **243** |
| build stamp (`BUILD-INFO.txt`) | 2026-09-05T20:08:13Z |

**(b) All three post-EXP-036 code changes are present, and the superseded files are absent.** This is the
whole reason for the run, so it is verified on the inputs rather than assumed:

| change | evidence in the package |
|---|---|
| D-024 applied to the delay script | `2026-09-02-delay-sensitivity.py:56` calls `core.low_information_facilities` |
| the unstable-cell registry | `verify.py` hash-locks the registry **and its generator**; `unstable_rules()` at line 129 |
| defect 7 fixed by retirement | only `2026-09-05-spatial-{analysis,mantel}.py` ship; `spatial_analysis.py` / `spatial_mantel.py` and every `_retired/` path are **absent** from the zip |

Neither dated spatial script contains an `open(...,"a")` on a tracker; the only occurrences of
`EXPERIMENTS_LOG` in either file are header comments recording the removal.

**(c) The defect-7 regression baseline, and it is exact.** The package's
`04_experiments/EXPERIMENTS_LOG.md` is **byte-identical to the repository copy**:
`4fb37242c8003ae5d9dfdd9e011dc4f91382450d0382d4cf0e0073bd4523f0b5`. So the gate on defect 7 is a hash
equality with a value fixed **before** the run, not a judgement made after it.

**(d) Expected output shapes, read from the shipped references before anything runs.**

| reference | data rows |
|---|---|
| `2026-09-02-delay-sensitivity-belgrade.csv` | **147** (D-024 applied: 7 facilities x 3 horizons x 7 method-gamma) |
| `2026-09-02-delay-sensitivity-birmingham.csv` | **210** (10 facilities; the exclusion is empty there) |
| `2026-09-03-e3-belgrade-per-facility.csv` | **164** |
| `2026-09-03-e3-birmingham-per-facility.csv` | **196** |

`05_results/reference/` holds **121** tables; `00_admin/2026-09-05-archived-artifacts.csv` lists **58**
with a per-file reason, so a complete run regenerates **63**. `05_results/tables/` ships empty
(`.gitkeep` only), which is the C14 condition this package is built for.

**(e) The registry contains exactly two cells, and both are the same unit.** Both rows of
`00_admin/2026-09-05-unstable-cells.csv` are `2026-09-03-e3-belgrade-per-facility.csv`,
`arm=A3_v2_daychunk; facility_id=8; method=AgACI-style` — one for **MPIW**
(30.9050340968556 | 30.9051028176217) and one for **Winkler**
(43.5352127746001 | 43.5352814953661), each with **9** observations split **6|3** and
`picp_identical_across_observations = True`. **PICP is not registered and stays gated as exact.**

**(f) Disk, measured because A10 says ENOSPC does not present as a timeout.** `/sessions` (which holds
`$HOME`, and therefore `~/cleanroom`) has **719 MB free at 93% used**; `/` has 2.6 GB free. The clean room
goes in `$HOME` rather than `/tmp` deliberately: `/tmp` is the roomier volume but A11/A16 record it
vanishing between *and within* sessions, and losing a ~60-call run mid-way costs more than the headroom
is worth. **If a step fails on ENOSPC this is branch E-disk, not a numerical finding.**

---

## 1. WHAT IS RUN

`~/cleanroom/parking-conformal-reliability`, a fresh unzip of the package identified in 0(a). Every step
of `run_all.sh` from an empty `05_results/tables/`, advancing with `--from <step>` as steps complete:

`env core e3 tod trust baselearner orthogonal folds rolling delay x08 inference vignette rphase5 c01
relalloc display spatial figures verify`

**Expected cost, stated rather than implied: ~60 `device_bash` calls** — about 4 for `core`, ~30 for `e3`,
~15 for everything after it (EXP-036's measured rate). `timeout 172 bash run_all.sh` per call.

**Nothing in the repository is written by this run.** The only repository writes this session are this
file and, at the end, the trackers.

## 2. THE GATE

Per A9 the gate is **the exit code and a zero failure count**, not a check count. Revision 45 measured
~306 checks against 243 manifest entries on a tree carrying a complete output set; that figure is
**informational** and a different number is not itself a failure.

1. `run_all.sh` reaches `ALL STEPS COMPLETED` with exit 0.
2. `python 03_code/verify.py` inside **the tree that was actually run** exits 0 with **zero failures**,
   printing the *"58 archived reference table(s) not regenerated"* note and, if a registered branch was
   drawn, the *"known-unstable cell(s) … matched a recorded value"* note. Both notes are **correct output**.
3. `python 03_code/verify.py` inside **a fresh unzip carrying only the run's `05_results` outputs** also
   exits 0 with zero failures. **Both passes are required and they test different things** (C16): the
   first catches self-inflicted drift in code, docs and trackers; the second catches missing inputs
   (C14). Neither alone is the clean room.
4. `04_experiments/EXPERIMENTS_LOG.md` in the run tree hashes to **`4fb37242…f0b5`**, unchanged from 0(c).
5. `2026-09-02-delay-sensitivity-belgrade.csv` has **147** rows and facility 8 is absent;
   `-birmingham.csv` has **210**.
6. Tolerances as standing: **PICP exact; widths 1e-12 relative; CI bounds and p-values 1e-9.**

## 3. OUTCOME BRANCHES, FIXED NOW

- **Branch A — every gate in section 2 holds.** The shipped package is confirmed end to end for the first
  time. Record as a new EXPERIMENTS_LOG entry; update the four trackers; R-Phase 7 is next and unblocked.
- **Branch B — a published number differs, outside the registry.** **STOP.** Report the file, the
  identity columns, both values and the relative magnitude at full size. Diagnose the mechanism before
  proposing anything (rule 1-2), open the unit's raw series if one unit dominates, and put it to the
  author. **The tolerance does not move and no population changes.**
- **Branch C — a manifest-listed document is mutated by the run** (gate 4 fails). Defect 7's fix is
  incomplete or a second writer exists. **STOP**, identify the writing step from `07_logs/`, and report.
  Do not re-hash the manifest.
- **Branch D — a registered cell takes a THIRD value.** The registry is designed to fail closed here and
  its negative control C2 asserts exactly this. Report it as a **failure**, record the new value and its
  observation count, and **do not append it** — extending the registry needs the same four-control proof
  revision 45 gave it, and that is a separate decision.
- **Branch E — an infrastructure failure.** Classify before debugging: **E-deps** (`ModuleNotFoundError`
  on a package that worked earlier) is A16 — re-run `restore-env.sh`, then `verify-state.sh deps`, do not
  debug the package; **E-disk** is A10 — ENOSPC, not a timeout, and re-running cannot fix it;
  **E-input** (`FileNotFoundError`) is the C14 class and **is a package defect and a real finding**.
- **Branch F — the two verify passes disagree.** That disagreement is itself the finding (C16) and is
  reported as such, with the differing file named, rather than resolved by preferring the passing tree.

## 4. WHAT THE OUTCOME WILL RAISE, RECORDED NOW SO IT IS NOT DISCOVERED LATER

`04_experiments/EXPERIMENTS_LOG.md` is a **shipped** file. Writing this run up therefore changes a file in
the package, and rule 13 requires the manifest re-cut and package rebuild at the end of the session
(C13) — which produces, again, a package that has not been run end to end. **That recursion is real and
it is documentation-only**: if this run passes, the code and data files in the rebuilt package are
byte-identical to the ones just exercised and only tracker prose differs. **The recommendation to the
author, made in advance of the result so it cannot be shaped by it:** a package delta consisting solely
of tracker prose does not require another ~60-call run, provided the delta is verified by class — every
`code` and `data` entry byte-identical, only `doc` entries changed. If any code or data file changes, the
run is owed. This is a recommendation, not a decision taken here.

## 5. DELIVERABLES

The completed run in `~/cleanroom` with its `07_logs/`; both verify passes with their exit codes; a new
`EXPERIMENTS_LOG` entry (**EXP-038** — **EXP-037 stays reserved** for the record section 12.3 pilot,
which this session's scope excludes); updates to all four living trackers; a revision-46 record on the
revision-45 template with its paired next-session prompt; and, per C13, the manifest re-cut and package
rebuild **last, after the logs are written**.
