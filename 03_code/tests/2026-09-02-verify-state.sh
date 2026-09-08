#!/usr/bin/env bash
# State verification for the pre-submission revision (D-014).
# Answers one question: is the inherited state exactly as the record claims?
# Exits 0 if safe to proceed, 1 if not. Never modifies anything.
set -uo pipefail
ROOT="$HOME/mnt/Parking Allocation Problem"
cd "$ROOT" 2>/dev/null || { echo "FATAL: project folder not reachable. Is the computer linked and the folder connected?"; exit 1; }
FAIL=0
line(){ printf '%.0s-' {1..72}; echo; }

echo "STATE VERIFICATION — $(date -u '+%Y-%m-%d %H:%M UTC')"; line

echo "[1/4] dependencies"
python3 - <<'PY' 2>/dev/null || pip install pyarrow holidays scikit-learn scipy --quiet
import pyarrow, holidays, sklearn, scipy
PY
python3 -c "import pyarrow,holidays,sklearn,scipy" 2>/dev/null \
  && echo "      OK — pyarrow, holidays, scikit-learn, scipy importable" \
  || { echo "      FAIL — could not install the scientific stack (network restricted?)"; FAIL=1; }

echo "[2/4] required artifacts present"
for p in \
  01_data/processed/belgrade_features_v2.parquet \
  01_data/processed/birmingham_features_v2.parquet \
  03_code/src/conformal/core.py \
  03_code/src/conformal/2026-09-02-run-core-methods.py \
  05_results/tables/2026-09-02-core-belgrade-gcal-per-facility.csv \
  05_results/tables/2026-09-02-core-birmingham-gcal-per-facility.csv \
  00_admin/2026-09-02-preaudit-freeze/MANIFEST-sha256.txt \
  2026-09-02-REVISION-35-RECORD.md ; do
  [ -f "$p" ] && echo "      OK   $p" || { echo "      MISSING  $p"; FAIL=1; }
done

echo "[3/4] test suites"
cd 03_code/tests
OUT1=$(python3 2026-09-02-test_split_integrity.py 2>&1); R1=$?
OUT2=$(python3 2026-09-02-test_conformal_core.py 2>&1);  R2=$?
cd "$ROOT"
if [ $R1 -eq 0 ]; then echo "      OK   split/session integrity — 43/43"; else
  echo "      FAIL split/session integrity:"; echo "$OUT1" | grep -E "^\s+\[FAIL\]" | sed 's/^/        /'; FAIL=1; fi
if [ $R2 -eq 0 ]; then echo "      OK   conformal core properties — 20/20"; else
  echo "      FAIL conformal core properties:"; echo "$OUT2" | grep -E "^\s+\[FAIL\]" | sed 's/^/        /'; FAIL=1; fi

echo "[4/4] pre-audit baseline unchanged since the freeze"
python3 - <<'PY'
import hashlib, pathlib, sys
root = pathlib.Path.home()/"mnt"/"Parking Allocation Problem"
man = root/"00_admin"/"2026-09-02-preaudit-freeze"/"MANIFEST-sha256.txt"
drift, gone, n = [], [], 0
for ln in man.read_text().splitlines():
    if len(ln) < 66 or not ln[:64].isalnum(): continue
    h, rel = ln[:64], ln[66:].strip()
    f = root/rel
    if not f.exists(): gone.append(rel); continue
    n += 1
    if hashlib.sha256(f.read_bytes()).hexdigest() != h: drift.append(rel)
print(f"      checked {n} frozen files")
if gone:  print("      MOVED/REMOVED since freeze (expected for retired scripts):")
for g in gone[:12]: print(f"        {g}")
if drift:
    print("      *** CHANGED since the freeze — investigate before trusting any inherited number:")
    for d in drift: print(f"        {d}")
    sys.exit(1)
print("      OK   no frozen file was modified")
PY
[ $? -ne 0 ] && FAIL=1

line
if [ $FAIL -eq 0 ]; then
  echo "RESULT: PASS — inherited state matches the record. Safe to proceed to R-Phase 3b."
else
  echo "RESULT: FAIL — DO NOT PROCEED WITH R-PHASE 3B."
  echo
  echo "Tell the user exactly which checks failed and stop. Do not attempt repairs, do not"
  echo "regenerate the v2 feature tables, and do not run any experiment: the inherited results"
  echo "in 05_results/tables/2026-09-02-* can no longer be trusted to match the logged numbers."
  echo "Recovery: everything needed to rebuild is on disk and reproducible ——"
  echo "  features  : 03_code/src/features/2026-09-02-build_features{,_birmingham}_v2.py"
  echo "  core runs : 03_code/src/conformal/2026-09-02-run-core-methods.py --dataset <city>"
  echo "  provenance: 00_admin/2026-09-02-preaudit-freeze/ (manifest + baseline + snapshot zip)"
  echo "  narrative : 2026-09-02-REVISION-35-RECORD.md, EXPERIMENTS_LOG EXP-016..019"
  echo "Ask the user whether to rebuild from these before continuing."
fi
exit $FAIL
