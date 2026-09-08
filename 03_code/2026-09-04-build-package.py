#!/usr/bin/env python3
"""
R-PHASE 6 — build the replication package from the CORRECTED tree.

The 2026-08-04 package is not repaired, it is replaced: it shipped the v1 leaky feature tables, the
August code including three scripts EXP-017 retired, no `core.py`, empty result directories, a 60-byte
experiment log, an unbounded runner, `mapie==1.4.1` (the wrong version), and a REPLICATION.md whose
verification targets are now every one of them dead. It is retired under
`06_manuscript/CTR/replication/_superseded/` with a README saying so.

THE RULE THIS SCRIPT EXISTS TO ENFORCE: **every verification target in REPLICATION.md is READ FROM A CSV
at build time.** Nobody types a number into that file again. That is the structural fix for the failure
mode where a package ships targets that the paper stopped believing months earlier.

Outputs (nothing existing is overwritten; the repo's current README/REPLICATION/USER_ACTIONS are left
untouched and the new versions are written beside them, dated):
    06_manuscript/CTR/replication/2026-09-04-{README,REPLICATION,USER_ACTIONS}.md
    CITATION.cff, 01_data/DATA_DICTIONARY.md
    03_code/2026-09-04-environment.yml, 03_code/2026-09-04-Dockerfile
    06_manuscript/CTR/replication/2026-09-07-parking-conformal-reliability.zip
    (2026-09-07: re-dated for revision 49 -- D-030 added a TABLE
    (2026-09-07-spatial-statistics-exclusion-base.csv) and two read-only makers, and the ESM
    figures changed, so the package is rebuilt rather than repaired and the 2026-09-06 zip
    (sha256 885581665211c17e..., the artifact EXP-039 exercised) is retired byte-intact under
    replication/_superseded/2026-09-07-parking-conformal-reliability-S48.zip.)
    (2026-09-06: re-dated again for the defect-8 fix to
    03_code/src/conformal/2026-09-04-rphase5-failure-case.py (revision 46, EXP-038) -- a CODE file changed,
    so the package is rebuilt rather than repaired and the 2026-09-05 zip is retired under
    replication/_superseded/. Its sha256 6d7c413b... is pinned in EXP-038 as the artifact that run
    exercised, so it must survive.
    2026-09-05: re-dated when EXP-033 regenerated the E3 arm; the 2026-09-04 zip is retired under
     replication/_superseded/ and is not repaired in place -- a package and its numbers travel together.)

Usage:  python 03_code/2026-09-04-build-package.py [--stage-only]
"""
from __future__ import annotations
import argparse, csv, os, shutil, sys, zipfile
from pathlib import Path
import pandas as pd

p = Path(__file__).resolve()
while p != p.parent and not (p / "01_data").is_dir():
    p = p.parent
ROOT = p
TAB = ROOT / "05_results" / "tables"
REPL = ROOT / "06_manuscript" / "CTR" / "replication"
STAGE = Path(os.environ.get("PKG_STAGE", str(Path.home() / "pkgbuild"))) / "parking-conformal-reliability"
LOCK = ROOT / "03_code" / "2026-09-04-requirements.lock.txt"
ENVCSV = TAB / "2026-09-04-environment-recorded.csv"

TITLE = ("Average coverage is not enough: per-facility reliable conformal prediction for urban "
         "parking-occupancy forecasting")
AUTHOR = "Mohamed Abdelmagid"
AFFIL = "Khalifa University, Abu Dhabi, United Arab Emirates"
EMAIL = "100059835@ku.ac.ae"


def log(m): print(f"[pkg] {m}", flush=True)


MARKER = "2026-09-04-build-package.py"


def refuse(f: Path):
    """Refuse to clobber anything this script did not write.

    A build script must be re-runnable, but it must never overwrite a file a human authored. The test
    is the generator marker: if the existing file names this script as its generator, rewriting it is
    regeneration; if it does not, this is somebody else's file and the build stops.
    """
    if not f.exists():
        return
    try:
        if MARKER in f.read_text(errors="replace"):
            return
    except Exception:
        pass
    sys.exit(f"[pkg] REFUSING to overwrite {f.relative_to(ROOT)} — it was not written by this script. "
             f"Supersede by date instead.")


# ------------------------------------------------------------------------------------------------
# Verification targets, READ FROM CSVs. Never typed.
# ------------------------------------------------------------------------------------------------
def verification_targets() -> str:
    t = pd.read_csv(TAB / "2026-09-04-T3prime-two-level-inference.csv")
    core = t[t.scope.str.startswith("population + facility")]
    lines = [
        "| city | horizon | method | n | mean PICP | across-facility sd | worst facility | worst PICP |"
        " mean Winkler | source |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in core.iterrows():
        lines.append(
            f"| {r.city} | {r.horizon} | {r.method} | {int(r.n_facilities)} | {r.mean_PICP:.4f} | "
            f"{r.across_facility_sd:.4f} | {int(r.worst_facility)} | {r.worst_facility_PICP:.4f} | "
            f"{r.mean_Winkler:.2f} | `2026-09-04-T3prime-two-level-inference.csv` |")

    # Dispersion ratios come from the UNROUNDED per-facility aggregate, never from T3's 4-dp columns:
    # 0.0411 / 0.0053 rounds to 7.75x while the published spine is 7.76x, and a package that ships a
    # different figure from the manuscript is exactly the class of defect this rebuild exists to remove.
    hd = pd.read_csv(TAB / "2026-09-04-x08-core-headline-excl.csv")
    hb = hd[hd.city == "belgrade"].set_index("method")
    hm = hd[hd.city == "birmingham"].set_index("method")
    ratio = hb.loc["split-CP", "std"] / hb.loc["ACQR", "std"]
    ratio_b = hm.loc["split-CP", "std"] / hm.loc["ACI", "std"]
    bel = core[core.city == "belgrade"].set_index("method")

    cell = t[t.cells_below_080.notna()].set_index("method")
    scp = cell.loc["split-CP"]
    tod = cell.loc["ToD-ACI"]

    extra = [
        "",
        "**Derived checks** (each computed from the row above it, so a replicator can recompute them):",
        "",
        f"* Belgrade across-facility dispersion, split-CP / ACQR: **{ratio:.2f}x** "
        f"({hb.loc['split-CP','std']:.6f} / {hb.loc['ACQR','std']:.6f}, unrounded, from "
        f"`2026-09-04-x08-core-headline-excl.csv`).",
        f"* Birmingham across-facility dispersion, split-CP / ACI: **{ratio_b:.2f}x** "
        f"({hm.loc['split-CP','std']:.6f} / {hm.loc['ACI','std']:.6f}).",
        f"* Worst facility x time-of-day cell, split-CP **{scp.worst_facility_bucket_cell:.4f}** against "
        f"ToD-ACI **{tod.worst_facility_bucket_cell:.4f}**, with "
        f"**{int(scp.cells_below_080)} of {int(scp.n_cells)}** split-CP cells below 0.80 and "
        f"**{int(tod.cells_below_080)}** for ToD-ACI "
        "(`2026-09-04-T3prime-two-level-inference.csv`, cell-level reference rows).",
    ]

    m02 = TAB / "2026-09-04-x08-e3-summary-excl.csv"
    if m02.exists():
        d = pd.read_csv(m02).set_index(["dataset", "method"])
        for city in ("belgrade", "birmingham"):
            try:
                a = d.loc[(city, "NGBoost")]
                b = d.loc[(city, "NGBoost-conformal")]
                extra.append(
                    f"* {city.title()} conformalizing the SAME fitted NGBoost (M02): PICP "
                    f"**{a.mean_PICP:.4f} -> {b.mean_PICP:.4f}**, mean Winkler "
                    f"**{a.mean_Winkler:.2f} -> {b.mean_Winkler:.2f}** "
                    f"({100*(b.mean_Winkler-a.mean_Winkler)/a.mean_Winkler:+.2f}%), n = "
                    f"{int(a.n_facilities)} (`2026-09-04-x08-e3-summary-excl.csv`). This is the "
                    f"post-exclusion base; the pre-exclusion pair is superseded and is not quoted.")
            except KeyError:
                pass

    c01 = TAB / "2026-09-04-c01-attribution.csv"
    if c01.exists():
        d = pd.read_csv(c01)
        tr = d[d.arm_role == "treated"]
        ctl = d[d.arm_role == "negative-control"]
        for m, g in tr.groupby("method"):
            extra.append(f"* C01 order-statistic attribution, {m}: taking the (k+1)-th instead of the "
                         f"k-th order statistic widens intervals by **{100*g.rel_MPIW.mean():.2f}%** and "
                         f"lifts PICP by **{g.d_PICP.mean():.4f}**, at "
                         f"**{int((g.d_PICP>=0).sum())} of {len(g)}** facilities "
                         "(`2026-09-04-c01-attribution.csv`).")
        extra.append(f"* Built-in negative control for the above: split-CP and CQR are unaffected by C01, "
                     f"and differ across the two arms by exactly "
                     f"**{ctl[['d_PICP','d_MPIW','d_Winkler']].abs().to_numpy().max():.1f}**.")

    probe = TAB / "2026-09-04-determinism-probe.csv"
    if probe.exists():
        d = pd.read_csv(probe)
        pic = d[d.quantity == "PICP"]
        wid = d[d.quantity.isin(["MPIW", "Winkler"])]
        extra.append(f"* Reproducibility floor of this pipeline, measured: PICP max |difference| "
                     f"**{pic.abs_AC.max():.1f}** across a repeat and across thread counts; width "
                     f"statistics **{wid.rel_AC.max():.1e}** relative "
                     "(`2026-09-04-determinism-probe.csv`). This is why `verify.py` requires PICP to "
                     "match exactly and allows 1e-12 on widths.")
    return "\n".join(lines + extra)


def env_facts() -> dict:
    d = pd.read_csv(ENVCSV)
    return {r["name"]: r["version"] for _, r in d[d.kind == "environment"].iterrows()}


def pins() -> list[tuple[str, str]]:
    out = []
    for line in LOCK.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "==" in line:
            out.append(tuple(line.split(" ")[0].split("==")))
    return out


# ------------------------------------------------------------------------------------------------
def write_docs():
    env = env_facts()
    pin = pins()
    pinstr = "\n".join(f"  - {n}={v}" for n, v in pin)

    # ---- environment.yml -------------------------------------------------------------------
    yml = ROOT / "03_code" / "2026-09-04-environment.yml"
    refuse(yml)
    yml.write_text(
        "# Conda environment for the parking conformal-prediction replication package.\n"
        "# Generated by 03_code/2026-09-04-build-package.py — do not hand-edit.\n"
        "# Generated from 2026-09-04-requirements.lock.txt; do not edit by hand.\n"
        "# The pins are NOT advisory: LESSONS_LOG A13 records a measured case in this project where an\n"
        "# unpinned MAPIE moved a published coverage number.\n"
        "name: parking-cp\n"
        "channels: [conda-forge]\n"
        "dependencies:\n"
        f"  - python={env.get('python_version','3.10.12')}\n"
        "  - pip\n"
        "  - pip:\n" + "\n".join(f"    - {n}=={v}" for n, v in pin) + "\n")
    log(f"wrote {yml.name}")

    # ---- Dockerfile ------------------------------------------------------------------------
    dock = ROOT / "03_code" / "2026-09-04-Dockerfile"
    refuse(dock)
    dock.write_text(
        f"# Clean-room image for the replication package. Generated by\n"
        f"# 03_code/2026-09-04-build-package.py — do not hand-edit.\n"
f"# Built to match the environment every\n"
        f"# published number was computed under, recorded in\n"
        f"# 05_results/tables/2026-09-04-environment-recorded.csv.\n"
        f"#\n"
        f"# NOTE, and it matters: this image installs from the LOCK FILE's wheels and pins NO system\n"
        f"# BLAS. The recorded environment loads two different bundled OpenBLAS builds at once\n"
        f"# (numpy's and scipy's, {env.get('numpy_blas','')}), and forcing a single system BLAS would be\n"
        f"# a DIFFERENT numerical environment from the one the numbers come from.\n"
        f"#\n"
        f"#   docker build -f 03_code/2026-09-04-Dockerfile -t parking-cp .\n"
        f"#   docker run --rm -v \"$PWD\":/work -w /work parking-cp bash run_all.sh\n"
        f"FROM python:{env.get('python_version','3.10.12')}-slim\n"
        f"# recorded host: {env.get('platform','')} / {env.get('libc','')} / "
        f"BLAS {env.get('numpy_blas','')} / LAPACK {env.get('numpy_lapack','')}\n"
        f"WORKDIR /work\n"
        f"COPY 03_code/2026-09-04-requirements.lock.txt /tmp/lock.txt\n"
        f"RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/lock.txt\n"
        f"ENV PYTHONDONTWRITEBYTECODE=1\n"
        f"CMD [\"bash\", \"run_all.sh\"]\n")
    log(f"wrote {dock.name}")

    # ---- CITATION.cff ----------------------------------------------------------------------
    cff = ROOT / "CITATION.cff"
    refuse(cff)
    cff.write_text(
        "# Generated by 03_code/2026-09-04-build-package.py — do not hand-edit.\n"
        "cff-version: 1.2.0\n"
        "message: \"If you use this software or the processed data, please cite the article below.\"\n"
        "type: software\n"
        f"title: \"Replication package: {TITLE}\"\n"
        "authors:\n"
        f"  - family-names: Abdelmagid\n    given-names: Mohamed\n"
        f"    affiliation: \"{AFFIL}\"\n    email: {EMAIL}\n"
        "license: MIT\n"
        "license-url: \"https://opensource.org/licenses/MIT\"\n"
        "repository-code: \"https://github.com/mtdfalla/parking-conformal-reliability\"\n"
        "date-released: 2026-09-04\n"
        "keywords:\n"
        "  - conformal prediction\n  - prediction intervals\n  - uncertainty quantification\n"
        "  - parking occupancy\n  - intelligent transportation systems\n  - evaluation methodology\n"
        "abstract: >-\n"
        "  Code and processed data reproducing every table in the article. The package evaluates split\n"
        "  conformal prediction, CQR, delay-aware adaptive conformal inference and adaptive CQR on two\n"
        "  city parking-occupancy records, at the population level and at the facility level, and\n"
        "  quantifies how much eight evaluation-protocol choices move a reported coverage number.\n"
        "preferred-citation:\n"
        "  type: article\n"
        f"  title: \"{TITLE}\"\n"
        "  authors:\n"
        f"    - family-names: Abdelmagid\n      given-names: Mohamed\n      affiliation: \"{AFFIL}\"\n"
        "  year: 2026\n"
        "  notes: \"Under review. Journal, volume, pages and DOI to be added on acceptance.\"\n")
    log("wrote CITATION.cff")

    # ---- data dictionary --------------------------------------------------------------------
    dd = ROOT / "01_data" / "2026-09-04-DATA-DICTIONARY-processed.md"
    refuse(dd)
    parts = ["<!-- Generated by 03_code/2026-09-04-build-package.py. Do not hand-edit. -->\n", "# Data dictionary — PROCESSED tables\n\n> The June-2026 `DATA_DICTIONARY.md` in this folder documents the RAW sources and is kept\n> unchanged beside this file. This one documents the processed tables the analysis actually\n> reads, and it is generated from their schemas.\n",
             "Generated by `03_code/2026-09-04-build-package.py` from the parquet schemas themselves, so",
             "it cannot drift from the files it describes.\n",
             "## Column meanings by family\n",
             "| column family | meaning |",
             "|---|---|",
             "| `facility_id` | integer id of the car park, stable across all tables |",
             "| `timestamp` | local time at the start of the interval |",
             "| `occupancy` | occupied spaces reported by the feed at `timestamp` |",
             "| `capacity` | nominal capacity where the source supplies one; the analysis uses a "
             "**training-window-only** proxy instead (decision D01) |",
             "| `y_t+<H>` | the forecast target: occupancy H minutes ahead |",
             "| `use_<H>` | boolean. TRUE when this row may be used at horizon H: same split, embargo "
             "respected, and for Birmingham no lag, anchor or target crossing a night (S01, S02/X01) |",
             "| `lag_*`, `roll_*` | causal lag and rolling features, computed from the past only |",
             "| `tod_sin`, `tod_cos` | time of day encoded on the circle |",
             "| `dow`, `is_weekend`, `is_holiday` | day of week; weekend flag; national holiday flag |",
             "| `split` | `train` / `calibration` / `test`, assigned by time and never by sampling |",
             "| `interpolated` | TRUE where the value was filled to the analysis grid |",
             "",
             "## Exclusion rule applied to every reported number\n",
             "A facility-window is excluded when it carries **fewer than 10 distinct occupancy readings**",
             "in the evaluation window (`core.low_information_facilities`). The rule is stated on the",
             "inputs alone and is blind to every method's performance. Its threshold is not delicate, and",
             "the gap is published rather than just the cutoff: Belgrade facility 1 has **1** distinct",
             "reading, facility 8 has **2**, and the next lowest has **64** — so any cutoff in [3, 60]",
             "selects the same two facilities. Birmingham excludes none.\n",
             "## Schemas as shipped\n"]
    for f in sorted((ROOT / "01_data" / "processed").glob("*_v2.parquet")):
        d = pd.read_parquet(f)
        parts += [f"### `{f.name}`\n",
                  f"{len(d):,} rows x {len(d.columns)} columns; "
                  f"{d.facility_id.nunique()} facilities; "
                  f"{pd.to_datetime(d.timestamp).min()} to {pd.to_datetime(d.timestamp).max()}.\n",
                  "| column | dtype | non-null |", "|---|---|---|"]
        for c in d.columns:
            parts.append(f"| `{c}` | {d[c].dtype} | {d[c].notna().sum():,} |")
        parts.append("")
    dd.write_text("\n".join(parts) + "\n")
    log(f"wrote 01_data/{dd.name}")

    # ---- README / REPLICATION / USER_ACTIONS -------------------------------------------------
    targets = verification_targets()
    readme = REPL / "2026-09-04-README.md"
    repl = REPL / "2026-09-04-REPLICATION.md"
    ua = REPL / "2026-09-04-USER_ACTIONS.md"
    for f in (readme, repl, ua):
        refuse(f)

    readme.write_text(f"""<!-- Generated by 03_code/2026-09-04-build-package.py. Do not hand-edit. -->
# Replication package — "{TITLE}"

Author: {AUTHOR} ({AFFIL}) · Contact: {EMAIL}

This package reproduces **every table in the article** from the included processed datasets, and
regenerates the figures. Read `REPLICATION.md` for the script-to-artifact map, the verification
targets and the tolerances.

**What this package can and cannot do, stated plainly** (audit issues R03/R04/X02): it runs
**processed data -> results**. The preprocessing and feature-building scripts are included for
provenance and can rebuild the processed tables from raw, but the raw Belgrade feed is not
redistributed here (see *Data & licences*). The two article figures, F1' and F2', are produced by the
`figures` step (`03_code/src/viz/2026-09-06-figures-f1-f2.py`) from manifest-listed tables on the
excluded base; like every figure they are regenerated and inspected, never hashed.

## Layout
```
01_data/processed/     processed datasets (v2 causal tables) + DATA_DICTIONARY.md
03_code/               all analysis code
  src/conformal/       core.py plus every experiment script
  tests/               property suites: conformal core, split integrity, environment restore
  verify.py            checks outputs against the manifest and the tolerance table
  2026-09-04-requirements.lock.txt / -environment.yml / -Dockerfile
04_experiments/        EXPERIMENTS_LOG.md — the full experiment record, not a placeholder
05_results/reference/  the outputs we obtained; verify.py compares your run against these
05_results/tables/     where YOUR run lands
07_logs/               per-step logs written by run_all.sh
run_all.sh             one command, bounded retries, fails loudly
```

## Quick start
```
python -m venv venv && source venv/bin/activate
pip install --require-hashes --no-deps -r 03_code/2026-09-04-requirements.lock.txt
bash run_all.sh              # every step is resumable; --smoke for a bounded check
python 03_code/verify.py     # exits nonzero on any mismatch
```
Or build the recorded environment exactly:
`docker build -f 03_code/2026-09-04-Dockerfile -t parking-cp . && docker run --rm -v "$PWD":/work -w /work parking-cp`

**Pin the versions.** The lock file is not advisory. Re-running one baseline under a different MAPIE
release already changed a published coverage figure in this project by 1-2 coverage indicators; the
lock file is what prevents that.

## Data & licences
- `belgrade_*` — processed Belgrade parking-occupancy data (24 facilities, 2-minute source cadence
  resampled to 5 minutes, 4-21 March 2017). **CC0 1.0.**
- `birmingham_*` — features derived from the **Parking Birmingham** dataset (Birmingham City Council
  via the UCI Machine Learning Repository, dataset 482, CC BY 4.0). Attribution is required by the
  source licence, and our derived files are shared under the **same CC BY 4.0 terms**.
- Code — **MIT** (see `LICENSE`).

These are **file-level** licences. They are not interchangeable and the package must not be deposited
anywhere under a single blanket licence.

## Citation
See `CITATION.cff`. The article is under review; the journal, DOI and data DOI are added on acceptance.
""")
    log(f"wrote {readme.name}")

    repl.write_text(f"""<!-- Generated by 03_code/2026-09-04-build-package.py. Do not hand-edit. -->
# Replication explanatory file

**Article:** {TITLE}
**Author:** {AUTHOR}, {AFFIL} ({EMAIL})

## 1. Data and code

Everything needed is in this package: processed datasets in `01_data/processed/` (documented in
`01_data/DATA_DICTIONARY.md`) and all analysis code in `03_code/`. No external download is required.

The raw Birmingham source is public (Birmingham City Council, UCI Machine Learning Repository,
dataset 482, CC BY 4.0). The raw Belgrade feed was obtained from the city parking operator and is
shared here **in processed form** under CC0.

**Deposit status, stated accurately:** a permanent data deposit is prepared but **has not been made**.
It is held pending written confirmation of redistribution rights from the Belgrade operator. When a
DOI exists it will be added here and in the article; until then this file does not claim one.

## 2. Environment

Python {env.get('python_version','3.10.12')}. Install from the lock file with `--require-hashes`.
Recorded host for the reference outputs: {env.get('platform','')}, {env.get('libc','')},
BLAS {env.get('numpy_blas','')}, {env.get('cpu_count','?')} CPU(s).

{pinstr}

## 3. One-command replication

`bash run_all.sh`. Every step is resumable and bounded: a failing step stops the run with a nonzero
exit and its log in `07_logs/`, and no step can loop indefinitely. `bash run_all.sh --list` prints the
step names; `--from STEP` resumes; `--only STEP` runs one.

## 4. Verification targets — GENERATED FROM THE RESULT CSVs AT BUILD TIME

Every number below was read out of a CSV in this package when the package was built. None was typed.
This is deliberate: the previous version of this file shipped hand-copied targets that the analysis
had since superseded, so a replicator following it would have failed every one of them.

{targets}

`python 03_code/verify.py` performs these comparisons for you, over every shipped table, and exits
nonzero on any mismatch.

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
differences only. It cannot absorb a library-version difference — that is what the lock file is for.

## 6. Randomness and seeds

Seed 42 throughout (random forests, gradient boosting, bootstrap resampling, demand draws).
Bootstrap: moving-block with **B = 10,000** resamples and a **cadence-derived 3-hour block**
(36 rows at Belgrade's 5-minute cadence, 6 at Birmingham's 30-minute). Paired contrasts use 10,000
facility resamples with Holm correction within family within city.

## 7. Licences

Code MIT; Belgrade-derived data CC0 1.0; Birmingham-derived data CC BY 4.0 with attribution to
Birmingham City Council via the UCI Machine Learning Repository. See `LICENSE`. **File-level, not
blanket** — see `USER_ACTIONS.md`.
""")
    log(f"wrote {repl.name}")

    ua.write_text(f"""<!-- Generated by 03_code/2026-09-04-build-package.py. Do not hand-edit. -->
# Author actions for this package

## 1. Code mirror (GitHub)

The repository `parking-conformal-reliability` is **private** and stays private until the licensing
position below is resolved. When it is made public, upload the contents of the unzipped package.

## 2. Data deposit — **HELD. Do not upload.**

**Do not deposit this package under a single blanket licence, and do not deposit it at all yet.**

Reason: the package contains data under **two different licences**, and the deposit platform's default
of "CC0 for the whole upload" would relicense the Birmingham-derived files, whose source licence
(CC BY 4.0) **requires attribution** and cannot be waived by us. Separately, written confirmation of
redistribution rights for the Belgrade processed data has been requested from the operator and has not
yet arrived.

When the deposit is made, it must be one of:

* **file-level licences** — Belgrade-derived files CC0 1.0, Birmingham-derived files CC BY 4.0 with the
  Birmingham City Council / UCI attribution; or
* **two deposit components**, one per licence, cross-referenced.

Ask the replication editor in writing which of the two the platform supports, and keep the answer.

## 3. What to send back when both are done

The repository URL and the data DOI. They are then inserted into the article's data-availability
section, `README.md`, `REPLICATION.md` and the cover letter.

## 4. Do not reintroduce

* A single blanket licence for the whole upload.
* Any hand-typed verification target in `REPLICATION.md` — they are generated from the CSVs.
* The 2026-08-04 package, retired in `_superseded/`. Every number it produces is superseded.
""")
    log(f"wrote {ua.name}")
    return readme, repl, ua


# ------------------------------------------------------------------------------------------------
def stage(readme, repl, ua):
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    def put(src: Path, rel: str):
        dst = STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "_retired", "_superseded",
                                                          "*.pyc", "_provenance-not-used"))
        else:
            shutil.copy2(src, dst)

    for f in sorted((ROOT / "01_data" / "processed").glob("*")):
        put(f, f"01_data/processed/{f.name}")
    # The v1 tables ARE shipped, and they carry a warning file. They are needed by exactly one step —
    # the A12_v1_paired arm of the E3 baselines, which measures the C07 chunking delta paired inside one
    # fitted model and is row 1 of T6. Withholding them would make a REPORTED number unverifiable, and a
    # paper whose contribution is protocol sensitivity cannot ship a package that hides the inputs its
    # own sensitivity table is computed from. The leakage is handled by labelling, not by omission.
    (STAGE / "01_data" / "processed" / "README-v1-tables.md").write_text(
        "# The v1 feature tables: attribution only. NOT for any reported result.\n\n"
        "`belgrade_features.parquet` and `birmingham_features.parquet` are the **v1** tables. They\n"
        "carry the defects the revision fixed:\n\n"
        "* **S01** — training and calibration rows whose outcome is observed in a later split.\n"
        "* **S02 / X01** — Birmingham lags, anchors and targets that cross a night boundary, which\n"
        "  contaminated about 10% of the t+90 targets.\n\n"
        "**Every reported number in the article is computed on the `*_features_v2.parquet` tables.**\n"
        "The v1 tables are shipped for one reason: the `A12_v1_paired` arm of\n"
        "`03_code/src/conformal/2026-09-03-e3-baselines.py` runs both EnbPI chunking schemes on ONE\n"
        "fitted model per facility to attribute the C07 protocol delta (row 1 of the\n"
        "protocol-sensitivity table). That comparison is only meaningful on the configuration the\n"
        "archived result came from, and it is paired inside a single fit, so the leakage is common to\n"
        "both sides of the delta and cancels.\n\n"
        "Do not use these tables for anything else. `run_all.sh` uses them for that one arm and\n"
        "nowhere else.\n")
    put(ROOT / "01_data" / "2026-09-04-DATA-DICTIONARY-processed.md",
        "01_data/DATA_DICTIONARY.md")
    put(ROOT / "01_data" / "DATA_DICTIONARY.md",
        "01_data/DATA_DICTIONARY-raw-provenance.md")

    put(ROOT / "03_code" / "src", "03_code/src")
    put(ROOT / "03_code" / "tests", "03_code/tests")
    put(ROOT / "03_code" / "verify.py", "03_code/verify.py")
    for n in ("2026-09-04-requirements.lock.txt", "2026-09-04-environment.yml",
              "2026-09-04-Dockerfile", "2026-09-04-build-lockfile.py",
              "2026-09-04-build-package.py",
              # 2026-09-05 (revision 45): the GENERATOR of the unstable-cell registry ships too. The
              # package carries a mechanism that can excuse a differing cell, so a replicator must be able
              # to see how the registry was produced and re-derive it from the probe -- shipping the
              # registry without its generator is a provenance hole in exactly the place that needs one.
              # `03_code/tests/` already ships wholesale, so the probe and the four negative controls are
              # in the package alongside it.
              "2026-09-05-build-unstable-cells.py"):
        put(ROOT / "03_code" / n, f"03_code/{n}")

    put(ROOT / "04_experiments" / "EXPERIMENTS_LOG.md", "04_experiments/EXPERIMENTS_LOG.md")
    for n in sorted((ROOT / "04_experiments").glob("*PRESPECIFICATION.md")):
        put(n, f"04_experiments/{n.name}")

    # 2026-09-05 (revision 44, EXP-035): the archived-artifact list MUST ship. `verify.py` reads it to
    # tell an artifact that no live step regenerates (branch S) from one that failed to regenerate; a
    # package without it reports 58 non-defects as failures, which is the same class of damage as the
    # dead verification targets this rebuild exists to remove. Found by running verify.py inside a
    # freshly unzipped package rather than in the repository.
    put(ROOT / "00_admin" / "2026-09-05-archived-artifacts.csv",
        "00_admin/2026-09-05-archived-artifacts.csv")
    # 2026-09-05 (revision 45, EXP-036): the unstable-cell registry must ship for the same reason the
    # archived list must (C14) -- `verify.py` reads it from 00_admin/, so without it a replicator sees the
    # measurably-nondeterministic facility-8 AgACI cell reported as a defect in their environment. It is
    # GENERATED by 03_code/2026-09-05-build-unstable-cells.py from an append-only probe, never typed.
    put(ROOT / "00_admin" / "2026-09-05-unstable-cells.csv",
        "00_admin/2026-09-05-unstable-cells.csv")
    put(ROOT / "05_results" / "reference", "05_results/reference")
    put(ROOT / "05_results" / "figures", "05_results/figures")
    (STAGE / "05_results" / "tables").mkdir(parents=True, exist_ok=True)
    (STAGE / "05_results" / "tables" / ".gitkeep").write_text(
        "# Your run's outputs land here. The reference outputs we obtained are in ../reference/.\n")
    (STAGE / "07_logs").mkdir(exist_ok=True)
    (STAGE / "07_logs" / ".gitkeep").write_text("# run_all.sh writes one log per step here.\n")
    import datetime
    (STAGE / "BUILD-INFO.txt").write_text(
        "Replication package build information\n"
        "=====================================\n"
        f"Generated by 03_code/2026-09-04-build-package.py\n"
        f"Build date (UTC): {datetime.datetime.utcnow().isoformat(timespec='seconds')}Z\n"
        "Source tree: the corrected post-audit repository (R-Phases 0-6).\n"
        "Supersedes: 2026-08-04 package, retired with a written reason under\n"
        "  06_manuscript/CTR/replication/_superseded/.\n"
        "Every verification target in REPLICATION.md was read from a CSV at build time.\n")

    # The repository's manifest is NOT copied: its paths are repository paths, and several of them
    # (the dated docs, the v1 feature tables that are deliberately not shipped) do not exist in the
    # package layout. A manifest that does not match the tree it ships with is worse than none, so the
    # package's manifest is cut FROM THE STAGED TREE, below, by the same verify.py the replicator runs.
    put(ROOT / "run_all.sh", "run_all.sh")
    put(ROOT / "CITATION.cff", "CITATION.cff")
    put(readme, "README.md")
    put(repl, "REPLICATION.md")
    put(ua, "USER_ACTIONS.md")

    (STAGE / "LICENSE").write_text(f"""MIT License

Copyright (c) 2026 {AUTHOR}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---
DATA LICENCES — FILE LEVEL, NOT BLANKET. These differ per file and may not be merged.

Belgrade-derived files under 01_data/ (belgrade_*.parquet, facility_coords.parquet,
facility_index.csv): dedicated to the public domain under CC0 1.0
(https://creativecommons.org/publicdomain/zero/1.0/).

Birmingham-derived files under 01_data/ (birmingham_*.parquet): distributed under CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/) with the attribution REQUIRED by the source licence:
Birmingham City Council (2016), Parking Birmingham, via the UCI Machine Learning Repository,
dataset 482, https://archive.ics.uci.edu/dataset/482/parking+birmingham.

This attribution requirement cannot be waived by the authors of this package. Depositing the whole
package under a single permissive licence would misrepresent it.
""")
    n = sum(1 for _ in STAGE.rglob("*") if _.is_file())
    log(f"staged {n} files at {STAGE}")

    # Cut the package's own manifest from the staged tree, then verify the staged tree against it.
    import subprocess
    r = subprocess.run([sys.executable, "03_code/verify.py", "--build"], cwd=STAGE,
                       capture_output=True, text=True)
    print("".join("    " + l + "\n" for l in r.stdout.strip().splitlines()))
    if r.returncode != 0:
        sys.exit(f"[pkg] staged-manifest build failed:\n{r.stderr}")
    r = subprocess.run([sys.executable, "03_code/verify.py", "--smoke"], cwd=STAGE,
                       capture_output=True, text=True)
    print("".join("    " + l + "\n" for l in r.stdout.strip().splitlines()))
    if r.returncode != 0:
        sys.exit("[pkg] the STAGED package does not verify against its own manifest — not shipping it.")
    log("staged package verifies against its own manifest")
    return n


def zip_it():
    out = REPL / "2026-09-07-parking-conformal-reliability.zip"
    if out.exists():
        # A zip is not readable as text, so refuse() cannot see the generator marker. Look for the
        # BUILD-INFO.txt this script writes into every package it builds instead.
        try:
            with zipfile.ZipFile(out) as z:
                if MARKER not in z.read(
                        "parking-conformal-reliability/BUILD-INFO.txt").decode("utf-8", "replace"):
                    raise KeyError
        except Exception:
            sys.exit(f"[pkg] REFUSING to overwrite {out.name} — it was not built by this script.")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(STAGE.rglob("*")):
            if f.is_file():
                z.write(f, f"parking-conformal-reliability/{f.relative_to(STAGE).as_posix()}")
    log(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size/1e6:.1f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-only", action="store_true")
    a = ap.parse_args()
    readme, repl, ua = write_docs()
    stage(readme, repl, ua)
    if not a.stage_only:
        zip_it()
    log("ALL DONE")


if __name__ == "__main__":
    main()
