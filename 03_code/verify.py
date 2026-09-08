#!/usr/bin/env python3
"""
verify.py — R-Phase 6 (audit issues R03, X02). The gate a replicator can run.

WHAT IT CHECKS, in three phases:

  A. INTEGRITY.  Every input, script, reference output and packaging document listed in the manifest
     still hashes to what the manifest records. Catches an edited script or a swapped dataset.

  B. REPRODUCTION.  Every table produced by a fresh run into `05_results/tables/` is compared, cell by
     cell, against the shipped reference in `05_results/reference/`, using the TOLERANCE TABLE fixed in
     `04_experiments/2026-09-04-rphase6-PRESPECIFICATION.md` section 4 BEFORE any clean-room run existed:

        exact      PICP, coverage, counts, ids, levels, gamma, crossing counts, any integer
        tight      MPIW, Winkler and every width/efficiency statistic      relative <= 1e-12
        declared   bootstrap CI bounds and p-values                        relative <= 1e-9
        not gated  figures — regenerated and eyeballed, never hashed

     Those numbers are not guesses. `05_results/tables/2026-09-04-determinism-probe.csv` measured this
     pipeline's floor: PICP is bit-exact across a repeat and across thread counts, and widths agree to
     2.2e-16 relative. 1e-12 leaves four orders of headroom. LESSONS_LOG A13 records that the term the
     tolerance CANNOT absorb is a library-version difference (~1e-3 in PICP), which is why the exact `==`
     lock file, not this tolerance, is what makes a clean room reproduce.

  C. FAIL CLOSED.  Any artifact present under the scanned roots but ABSENT from the manifest is a
     FAILURE, not a shrug. D-020 leaves F1' and F2' to be regenerated in R-Phase 7, so the manifest
     carries a `phase` column and this check is what will force it to be re-cut then rather than
     silently going stale.

Exit status: 0 only if every check passes.

Usage:
    python 03_code/verify.py                # verify
    python 03_code/verify.py --smoke        # verify only what exists (for a partial run)
    python 03_code/verify.py --build        # cut the manifest and populate 05_results/reference/
"""
from __future__ import annotations
import argparse, csv, hashlib, sys
from pathlib import Path

p = Path(__file__).resolve()
while p != p.parent and not (p / "01_data").is_dir():
    p = p.parent
ROOT = p
MANIFEST = ROOT / "00_admin" / "2026-09-04-shipped-outputs" / "MANIFEST-outputs.csv"
REFDIR = ROOT / "05_results" / "reference"
TABLES = ROOT / "05_results" / "tables"

# Roots scanned by phase C. Anything here must be in the manifest.
SCAN = [
    ("01_data/processed", "input"),
    ("03_code/src", "code"),
    ("03_code/tests", "code"),
    ("05_results/reference", "reference"),
    ("05_results/figures", "figure"),
]
# Individually listed because they are not inside a scanned directory. The lock file above all:
# it is the artifact that makes a clean room reproduce (LESSONS_LOG A13), so it must be hashed.
SCAN_FILES = [
    ("03_code/verify.py", "code"),
    ("03_code/2026-09-04-requirements.lock.txt", "code"),
    ("03_code/2026-09-04-environment.yml", "code"),
    ("03_code/2026-09-04-Dockerfile", "code"),
    ("03_code/2026-09-04-build-lockfile.py", "code"),
    ("03_code/2026-09-04-build-package.py", "code"),
    # 2026-09-05 (revision 45): the unstable-cell registry and the script that GENERATES it are hash-locked
    # here, so the one mechanism in this verifier that can excuse a difference cannot itself be edited
    # without the manifest noticing. A listed file that is absent is skipped, not failed, so this is safe
    # in layouts that do not ship the generator.
    ("03_code/2026-09-05-build-unstable-cells.py", "code"),
    ("00_admin/2026-09-05-unstable-cells.csv", "doc"),
    ("run_all.sh", "code"),
    ("CITATION.cff", "doc"),
    ("01_data/2026-09-04-DATA-DICTIONARY-processed.md", "doc"),
    ("06_manuscript/CTR/replication/2026-09-04-README.md", "doc"),
    ("06_manuscript/CTR/replication/2026-09-04-REPLICATION.md", "doc"),
    ("06_manuscript/CTR/replication/2026-09-04-USER_ACTIONS.md", "doc"),
    # The same documents under the names they carry INSIDE the shipped package. Whichever layout this
    # file finds itself in, one spelling resolves and the other is reported as skipped, so a document
    # is never silently unhashed.
    ("README.md", "doc"),
    ("REPLICATION.md", "doc"),
    ("USER_ACTIONS.md", "doc"),
    ("LICENSE", "doc"),
    ("BUILD-INFO.txt", "doc"),
    ("01_data/DATA_DICTIONARY.md", "doc"),
    ("01_data/DATA_DICTIONARY-raw-provenance.md", "doc"),
    ("04_experiments/EXPERIMENTS_LOG.md", "doc"),
]

IGNORE_PARTS = {"__pycache__", "_retired", "_superseded", "_provenance-not-used", "eq", ".ipynb_checkpoints"}
IGNORE_SUFFIX = {".pyc", ".pyo", ".ini"}

EXACT_HINTS = ("picp", "n_test", "n_cal", "n_cal_b", "facility_id", "level", "gamma", "dynamic",
               "count", "n_crossings", "horizon", "method", "city", "dataset", "seed", "step",
               "frac", "n_facilities", "n_obs", "k_", "phase")
DECLARED_HINTS = ("ci_lo", "ci_hi", "_p", "p_value", "pval", "paired_p", "holm", "boot")
TOL = {"exact": 0.0, "tight": 1e-12, "declared": 1e-9}


def sha256(f: Path) -> str:
    h = hashlib.sha256()
    with f.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def interesting(f: Path) -> bool:
    if not f.is_file():
        return False
    if set(f.parts) & IGNORE_PARTS or f.suffix in IGNORE_SUFFIX or f.name.startswith("."):
        return False
    return True


def column_class(name: str) -> str:
    n = name.lower()
    if any(h in n for h in DECLARED_HINTS):
        return "declared"
    if any(h in n for h in EXACT_HINTS):
        return "exact"
    return "tight"


UNSTABLE_LIST = ROOT / "00_admin" / "2026-09-05-unstable-cells.csv"


def unstable_rules(fname: str) -> list:
    """Cells MEASURED to be nondeterministic across processes, with every observed value recorded.

    Branch S applied to a CELL rather than to a whole artifact. The 58 never-regenerated reference tables
    are reported with a stated reason instead of as failures; this does the same for a cell that a
    from-scratch run legitimately reproduces at either of two values, so a replicator is not told that a
    property of the method is a defect in their environment.

    THIS IS NOT A RELAXED TOLERANCE, and three guards keep that true: a registered cell is excused only
    when its value equals one of the recorded values, so a THIRD value is still a failure; a column in the
    `exact` class is never excused, which keeps PICP gated (it is identical across every observation, and
    that is why the instability is reportable at all); and an unregistered cell that differs still fails.
    The registry is generated by `03_code/2026-09-05-build-unstable-cells.py` from an append-only probe,
    never typed, so it cannot quietly acquire a cell that should have been reproducible.
    """
    if not UNSTABLE_LIST.exists():
        return []
    out = []
    with UNSTABLE_LIST.open() as fh:
        for r in csv.DictReader(fh):
            if (r.get("file") or "").strip() != fname:
                continue
            out.append(dict(match=dict(kv.split("=", 1) for kv in r["match"].split(";") if kv),
                            column=r["column"].strip(),
                            values=[float(v) for v in r["observed_values"].split("|")]))
    return out


def compare_csv(gen: Path, ref: Path):
    """Cell-by-cell comparison under the tolerance table. Returns a list of failure strings."""
    import pandas as pd, numpy as np
    a = pd.read_csv(gen)
    b = pd.read_csv(ref)
    if list(a.columns) != list(b.columns):
        return [f"column mismatch: generated {list(a.columns)} vs reference {list(b.columns)}"]
    if len(a) != len(b):
        return [f"row count {len(a)} vs reference {len(b)}"]

    # Align on identity columns before comparing. Row ORDER is not part of a reproduction claim: the
    # runner may produce a file's arms in a different order from the order they were originally
    # generated in (it does — the E3 table's two arms come out A3-then-A12 from run_all.sh and
    # A12-then-A3 in the archived file), and a positional comparison would report every cell as
    # different. Identity columns are the categorical and integer ones plus the level/horizon labels;
    # measured floats are never used as a sort key, so a tiny numeric difference cannot reorder rows
    # and cascade into spurious failures.
    key = [c for c in a.columns
           if a[c].dtype == object or pd.api.types.is_integer_dtype(a[c])
           or c.lower() in ("level", "horizon", "facility_id", "fold")]
    key = [c for c in key if a[c].notna().all() and b[c].notna().all()]
    if key:
        a = a.sort_values(key, kind="mergesort").reset_index(drop=True)
        b = b.sort_values(key, kind="mergesort").reset_index(drop=True)

    fails = []
    rules = unstable_rules(gen.name)
    n_known = 0
    for col in a.columns:
        cls = column_class(col)
        x, y = a[col], b[col]
        if x.dtype.kind in "fi" and y.dtype.kind in "fi":
            xv = x.to_numpy(dtype=float); yv = y.to_numpy(dtype=float)
            both_nan = np.isnan(xv) & np.isnan(yv)
            d = np.where(both_nan, 0.0, np.abs(xv - yv))
            with np.errstate(divide="ignore", invalid="ignore"):
                rel = np.where(np.abs(yv) > 0, d / np.abs(yv), d)
            rel = np.where(both_nan, 0.0, rel)
            bad = np.isnan(rel) | (rel > TOL[cls])
            if bad.any() and cls != "exact" and rules:
                excused = np.zeros(len(a), dtype=bool)
                for rule in rules:
                    if rule["column"] != col:
                        continue
                    sel = np.ones(len(a), dtype=bool)
                    for k, v in rule["match"].items():
                        if k not in a.columns:
                            sel[:] = False
                            break
                        sel &= (a[k].astype(str).str.strip() == v)
                    if not sel.any():
                        continue
                    near = np.zeros(len(a), dtype=bool)
                    for val in rule["values"]:
                        near |= np.isclose(xv, val, rtol=1e-12, atol=0.0)
                    excused |= sel & near & bad
                if excused.any():
                    n_known += int(excused.sum())
                    bad = bad & ~excused
            if bad.any():
                i = int(np.argmax(np.nan_to_num(rel, nan=np.inf)))
                fails.append(f"{col} [{cls}, tol {TOL[cls]:.0e}]: {int(bad.sum())} cell(s) differ; "
                             f"worst row {i}: {xv[i]!r} vs {yv[i]!r} (rel {rel[i]:.3e})")
        else:
            neq = (x.astype(str) != y.astype(str))
            if neq.any():
                i = int(neq.to_numpy().argmax())
                fails.append(f"{col} [exact, non-numeric]: {int(neq.sum())} cell(s) differ; "
                             f"row {i}: {x.iloc[i]!r} vs {y.iloc[i]!r}")
    if n_known:
        print(f"[verify] {n_known} known-unstable cell(s) in {gen.name} matched a recorded value — "
              f"expected; see 00_admin/2026-09-05-unstable-cells.csv for the mechanism")
    return fails


# ---------------------------------------------------------------------------------------------
def build():
    import shutil
    REFDIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists():
        sys.exit(f"[verify] REFUSING to overwrite {MANIFEST.name} — supersede by date instead.")

    n_copied = 0
    for t in sorted(TABLES.glob("*.csv")):
        if set(t.parts) & IGNORE_PARTS:
            continue
        dst = REFDIR / t.name
        if not dst.exists():
            shutil.copy2(t, dst); n_copied += 1
    print(f"[verify] populated 05_results/reference/ with {n_copied} table(s)")

    rows = []
    for rel, role in SCAN:
        base = ROOT / rel
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if not interesting(f):
                continue
            r = f.relative_to(ROOT).as_posix()
            cls = "not_gated" if role == "figure" else ("exact_hash" if role in ("input", "code") else "tolerance")
            rows.append(dict(path=r, role=role, sha256=sha256(f), bytes=f.stat().st_size,
                             tolerance_class=cls, phase="R6", producer_script="", claim="", notes=""))
    for rel, role in SCAN_FILES:
        f = ROOT / rel
        if not f.exists():
            print(f"[verify] NOTE: listed file absent at build time, skipped: {rel}")
            continue
        rows.append(dict(path=rel, role=role, sha256=sha256(f), bytes=f.stat().st_size,
                         tolerance_class="exact_hash", phase="R6", producer_script="",
                         claim="", notes=""))
    with MANIFEST.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"[verify] wrote {MANIFEST.relative_to(ROOT)} with {len(rows)} entries")
    print("[verify] NOTE: figures (F1'/F2' included, regenerated on the excluded base in revision 48) are listed not_gated.")


# 2026-09-05 (revision 44, EXP-035): BRANCH S of the R-Phase 6 prespecification, implemented.
# `05_results/reference/` holds 121 tables; a complete from-scratch run regenerates 63 of them. The other
# 58 are ARCHIVED -- pre-rejection and pre-audit artifacts, diagnostics that are deliberately not runner
# steps, and three files produced ad hoc in earlier stages that have no writer anywhere in the tree.
# Before this, phase B reported every one of them as a FAILURE ("reference exists, generated file does
# not"), so a replicator following the package saw 58 failures that were not defects. The prespecification
# already decided this class: list it with `provenance = unreproducible` and a stated reason, rather than
# pretending it is regenerated. `00_admin/2026-09-05-archived-artifacts.csv` carries the list with one
# reason per file, and it was GENERATED from a complete clean-room run rather than typed, so it cannot
# quietly acquire a file that should have been regenerated.
# The guard that keeps this honest: an archived artifact that IS regenerated is compared normally, and a
# NON-archived reference that is missing is still a failure.
ARCHIVED_LIST = ROOT / "00_admin" / "2026-09-05-archived-artifacts.csv"


def archived_set() -> set:
    if not ARCHIVED_LIST.exists():
        return set()
    with ARCHIVED_LIST.open() as fh:
        return {r["path"].rsplit("/", 1)[-1] for r in csv.DictReader(fh)}

def verify(smoke: bool):
    if not MANIFEST.exists():
        sys.exit(f"[verify] manifest missing: {MANIFEST}. Run with --build first.")
    listed = {}
    with MANIFEST.open() as fh:
        for r in csv.DictReader(fh):
            listed[r["path"]] = r

    fails, checked, skipped = [], 0, 0

    # --- A. integrity -------------------------------------------------------------------
    for path, r in listed.items():
        f = ROOT / path
        if not f.exists():
            (skipped := skipped) if smoke else fails.append(f"A MISSING  {path}")
            if smoke:
                skipped += 1
            continue
        if r["tolerance_class"] == "not_gated":
            checked += 1
            continue
        got = sha256(f)
        checked += 1
        if got != r["sha256"]:
            if r["role"] == "reference":
                fails.append(f"A CHANGED  {path} — a shipped reference must not be edited")
            else:
                fails.append(f"A CHANGED  {path} — sha256 {got[:12]}… != manifest {r['sha256'][:12]}…")

    # --- B. reproduction ----------------------------------------------------------------
    archived = archived_set()
    n_archived = 0
    for path, r in listed.items():
        if r["role"] != "reference":
            continue
        ref = ROOT / path
        gen = TABLES / Path(path).name
        if not gen.exists():
            if gen.name in archived:
                n_archived += 1            # branch S: no live producer, provenance stated. NOT a failure.
            elif smoke:
                skipped += 1
            else:
                fails.append(f"B NOTRUN   {gen.relative_to(ROOT)} — reference exists, generated file does not")
            continue
        if not ref.exists():
            continue
        for msg in compare_csv(gen, ref):
            fails.append(f"B DIFFERS  {gen.relative_to(ROOT)} :: {msg}")
        checked += 1

    if n_archived:
        print(f"[verify] {n_archived} archived reference table(s) not regenerated — expected; see "
              f"00_admin/2026-09-05-archived-artifacts.csv for the per-file reason")

    # --- C. fail closed -----------------------------------------------------------------
    for rel, role in SCAN:
        base = ROOT / rel
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if not interesting(f):
                continue
            r = f.relative_to(ROOT).as_posix()
            if r not in listed:
                fails.append(f"C UNLISTED {r} — present in the tree, absent from the manifest")

    print(f"[verify] manifest entries: {len(listed)}; checks performed: {checked}; "
          f"skipped (smoke): {skipped}")
    if fails:
        print(f"[verify] FAILURES: {len(fails)}")
        for m in fails[:60]:
            print("   ", m)
        if len(fails) > 60:
            print(f"    … and {len(fails)-60} more")
        print("[verify] FAIL")
        return 1
    print("[verify] PASS — every listed artifact matches, and nothing is unlisted.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.build:
        build(); return 0
    return verify(a.smoke)


if __name__ == "__main__":
    sys.exit(main())
