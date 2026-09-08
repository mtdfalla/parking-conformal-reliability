# PRESPECIFICATION — ESM figures: two regenerated on the exclusion base, two cut

**Written 2026-09-07, revision 49, BEFORE the maker was written or run.** Sixteenth prespecification.
Authority: the revision-48 record §7 item 2 and §11 item 3; D-028's method for a figure whose maker is frozen;
the author's go of 2026-09-07. Companion to the fifteenth (`2026-09-07-spatial-exclusion-base-PRESPECIFICATION.md`).

## 1. Provenance of the four pre-audit renders, located this session

| ESM figure | file | maker | status of the maker |
|---|---|---|---|
| S1 calibration | `2026-06-25-corr-belgrade-calibration.png` | `03_code/src/conformal/finalize_corrected.py` | **FROZEN**; reads the pre-audit `2026-06-25-corr-*` tables and **appends a `datetime.now()` entry to `EXPERIMENTS_LOG.md`** (defect-7 class). Must never be run. |
| S2 example facility | `2026-06-25-corr-fac3-example.png` | `03_code/src/conformal/_retired/_fac3_corrected.py` | retired; **refits a RandomForest** and carries its **own inline re-implementation of delay-aware ACI**, not `core.py`'s |
| S3 spatial | `2026-06-21-spatial-corr-vs-distance.png` | `03_code/src/spatial/2026-09-05-spatial-analysis.py` | live, but running it in the repository rewrites frozen tables (**A21**) and it uses the wrong roster (**D-030**) |
| S4 trust/abstain | `2026-06-25-corr-trustabstain.png` | `03_code/src/conformal/run_cond_trust_corrected.py` | **FROZEN**; also appends to `EXPERIMENTS_LOG.md` |

The main text references ESM **Tables** S2–S7 only and **no ESM figure**; the ESM contains no internal
cross-reference to its own figures. Figures and tables are separate S-sequences. So cutting and renumbering
figures has **no cross-reference consequence anywhere** — checked by grep before this was written.

## 2. Decisions, with the reason for each

**S1 — REGENERATE, and strengthen.** Source `05_results/tables/2026-09-06-exp037-pooled-vs-worst.csv`
(Belgrade, `y_t+15min`, `n_facilities > 0`), which carries mean and worst facility coverage at four nominal
levels on the X08-excluded base. **Two panels**: (a) mean facility coverage vs nominal level — the pre-audit
design; (b) **worst facility coverage vs nominal level**, same methods, same ideal diagonal. Panel (b) is new
and is the reason the figure earns its place: the paper's thesis is that (a) tracks the diagonal while (b)
does not, and the pre-audit figure drew only (a). split-CP and ACI are lines over all four levels; CQR and
ACQR are markers at 0.90 and 0.95 only — a property of the source table, stated in the caption (EXP-037 P1).

**S2 (was S3) — REGENERATE on the corrected roster.** Source `2026-06-21-spatial-corr-distance.csv` filtered to
the 20 `exclusion_base` facilities named in `2026-09-07-spatial-statistics-exclusion-base.csv`, with the
annotations read from that same table. Scatter of pairwise residual correlation against inter-facility distance,
a binned mean over 8 equal-width distance bins, and a zero line. **Change from the pre-audit render, stated:** the
old figure's title carried only the naive Spearman, the statistic §5.5 explicitly says *does not survive* the
independence correction, so the figure could be read as showing a borderline trend. The new one prints **both**
the Mantel r (the test the claim rests on) and the naive ρ, and labels the naive one as not
independence-corrected.

**Old S2 (example facility) — CUT.** No CSV supports it: it is a per-timestamp trace, and reproducing it means a
new fit plus a new per-timestamp artifact, i.e. a table-and-code change, for a figure that **supports no number
anywhere in the manuscript**. Its retired maker also carries a second implementation of delay-aware ACI, which
B9 forbids shipping unverified. Route to reinstate, if a referee asks for an illustrative trace: a dated maker
built on `core.py` writing a per-timestamp CSV, with the clean-room run that implies.

**Old S4 (trust/abstain) — CUT as redundant.** Revision 48 added **ESM Table S6**, the same operating curve on the
exclusion base **with the matched random control** the figure lacks, from `2026-09-04-x08-trust-abstain-excl.csv`.
A figure of the same ten rows adds nothing; D-027 gave trust/abstain one ESM slot, and the table is the better
occupant.

**Net effect: the ESM goes from four pre-audit renders to two figures that both trace to a CSV.** After this,
no artifact in the submission carries pre-audit pixels.

## 3. Maker

`03_code/src/viz/2026-09-07-figures-esm.py`, a sibling of `2026-09-06-figures-f1-f2.py`: reads only
manifest-listed tables, recomputes nothing, writes no tracker, pins matplotlib metadata so the PNG is
byte-stable. Outputs `05_results/figures/2026-09-07-esm-s1-calibration.{png,pdf}` and
`2026-09-07-esm-s2-spatial-corr-distance.{png,pdf}`. The frozen makers are not touched.

## 4. Predictions

| # | prediction | baseline named (C20) |
|---|---|---|
| P1 | S1 panel (a) at 0.90: split-CP 0.9008, CQR 0.8995, ACI 0.8913, ACQR 0.8940 | `2026-09-06-exp037-pooled-vs-worst.csv`, Belgrade `y_t+15min` |
| P2 | S1 panel (b) at 0.90: split-CP 0.7872 (facility 9), CQR 0.8266, ACI 0.8690 (13), ACQR 0.8788 (13); and the worst-facility curve lies below the diagonal at **every** level for **every** method | same file; T3' agrees at 0.90 |
| P3 | S1 shows CQR and ACQR at exactly two of the four levels | same file: 8 populated Belgrade t+15 rows for split-CP/ACI (4 each) and 4 for CQR/ACQR (2 each) |
| P4 | S2 draws **190 points** and annotates Mantel r −0.128, p 0.139; naive ρ −0.133, p 0.067 | `2026-09-07-spatial-statistics-exclusion-base.csv`, `exclusion_base` rows; 190 = C(20,2) |
| P5 | two runs give byte-identical PNGs | as F1'/F2' (D-028 P4) |

## 5. What changes downstream

`2026-09-06-apply-rphase7-esm.py`: the four `\includegraphics` blocks become two, the `% PRE-AUDIT RENDER` flags
go, the section headings renumber S3 → S2, and the two cut figures' blocks are deleted. **Figure-only**, so it
owes a manifest re-cut and a preview rebuild — but the session already owes a full clean-room run for D-030's
new table, and these figures ride in it.
