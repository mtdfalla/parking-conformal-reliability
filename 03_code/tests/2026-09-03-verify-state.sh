#!/usr/bin/env bash
# State verification — supersedes 2026-09-02-verify-state.sh.
#
# WHY THIS VERSION EXISTS: the 2026-09-02 script ran all four phases in ONE invocation and could not
# finish inside device_bash's ~120-180 s limit — the pip step alone exceeded it, and revision 36 burned
# three calls discovering that. This version takes a phase argument so every step fits the budget, and
# installs dependencies one package at a time (pyarrow is a 50 MB wheel and must not share a call with
# the rest). Run the phases in order; each prints its own PASS/FAIL.
#
#   bash 2026-09-03-verify-state.sh deps       # ~60 s, run twice if the first call times out
#   bash 2026-09-03-verify-state.sh artifacts  # instant
#   bash 2026-09-03-verify-state.sh tests      # ~90 s
#   bash 2026-09-03-verify-state.sh freeze     # ~20 s
#
# REVISION 38: `deps` no longer installs anything. It VERIFIES against the pinned EXP-025 lock and
# tells you to run 2026-09-03-restore-env.sh if something is missing. The previous version ran
# `pip install scikit-learn` UNPINNED, which would have silently installed whatever is current --
# precisely the hazard LESSONS_LOG A13 records as having ALREADY moved a published number here.
# Installation belongs in exactly one place (restore-env.sh, which pins and sha256-verifies);
# this script's job is to verify, and a verifier must never mutate what it verifies.
#
# Expected: 50 split-integrity checks, 48 conformal-core checks, 130 frozen files with zero drift.
# (split-integrity moved 36 -> 50 on 2026-09-04 with T10, the X08/B15 information check: 6 checks and
#  1 negative control per city. The gate is the exit code and a zero failure count; the totals below are
#  derived from the run and printed for information only -- never asserted (A9).)
# (Conformal core grew 27 -> 39 with P18-P21, the C07 batch-release gate, EXP-025; then
#  39 -> 48 with P22-P24 (nine checks), the X08 data-quality exclusion, revision 38 / D-018.)
# NOTE ON THE COUNTS: the 2026-09-02 script printed "43/43" for split-integrity as a HARDCODED string,
# not a measured count -- the suite actually emits 36 checks from 12 check() sites inside loops over
# horizons and cities. Revision 36 caught this. THE GATE IS THE EXIT CODE AND A ZERO [FAIL] COUNT; the
# totals below are informational and are derived here rather than asserted. Modifies nothing.
set -uo pipefail
ROOT="$HOME/mnt/Parking Allocation Problem"
cd "$ROOT" 2>/dev/null || { echo "FATAL: project folder not reachable."; exit 1; }
PHASE="${1:-all}"
line(){ printf '%.0s-' {1..72}; echo; }

if [ "$PHASE" = "deps" ] || [ "$PHASE" = "all" ]; then
  echo "[deps] VERIFYING the pinned stack (this phase installs nothing - see the header note)"
  python3 - <<'PY'
import sys
LOCK = {"numpy":"2.2.6","pandas":"2.3.3","scipy":"1.15.3","sklearn":"1.7.2",
        "pyarrow":"25.0.1","mapie":"1.5.0"}
EXTRA = ["ngboost","joblib","threadpoolctl","cloudpickle","holidays","matplotlib"]
missing, drift = [], []
for m in list(LOCK) + EXTRA:
    try:
        v = getattr(__import__(m), "__version__", "?")
    except Exception as e:
        missing.append(f"{m} ({type(e).__name__})"); continue
    if m in LOCK and v != LOCK[m]:
        drift.append(f"{m} {v} != pinned {LOCK[m]}")
if missing:
    print("  MISSING:", ", ".join(missing))
if drift:
    print("  VERSION DRIFT (this can move a published number -- LESSONS_LOG A13):")
    for d in drift: print("     ", d)
if missing or drift:
    print("  FAIL -- run:  bash 03_code/tests/2026-09-03-restore-env.sh")
    print("  Do NOT pip install by hand: restore-env.sh pins every version and sha256-verifies")
    print("  each wheel against the PyPI JSON API.")
    sys.exit(1)
print("  PASS -- scientific stack importable and every pinned version matches the EXP-025 lock")
PY
  [ $? -ne 0 ] && exit 1
fi

if [ "$PHASE" = "artifacts" ] || [ "$PHASE" = "all" ]; then
  echo "[artifacts] required inputs and R-Phase 3b outputs"; F=0
  for p in \
    01_data/processed/belgrade_features_v2.parquet \
    01_data/processed/birmingham_features_v2.parquet \
    03_code/src/conformal/core.py \
    03_code/src/conformal/2026-09-02-run-core-methods.py \
    03_code/src/conformal/2026-09-03-base-learner-robustness.py \
    03_code/src/conformal/2026-09-03-tod-conditional.py \
    03_code/src/conformal/2026-09-03-orthogonal-partition-check.py \
    03_code/src/conformal/2026-09-03-trust-abstain.py \
    05_results/tables/2026-09-02-core-belgrade-gcal-per-facility.csv \
    05_results/tables/2026-09-02-core-birmingham-gcal-per-facility.csv \
    05_results/tables/2026-09-03-base-learner-robustness.csv \
    05_results/tables/2026-09-03-tod-facility-bucket.csv \
    05_results/tables/2026-09-03-orthogonal-partition-summary.csv \
    05_results/tables/2026-09-03-trust-abstain-summary.csv \
    03_code/src/conformal/2026-09-03-e3-baselines.py \
    05_results/tables/2026-09-03-e3-belgrade-per-facility.csv \
    05_results/tables/2026-09-03-e3-birmingham-per-facility.csv \
    05_results/tables/2026-09-03-e3-summary.csv \
    00_admin/2026-09-02-preaudit-freeze/MANIFEST-sha256.txt ; do
    [ -f "$p" ] && echo "  OK   $p" || { echo "  MISSING  $p"; F=1; }
  done
  [ $F -eq 0 ] && echo "  PASS" || { echo "  FAIL"; exit 1; }
fi

if [ "$PHASE" = "tests" ] || [ "$PHASE" = "all" ]; then
  echo "[tests] property gates"
  cd 03_code/tests
  O1=$(python3 2026-09-02-test_split_integrity.py 2>&1); R1=$?
  O2=$(python3 2026-09-02-test_conformal_core.py  2>&1); R2=$?
  N1=$(echo "$O1" | grep -c "\[PASS\]"); N2=$(echo "$O2" | grep -c "\[PASS\]")
  cd "$ROOT"
  [ $R1 -eq 0 ] && echo "  OK   split/session integrity — $N1 checks passed, 0 failed (expect 50)" \
                || { echo "  FAIL split integrity:"; echo "$O1" | grep -E "\[FAIL\]"; exit 1; }
  [ $R2 -eq 0 ] && echo "  OK   conformal core — $N2 checks passed, 0 failed (expect 48)" \
                || { echo "  FAIL conformal core:"; echo "$O2" | grep -E "\[FAIL\]"; exit 1; }
  echo "  PASS"
fi

if [ "$PHASE" = "freeze" ] || [ "$PHASE" = "all" ]; then
  echo "[freeze] pre-audit baseline unchanged"
  python3 - <<'PY'
import hashlib, pathlib, sys
root = pathlib.Path.home()/"mnt"/"Parking Allocation Problem"
man = root/"00_admin"/"2026-09-02-preaudit-freeze"/"MANIFEST-sha256.txt"
drift, n = [], 0
for ln in man.read_text().splitlines():
    if len(ln) < 66 or not ln[:64].isalnum(): continue
    h, rel = ln[:64], ln[66:].strip(); f = root/rel
    if not f.exists(): continue
    n += 1
    if hashlib.sha256(f.read_bytes()).hexdigest() != h: drift.append(rel)
print(f"  checked {n} frozen files (expect 130)")
if drift:
    print("  *** CHANGED since the freeze — investigate before trusting any inherited number:")
    for d in drift: print(f"      {d}")
    sys.exit(1)
print("  PASS — no frozen file was modified")
PY
  [ $? -ne 0 ] && exit 1
fi

line; echo "PHASE '$PHASE' OK."
echo "If every phase passed, the inherited state matches the revision-36 record. Proceed."
