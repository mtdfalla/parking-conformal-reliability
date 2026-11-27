<!-- Generated file. Do not hand-edit. -->
# Average Coverage Is Not Enough: A Facility-Level Audit of Conformal Prediction for Urban Parking-Occupancy Forecasting

Replication package · Mohamed Abdelmagid · Khalifa University, Abu Dhabi, United Arab Emirates · 100059835@ku.ac.ae

This repository reproduces the results of the accompanying article: seven interval-forecasting
methods evaluated on 49 parking facilities in two cities under a delay-aware (no-lookahead) protocol,
with a two-level evaluation standard that separates population-level from per-facility validity.

> **Read `DATA_AVAILABILITY.md` first.** The Birmingham data are included in full; the Belgrade data
> are **not redistributed** for rights reasons, and `01_data/processed/BELGRADE-DATA.md` gives the
> acquisition route, the schema and the SHA-256 of every withheld file.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # the 13 analysis packages at the exact versions of the article
bash run_all.sh --list            # the step list
bash run_all.sh --city birmingham # the public-data path, end to end, then verify.py --smoke
```

`requirements.txt` pins the 13 packages the analysis imports, at the versions every reported number
was computed under, and lets pip resolve their own dependencies. Tested on Linux x86-64 with Python 3.10
and 3.12. `03_code/2026-09-04-requirements.lock.txt` records the same pins with the SHA-256 of each wheel
used. Its compiled wheels are CPython 3.10 builds and it lists no dependencies, so it is an audit record
of the exact build, not an install file.

**`bash run_all.sh` without `--city` runs both cities** and stops with a missing-input error at the first
Belgrade step until you supply the Belgrade files. `--city birmingham` runs every step that needs only the
Birmingham data and prints each step it skips. It does not regenerate the tables whose steps also read the
Belgrade data, including every table that pools both cities. `REPLICATION.md` section 3 lists them. The
path ends with `python 03_code/verify.py --smoke`, which compares every table the run wrote with its
reference and skips the rest. Without `--smoke`, verify.py reports each table the run did not write as
`B NOTRUN` and exits nonzero. `--smoke` shortens no step. `--only STEP` and `--from STEP` run a subset.

**Pin the versions.** The pins are not advisory. Re-running one baseline under a different MAPIE
release already moved a published coverage figure in this project by 1–2 coverage indicators. The
pins are what prevent that.

## Layout

```
01_data/processed/     processed datasets + DATA_DICTIONARY.md + BELGRADE-DATA.md
03_code/               all analysis code
  src/conformal/       core.py and every experiment script
  tests/               property suites: conformal core, split integrity, environment restore
  verify.py            checks outputs against the manifest and the tolerance table
04_experiments/        EXPERIMENTS_LOG.md, the full experiment record
05_results/reference/  the outputs we obtained; verify.py compares your run against these
05_results/tables/     where YOUR run lands
06_manuscript/CTR/     2026-09-06-typeset-tables.py: turns a run's tables into the article's table bodies
DISPLAY-ITEM-SOURCES.md  which table each article table, figure and quoted number is computed from
07_logs/               per-step logs written by run_all.sh
run_all.sh             one command, bounded retries, fails loudly
```

`REPLICATION.md` has the script-to-artifact map, the verification targets and the tolerances.

## Two reproducibility facts we report rather than assume

1. The NGBoost baseline's fit read the **global** random-number state, so its predictions depended on
   process history. It is now seeded immediately before each call and reproduces bit-for-bit.
2. One excluded Belgrade facility remains run-to-run nondeterministic in the widths of one aggregated
   method at the 1e-6 relative level, because its two-valued series creates exact ties between
   outcomes and interval bounds. Outside the data-quality row of the protocol-sensitivity table, no reported
   coverage, width or test depends on that facility.

## Licences

Code **MIT**. Birmingham-derived data **CC BY 4.0** (attribution required). See `DATA_AVAILABILITY.md`.
The licences are file-level and must not be replaced by a single blanket licence.

## Citation

See `CITATION.cff`. The article is under review; the journal reference and DOI are added on
acceptance. This repository is archived at Zenodo, and the concept DOI `10.5281/zenodo.22664704`
always resolves to its newest version.
