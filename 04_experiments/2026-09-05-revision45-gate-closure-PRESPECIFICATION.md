# PRESPECIFICATION — revision 45, closing the clean-room gate

**Written 2026-09-05, revision 45, AFTER section 0 was measured on the inputs and BEFORE any file was
changed.** Tenth prespecification. Authority: the author's decisions of 2026-09-05 on **D-024 (option 1)**,
on the treatment of the measurably-unstable e3 cell (**branch S**), and on **defect 7** (remove the
append). Constrained by D-018 (the exclusion), D05 (`sigma > 5` primary), B17 (assert the base), C13 (the
manifest is re-cut LAST), A6 (retire by moving within the mount, never delete), and rule 11 (the
reproduction tolerance does not move).

**What this session is NOT allowed to do, fixed here before any output exists:** relax or scope any
tolerance; backfill a ninth facility so the delay population stays at 8; change `--facilities` defaults;
prune facility 8 from any per-facility audit trail; or regenerate a logged number without recording the
before and after with sha256 on both sides.

---

## 0. FACTS MEASURED ON THE INPUTS FIRST. All four checks pass and one of them retires a clause.

Measured against `05_results/reference/2026-09-02-delay-sensitivity-belgrade.csv` (the logged artifact)
and the v2 processed features, before any edit.

**(a) The exclusion resolves to the same set in every scored window, so D-018 is unambiguous here.**

| city | logged population (`sd >= 5`, first N) | `low_information_facilities` per scored test window |
|---|---|---|
| belgrade | N=8 -> `[2,3,4,5,6,7,8,9]` | `use_5` -> `[8]`; `use_15` -> `[8]`; `use_30` -> `[8]` |
| birmingham | N=10 -> `[1,2,3,4,5,6,7,9,10,11]` | `use_30` -> `[]`; `use_60` -> `[]`; `use_90` -> `[]` |

**Birmingham excludes nothing, so no Birmingham number may change.** That is a gate below, not a hope.

**(b) B17 — the "before" column equals the logged number to 4 dp. All six of D-024's figures reproduce.**

| quantity | recomputed from the logged table | D-024 states |
|---|---|---|
| ACI PICP, h=6, gamma 0.05, 8 facilities | **0.8718** | 0.8718 |
| ACI PICP, h=6, gamma 0.005, 8 facilities | **0.9006** | 0.9006 |
| cost of gamma = 0.05, 8 facilities | **2.88** pts | 2.88 |
| ACI PICP, h=6, gamma 0.05, 7 facilities | **0.8690** | 0.8690 |
| ACI PICP, h=6, gamma 0.005, 7 facilities | **0.8962** | 0.8962 |
| cost of gamma = 0.05, 7 facilities | **2.72** pts | 2.72 |

**(c) The clause that dies, measured at every horizon rather than at the one D-024 quotes.**

| h | gamma = 0.005, logged base (8) | gamma = 0.005, excluded base (7) |
|---|---|---|
| 1 | 0.8979 | **0.8944** |
| 3 | 0.8990 | **0.8949** |
| 6 | 0.9006 | **0.8962** |

So *"gamma = 0.005 restores 0.90 at every horizon"* becomes *"recovers most of the shortfall, to
0.894-0.896"*. **It is retired, not quietly reworded**, and the sentence is rewritten in R-Phase 7.

**(d) The change is a row deletion, not a recomputation — which makes the gate unusually strong.** The
delay table is per-facility and every row is computed inside its own facility's loop iteration, so
excluding facility 8 removes exactly **21 rows** (3 horizons x 7 method-gamma combinations) and must
leave the other **147 bit-identical**. 168 -> 147.

---

## 1. WHAT IS CHANGED, AND THE GATE ON EACH

### Change 1 — D-024 option 1: apply D-018 to `2026-09-02-delay-sensitivity.py`
Add `core.low_information_facilities` on each scored test window, exactly as
`2026-09-04-rphase5-d05-sweep.py` and `2026-09-04-c01-attribution.py` already do (B9: one definition of
the rule, in `core.py`). Regenerate both cities.

**Gate — all four must hold or the change is reverted:**
1. Belgrade: **147 rows**, facilities `[2,3,4,5,6,7,9]`, facility 8 absent.
2. Belgrade: every one of the 147 retained rows **bit-identical** to the logged table on PICP, MPIW and
   Winkler. Anything else means a second unstable unit and I stop and report (rule 12).
3. Belgrade aggregates equal section 0(b)'s excluded column to 4 dp: **0.8690 / 0.8962 / 2.72**.
4. Birmingham: **210 rows bit-identical** to the logged table, and its facility set unchanged. This is
   the negative control (B7/B11): the exclusion is empty there, so a Birmingham change would prove the
   edit did something other than exclude.

### Change 2 — branch S for the measurably-unstable cell
`2026-09-03-e3-belgrade-per-facility.csv`, facility 8, `AgACI-style`, MPIW and Winkler. Register it in a
**generated** CSV — `00_admin/2026-09-05-unstable-cells.csv` — carrying, per cell, both observed values,
the observation count, the mechanism and the reason it changes no reported number; and have `verify.py`
report a registered cell as **known-unstable** rather than as a failure, on the same footing as the 58
archived artifacts.

**This is not a tolerance relaxation and the difference is stated so it can be checked:** the tolerance
is unchanged for every other cell and for every other column of this cell (PICP is exact and stays
gated); the registry names specific cells measured to be nondeterministic, with the measurement on disk;
and the guards below make it fail closed.

**Gate — all four must hold:**
1. A registered cell whose new value is **neither** of the two recorded values is a **failure**, not a
   pass. The registry pins values, it does not exempt a cell.
2. A registered cell's **PICP** stays under the exact-match tolerance (it is identical across both
   branches — measured, four observations).
3. An unregistered cell that differs is still a failure.
4. The registry is **generated from measured runs**, never typed, and records how many observations of
   each value exist.

### Change 3 — defect 7: the spatial step mutates a manifest-listed tracker
Remove the `open(EXPERIMENTS_LOG.md, "a")` block from `03_code/src/spatial/spatial_analysis.py` and
`spatial_mantel.py`. Both already write their CSVs; the append is a side effect that edits a living
tracker with a `datetime.now()` stamp, so the file's hash differs per run and per replicator.

**Gate:** after the change, a full clean-room run leaves `04_experiments/EXPERIMENTS_LOG.md`
byte-identical to the shipped copy, and the two spatial CSVs are unchanged.

---

## 2. OUTCOME BRANCHES, FIXED NOW

- **Branch A — all three gates pass.** Adopt; record the retired clause; refresh the affected references
  with sha256 on both sides in a dated CSV (C13); rebuild the package; re-cut the manifest LAST.
- **Branch B — a retained delay row differs.** A second unstable unit exists. **STOP**, do not regenerate
  anything else, report which rows and at what magnitude, and put it to the author.
- **Branch C — Birmingham moves.** The edit did something other than apply the exclusion. **Revert** and
  report.
- **Branch D — the regenerated aggregates disagree with section 0(b).** D-024's measured table was
  wrong. **STOP** and report before any tracker is updated.
- **Branch E — the clean room still fails on something outside the registry.** Report at full size; the
  tolerance does not move.

## 3. DELIVERABLES

Regenerated `2026-09-02-delay-sensitivity-{belgrade,birmingham}.csv`; the generated unstable-cell
registry; edited `verify.py`, both spatial scripts and the delay script; a dated reference-refresh CSV
with sha256 on both sides; an OUTCOME block on **D-024**; a new **EXP-036**; the new lessons; the
rebuilt package and a re-cut manifest, both **at the end of the session, after the logs are written**
(C13); and a confirming clean-room run.
