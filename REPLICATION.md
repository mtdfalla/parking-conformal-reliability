<!-- Generated file. Do not hand-edit. -->
# Replication explanatory file

**Article:** Average Coverage Is Not Enough: A Facility-Level Audit of Conformal Prediction for Urban Parking-Occupancy Forecasting
**Author:** Mohamed Abdelmagid, Khalifa University, Abu Dhabi, United Arab Emirates (100059835@ku.ac.ae)

## 1. Data and code

All analysis code is in `03_code/`. The processed Birmingham tables are in `01_data/processed/`,
documented in `01_data/DATA_DICTIONARY.md`. The processed Belgrade tables are **not redistributed**
in this repository. `DATA_AVAILABILITY.md` and `01_data/processed/BELGRADE-DATA.md` give the reason,
the acquisition route and the SHA-256 of each withheld file. Steps that read the Belgrade tables stop
with a missing-input error until those files are supplied. The Birmingham steps run unaided.

The raw Birmingham source is public (Birmingham City Council, UCI Machine Learning Repository,
dataset 482, CC BY 4.0). The raw Belgrade feed was obtained from the city parking operator, and we
hold no documented authority to redistribute it in raw or processed form.

**Archive.** This repository is archived at Zenodo. The concept DOI `10.5281/zenodo.22664704`
resolves to the newest version.

## 2. Environment

Python 3.10.12. Install from the lock file with `--require-hashes`.
Recorded host for the reference outputs: Linux-6.8.0-136-generic-x86_64-with-glibc2.35, glibc-2.35,
BLAS scipy-openblas 0.3.29, 2 CPU(s).

  - numpy=2.2.6
  - pandas=2.3.3
  - matplotlib=3.10.9
  - pyarrow=25.0.1
  - scipy=1.15.3
  - scikit-learn=1.7.2
  - joblib=1.6.0
  - threadpoolctl=3.6.0
  - cloudpickle=3.1.2
  - mapie=1.5.0
  - ngboost=0.5.11
  - tqdm=4.70.0
  - holidays=0.103

## 3. One-command replication

`bash run_all.sh`. Every step is resumable and bounded: a failing step stops the run with a nonzero
exit and its log in `07_logs/`, and no step can loop indefinitely. `bash run_all.sh --list` prints the
step names; `--from STEP` resumes; `--only STEP` runs one.

## 4. Verification targets, generated from the result CSVs at build time

Every number below was read out of a CSV in this package when the package was built. None was typed.
This is deliberate: the previous version of this file shipped hand-copied targets that the analysis
had since superseded, so a replicator following it would have failed every one of them.

| city | horizon | method | n | mean PICP | across-facility sd | worst facility | worst PICP | mean Winkler | source |
|---|---|---|---|---|---|---|---|---|---|
| belgrade | y_t+15min | split-CP | 21 | 0.9008 | 0.0411 | 9 | 0.7872 | 23.92 | `2026-09-04-T3prime-two-level-inference.csv` |
| belgrade | y_t+15min | CQR | 21 | 0.8995 | 0.0289 | 9 | 0.8266 | 19.63 | `2026-09-04-T3prime-two-level-inference.csv` |
| belgrade | y_t+15min | ACI | 21 | 0.8912 | 0.0077 | 13 | 0.8690 | 22.53 | `2026-09-04-T3prime-two-level-inference.csv` |
| belgrade | y_t+15min | ACQR | 21 | 0.8940 | 0.0053 | 13 | 0.8788 | 19.30 | `2026-09-04-T3prime-two-level-inference.csv` |
| birmingham | y_t+60min | split-CP | 28 | 0.8916 | 0.0550 | 7 | 0.7168 | 215.95 | `2026-09-04-T3prime-two-level-inference.csv` |
| birmingham | y_t+60min | CQR | 28 | 0.8976 | 0.0492 | 7 | 0.7522 | 219.38 | `2026-09-04-T3prime-two-level-inference.csv` |
| birmingham | y_t+60min | ACI | 28 | 0.8793 | 0.0227 | 24 | 0.8214 | 221.14 | `2026-09-04-T3prime-two-level-inference.csv` |
| birmingham | y_t+60min | ACQR | 28 | 0.8919 | 0.0278 | 22 | 0.8333 | 227.11 | `2026-09-04-T3prime-two-level-inference.csv` |

**Derived checks** (each computed from the row above it, so a replicator can recompute them):

* Belgrade across-facility dispersion, split-CP / ACQR: **7.73x** (0.041135 / 0.005319, unrounded, from `2026-09-04-x08-core-headline-excl.csv`).
* Birmingham across-facility dispersion, split-CP / ACI: **2.42x** (0.054968 / 0.022750).
* Worst facility x time-of-day cell, split-CP **0.5160** against ToD-ACI **0.8421**, with **12 of 105** split-CP cells below 0.80 and **0** for ToD-ACI (`2026-09-04-T3prime-two-level-inference.csv`, cell-level reference rows).
* Belgrade conformalizing the SAME fitted NGBoost (M02): PICP **0.7736 -> 0.8917**, mean Winkler **22.00 -> 19.87** (-9.68%), n = 21 (`2026-09-04-x08-e3-summary-excl.csv`). This is the post-exclusion base; the pre-exclusion pair is superseded and is not quoted.
* Birmingham conformalizing the SAME fitted NGBoost (M02): PICP **0.3299 -> 0.8993**, mean Winkler **510.44 -> 214.14** (-58.05%), n = 28 (`2026-09-04-x08-e3-summary-excl.csv`). This is the post-exclusion base; the pre-exclusion pair is superseded and is not quoted.
* C01 order-statistic attribution, ACI: taking the (k+1)-th instead of the k-th order statistic widens intervals by **0.27%** and lifts PICP by **0.0004**, at **21 of 21** facilities (`2026-09-04-c01-attribution.csv`).
* C01 order-statistic attribution, ACQR: taking the (k+1)-th instead of the k-th order statistic widens intervals by **0.50%** and lifts PICP by **0.0002**, at **20 of 21** facilities (`2026-09-04-c01-attribution.csv`).
* Built-in negative control for the above: split-CP and CQR are unaffected by C01, and differ across the two arms by exactly **0.0**.
* Reproducibility floor of this pipeline, measured: PICP max |difference| **0.0** across a repeat and across thread counts; width statistics **2.2e-16** relative (`2026-09-04-determinism-probe.csv`). This is why `verify.py` requires PICP to match exactly and allows 1e-12 on widths.

`python 03_code/verify.py` performs these comparisons for you, over every shipped table, and exits
nonzero on any mismatch.

`DISPLAY-ITEM-SOURCES.md` names the table behind every table, figure and quoted number of the article,
and `python 06_manuscript/CTR/2026-09-06-typeset-tables.py` turns the tables of a run into the article's
table bodies (`06_manuscript/CTR/_build/typeset.json`), so a run can be compared with the printed
tables directly.

## 5. Tolerances, and why they are what they are

| class | applies to | criterion |
|---|---|---|
| exact | PICP, coverage indicators, counts, ids, levels, selected gamma | equality |
| tight | MPIW, Winkler and other width/efficiency statistics | relative <= 1e-12 |
| declared | bootstrap CI bounds, p-values | relative <= 1e-9 |
| not gated | figures | regenerated and inspected, never hashed |

These were fixed **before** any clean-room run, against a measured floor: on this pipeline PICP is
bit-identical across a repeat and across thread counts, and width statistics agree to ~2e-16 relative
(`05_results/reference/2026-09-04-determinism-probe.csv`). The tolerance covers thread-scheduling
differences only. It cannot absorb a library-version difference, which is what the lock file is for.

## 6. Randomness and seeds

Seed 42 throughout (random forests, gradient boosting, bootstrap resampling, demand draws).
Bootstrap: moving-block with **B = 10,000** resamples and a **cadence-derived 3-hour block**
(36 rows at Belgrade's 5-minute cadence, 6 at Birmingham's 30-minute). Paired contrasts use 10,000
facility resamples with Holm correction within family within city.

## 7. Licences

Code MIT. Birmingham-derived data CC BY 4.0 with attribution to Birmingham City Council via the
UCI Machine Learning Repository. The Belgrade data are not redistributed and no licence is granted
over them. See `LICENSE` and `DATA_AVAILABILITY.md`. The licences are file-level and must not be
replaced by a single blanket licence.
