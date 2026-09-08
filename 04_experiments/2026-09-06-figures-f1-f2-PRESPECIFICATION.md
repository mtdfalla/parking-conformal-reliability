# PRESPECIFICATION — F1' and F2' regenerated on the X08-excluded base (D-020 items 7–8, D-027)

**Written 2026-09-06, revision 48, BEFORE the maker was run.** Thirteenth prespecification. Authority: D-020
(F1'/F2' "regenerated on the X08-excluded base"), D-027 (the eight display items), the revision-47 record §11
item 5 and the author's go of 2026-09-06 (revision 48). Rule 3 of the contradiction protocol (reproduce a maker
with only output paths changed) cannot be applied literally: the F1 maker is the **frozen** `finalize_corrected.py`
(reads the pre-audit `2026-06-25-corr-*` tables and appends a `datetime.now()` entry to `EXPERIMENTS_LOG.md`, the
defect-7 class), and F2 never had a script (REPLICATION.md: "plotting snippet in repo README"). So a **new
dated maker** `03_code/src/viz/2026-09-06-figures-f1-f2.py` reproduces the F1 design and gives F2 a script for
the first time. The frozen file is not touched.

## 1. Inputs — all already in the manifest; nothing is recomputed

| figure | source tables | filter |
|---|---|---|
| F1' | `2026-09-02-core-{belgrade,birmingham}-gcal-per-facility.csv` | `dynamic`, level 0.90, X08 exclusion from `core.low_information_facilities` on each horizon's test rows (the EXP-037 population, 21 / 28 facilities), four primary methods |
| F2' | `2026-09-04-x08-core-headline-excl.csv` (4 primary methods: `std`, `Winkler`), `2026-09-04-x08-e3-summary-excl.csv` (EnbPI, AgACI-style, NGBoost, NGBoost-conformal: `sd_PICP`, `mean_Winkler`, `worst_facility_PICP`), `2026-09-04-T3prime-two-level-inference.csv` (`worst_facility_PICP` for the primary four) | headline cells (Belgrade t+15, Birmingham t+60), the eight rows of Table 2 |

## 2. Design, fixed here

**F1' — `05_results/figures/2026-09-06-f1-per-facility-coverage.png` (+ `.pdf`).** One figure, **2 rows (city) × 3
columns (horizon)**, shared y-axis 0.55–1.02, a dotted line at 0.90, a shaded ±0.02 band. Per panel: boxplots
for split-CP, CQR, ACI, ACQR (in that order, the T2 order with the adaptive pair last), individual facilities as
jittered points, the same colours as the pre-audit figure (split-CP `#C00000`, ACI `#1F4E79`, CQR `#2E9E5B`) plus
ACQR `#7030A0`. Panel title: city, horizon, n facilities. **Change from the pre-audit F1, stated:** (i) ACQR
added — the caption already refers to "the adaptive family"; (ii) Birmingham in the same figure — the pre-audit
caption promised a "Birmingham analogue in the ESM" that does not exist; (iii) the retired
"fraction of facilities whose CI contains 0.90" is not drawn or written anywhere.

**F2' — `05_results/figures/2026-09-06-f2-reliability-efficiency.png` (+ `.pdf`).** Two panels (Belgrade t+15,
Birmingham t+60). **x = mean Winkler score (lower is better); y = across-facility sd of coverage (lower is
better)**; each of the eight methods one marker, labelled, with its worst facility's coverage printed beside it.
The origin corner (low, low) is the desirable one and the panel says so. A method whose Winkler exceeds
**1.5 × the median of the other seven** is placed at the right axis limit with an arrow and its true values
printed (prediction: NGBoost on Birmingham, Winkler 408.7, and nothing else). The retired "share statistically
at target" axis is not used, and no ratio is drawn.

## 3. Predictions

| # | prediction | source |
|---|---|---|
| P1 | F1' Belgrade t+15 panel: split-CP min 0.787 (facility 9), ACQR min 0.879, ACI min 0.869, CQR min 0.827; Birmingham t+60: split-CP min 0.787, CQR 0.779, ACI 0.866, ACQR 0.854 | T3' / EXP-037 CSV |
| P2 | F2' points equal Table 2's (sd, Winkler) columns to the printed precision on all sixteen rows | `typeset.json` T2 |
| P3 | Exactly one off-scale marker (NGBoost, Birmingham) | e3 summary |
| P4 | The maker is deterministic: two runs give byte-identical PNGs (matplotlib metadata pinned: `metadata={"Software": None}`, fixed `SOURCE_DATE_EPOCH`-independent PDF creation date disabled) — if the PDF cannot be made byte-stable it is listed `not_gated` like every figure, and the PNG is the gate | — |

## 4. What changes downstream

The two `\includegraphics` lines and the two captions in `2026-09-06-apply-rphase7.py`; the "[Regenerated on the
exclusion base at submission.]" placeholders are removed; the ESM's "PRE-AUDIT RENDER" flags stay on the ESM
figures, which this prespecification does not cover. `run_all.sh` gains the step; `verify.py`'s manifest is re-cut
(figures are `not_gated` by hash — C13, at the end of the session, after the trackers).
