#!/usr/bin/env bash
# =====================================================================================
# ONE-COMMAND REPRODUCTION — parking conformal-prediction replication package
# R-Phase 6 (audit issues R02, R03, X02). Replaces the 2026-08-04 runner, which is
# retired in 06_manuscript/CTR/replication/_superseded/ with a README saying why.
#
# WHAT WAS WRONG WITH THE OLD ONE, so it is not reintroduced:
#   * `set -e` with NO `pipefail`, and eight `until python … | grep -q "ALL DONE"; do :; done`
#     loops: a persistently failing step spun forever and the pipe swallowed the traceback.
#   * It never invoked the base-learner or figure scripts, while the README claimed the
#     package reproduced "every table and figure".
#   * Its last step was the allocation vignette — an experiment that is now dead (EXP-029).
#
# THIS RUNNER:
#   * `set -euo pipefail`, so a failure anywhere stops the run with a nonzero exit.
#   * BOUNDED retries. Every resumable step gets at most $MAX_ITERS iterations and then
#     fails loudly. It never loops forever.
#   * Per-step logs under 07_logs/, via `tee`, with the exit status recorded.
#   * Every step wired in, including figures and the verifier.
#   * `--smoke` runs a bounded subset end to end, for checking the runner itself.
#   * `--from STEP` / `--only STEP` to resume without redoing completed work.
#
# Usage:
#   bash run_all.sh                 # full reproduction (hours; every step is resumable)
#   bash run_all.sh --smoke         # bounded end-to-end check of the runner
#   bash run_all.sh --list          # print the step list and exit
#   bash run_all.sh --from core     # resume from a named step
#   bash run_all.sh --only verify   # run one step
# =====================================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
CONF="03_code/src/conformal"
LOGS="$ROOT/07_logs"
mkdir -p "$LOGS"
export PYTHONDONTWRITEBYTECODE=1          # LESSONS_LOG A12

PY="${PYTHON:-python3}"
MAX_ITERS="${MAX_ITERS:-200}"             # hard ceiling on any resumable step
BUDGET="${BUDGET:-150}"                   # seconds per invocation (LESSONS_LOG A1)
SMOKE=0; FROM=""; ONLY=""; LIST=0

while [ $# -gt 0 ]; do
  case "$1" in
    --smoke) SMOKE=1; shift ;;
    --list)  LIST=1; shift ;;
    --from)  FROM="${2:?--from needs a step name}"; shift 2 ;;
    --only)  ONLY="${2:?--only needs a step name}"; shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

STEPS=(env core e3 tod trust baselearner orthogonal folds rolling delay
       x08 inference vignette rphase5 c01 relalloc display exp037 spatial figures verify)

if [ "$LIST" = 1 ]; then printf '%s\n' "${STEPS[@]}"; exit 0; fi

started=0
want () {                                  # should this step run?
  local s="$1"
  if [ -n "$ONLY" ]; then [ "$s" = "$ONLY" ]; return; fi
  if [ -n "$FROM" ]; then
    [ "$s" = "$FROM" ] && started=1
    [ "$started" = 1 ]; return
  fi
  return 0
}

say () { printf '\n== %s ==\n' "$*"; }

# run <step> <label> <cmd...>            — a single-shot step
run () {
  local step="$1" label="$2"; shift 2
  want "$step" || return 0
  say "$label"
  local log="$LOGS/${step}.log"
  if ! "$@" 2>&1 | tee "$log"; then
    echo "FAILED: step '$step' — see $log" >&2
    exit 1
  fi
  # `set -o pipefail` makes the above catch the python exit code, not tee's.
}

# resume <step> <label> <cmd...>         — a resumable step; loops until ALL DONE, BOUNDED
resume () {
  local step="$1" label="$2"; shift 2
  want "$step" || return 0
  say "$label"
  local log="$LOGS/${step}.log" i=0
  : > "$log"
  while :; do
    i=$((i+1))
    if [ "$i" -gt "$MAX_ITERS" ]; then
      echo "FAILED: step '$step' did not finish in $MAX_ITERS iterations — see $log" >&2
      exit 1
    fi
    # Stream to the log AS IT RUNS. An earlier version captured the output in a command
    # substitution and wrote it afterwards, which meant a long step killed by an external timeout
    # left an EMPTY log — the one case where you most want to see progress.
    local tmp="$log.iter"
    if ! "$@" > >(tee -a "$log" > "$tmp") 2>&1; then
      echo "FAILED: step '$step' exited nonzero on iteration $i — see $log" >&2
      exit 1
    fi
    wait
    local out; out="$(cat "$tmp")"; rm -f "$tmp"
    printf '%s\n' "$out" | tail -1
    if printf '%s' "$out" | grep -q "ALL DONE"; then break; fi
    if ! printf '%s' "$out" | grep -q "REMAINING"; then
      echo "FAILED: step '$step' printed neither ALL DONE nor REMAINING — see $log" >&2
      exit 1
    fi
  done
}

SM=""; [ "$SMOKE" = 1 ] && SM="--smoke"

# --- 0. environment ------------------------------------------------------------------
run env "Environment lock check (R01)" \
    bash 03_code/tests/2026-09-03-verify-state.sh deps

# --- 1. core conformal methods (Tables 2-3 inputs, ESM S4) ---------------------------
for ds in belgrade birmingham; do
  resume core "Core methods — $ds" \
      $PY "$CONF/2026-09-02-run-core-methods.py" --dataset "$ds" --budget "$BUDGET"
done

# --- 2. E3 baselines: EnbPI / AgACI-style / NGBoost (Table 2) ------------------------
# BOTH arms. A3_v2_daychunk is the reported configuration; A12_v1_paired runs both chunking
# schemes on ONE fitted model per facility and is what makes the C07 protocol delta attributable
# (D-017), i.e. row 1 of T6. Omitting it was the defect the clean-room gate caught in this very
# runner on its first full pass — the same class as audit issue X02, which is what this file exists
# to fix, so it is wired in explicitly rather than left to the script's default.
for ds in belgrade birmingham; do
  for arm in A3_v2_daychunk A12_v1_paired; do
    resume e3 "E3 baselines — $ds, arm $arm" \
        $PY "$CONF/2026-09-03-e3-baselines.py" --dataset "$ds" --arm "$arm" --budget "$BUDGET"
  done
done

# --- 3. conditional coverage, trust/abstain, robustness ------------------------------
resume tod         "Time-of-day conditional coverage (Table 4)" \
    $PY "$CONF/2026-09-03-tod-conditional.py" --budget "$BUDGET"
resume trust       "Trust / abstain with matched control (Table 5)" \
    $PY "$CONF/2026-09-03-trust-abstain.py" --budget "$BUDGET"
resume baselearner "Base-learner robustness (ESM) — the step the old runner never ran (X02)" \
    $PY "$CONF/2026-09-03-base-learner-robustness.py" --budget "$BUDGET"

# --- 4. orthogonal partition and folds ------------------------------------------------
resume orthogonal "Orthogonal partition check" \
    $PY "$CONF/2026-09-03-orthogonal-partition-check.py" --budget "$BUDGET"
for arm in A_folds B_bham_coarse C_bham_hour; do
  resume folds "Orthogonal folds — arm $arm (EXP-028)" \
      $PY "$CONF/2026-09-04-orthogonal-folds-birmingham.py" --arm "$arm" --budget "$BUDGET"
done
run    folds      "Birmingham orthogonal folds — summary" \
    $PY "$CONF/2026-09-04-orthogonal-5b-summary.py"

# --- 5. rolling origin and delay sensitivity -----------------------------------------
resume rolling "Rolling-origin folds" \
    $PY "$CONF/2026-09-03-rolling-origin.py" --budget "$BUDGET"
run    rolling "Rolling-origin inference" \
    $PY "$CONF/2026-09-03-rolling-origin-inference.py"
# 2026-09-05 (revision 44, EXP-035): TWO defects fixed here, both lesson C11 -- what a runner omits is
# an ARM, not a script. (1) The script takes its city from the CITY ENVIRONMENT VARIABLE and defaults to
# belgrade, so the runner never produced `2026-09-02-delay-sensitivity-birmingham.csv` at all. (2) It
# takes `--facilities`, default 10, but the logged Belgrade table was cut at **8** facilities and the
# logged Birmingham table at **10**; passing neither made a from-scratch run emit 210 Belgrade rows
# against the reference's 168. The logged populations are pinned here so the runner reproduces the
# numbers EXP-018 actually quotes -- changing the population to the default would silently move a logged
# figure (2.88 -> 2.68 coverage points at h=6) for no scientific reason (B25).
run delay "Delay sensitivity — belgrade (logged population: 8 facilities)" \
    env CITY=belgrade $PY "$CONF/2026-09-02-delay-sensitivity.py" --facilities 8
run delay "Delay sensitivity — birmingham (logged population: 10 facilities)" \
    env CITY=birmingham $PY "$CONF/2026-09-02-delay-sensitivity.py" --facilities 10

# --- 6. X08 low-information exclusion, applied by re-aggregation (D-018) --------------
# `--filter off` FIRST: it is the negative control and must reproduce the logged summaries before any
# filtered number is read (B17, the EXP-027 pattern). Then `--filter on` produces the published base.
run x08 "X08 exclusion — negative control (filter OFF, must reproduce the logged summaries)" \
    $PY "$CONF/2026-09-04-x08-reaggregate.py" --filter off
run x08 "X08 exclusion — re-aggregate on the published base (filter ON)" \
    $PY "$CONF/2026-09-04-x08-reaggregate.py" --filter on
run x08 "X08 exclusion — before/after table" \
    $PY "$CONF/2026-09-04-x08-before-after.py"
run x08 "X08 exclusion — orthogonal excess" \
    $PY "$CONF/2026-09-04-x08-orthogonal-excess.py"

# --- 7. two-level inference (T3'; EXP-030) -------------------------------------------
run inference "Two-level inference — gate first (filter OFF must reproduce the logged summary)" \
    $PY "$CONF/2026-09-04-phase4-inference.py" --filter off
run inference "Two-level inference — population and facility (T3', filter ON)" \
    $PY "$CONF/2026-09-04-phase4-inference.py" --filter on

# --- 8. the ESM null. NOT a vignette: EXP-029 killed that claim and D-019 replaced it -
resume vignette "ESM null — capacity proxy and seeds (inputs to the (A) table)" \
    $PY "$CONF/2026-09-04-allocation-vignette.py" --budget "$BUDGET"
run    vignette "ESM null — summary and capability table" \
    $PY "$CONF/2026-09-04-vignette-summary.py"

# --- 9. R-Phase 5 (EXP-031) ------------------------------------------------------------
run    rphase5 "R-Phase 5 — ESM capability table (A)" \
    $PY "$CONF/2026-09-04-rphase5-esm-capability.py" --overwrite
resume rphase5 "R-Phase 5 — failure case, legs 1 and 2" \
    $PY "$CONF/2026-09-04-rphase5-failure-case.py" --budget "$BUDGET"
resume rphase5 "R-Phase 5 — injection level sweep" \
    $PY "$CONF/2026-09-04-rphase5-level-sweep.py" --budget "$BUDGET"
run    rphase5 "R-Phase 5 — failure-case summary" \
    $PY "$CONF/2026-09-04-rphase5-failure-case-summary.py"
run    rphase5 "R-Phase 5 — D05 threshold sweep" \
    $PY "$CONF/2026-09-04-rphase5-d05-sweep.py" --overwrite

# --- 10. R-Phase 6: the C01 attribution (EXP-032) --------------------------------------
resume c01 "C01 attribution — published protocol (primary)" \
    $PY "$CONF/2026-09-04-c01-attribution.py" --gamma-mode calibrated --budget "$BUDGET"
resume c01 "C01 attribution — fixed gamma (mechanism check)" \
    $PY "$CONF/2026-09-04-c01-attribution.py" --gamma-mode fixed --budget "$BUDGET"

# --- 10b. D-019 (C): the relative-threshold allocation demonstration (EXP-034) ---------
# Wired in as three steps because phase `a` caches the per-facility panels OUTSIDE the tree
# (regenerable), `s0` measures the inputs and `run` scores the policies. Lesson C11: what a
# runner silently omits is an ARM, not a script -- all three are passed explicitly.
resume relalloc "Relative-threshold allocation - phase A (panel fits)" \
    $PY "$CONF/2026-09-05-relative-threshold-allocation.py" --phase a --budget "$BUDGET"
resume relalloc "Relative-threshold allocation - section 0 (inputs only)" \
    $PY "$CONF/2026-09-05-relative-threshold-allocation.py" --phase s0
resume relalloc "Relative-threshold allocation - policy run, 4 thetas x 20 seeds" \
    $PY "$CONF/2026-09-05-relative-threshold-allocation.py" --phase run --budget "$BUDGET" --seeds 20
run relalloc "Relative-threshold allocation - paired summary and gate" \
    $PY "$CONF/2026-09-05-rel-alloc-summary.py"

# --- 11. display items (D-020) ---------------------------------------------------------
run display "Display items — T3' and T6" \
    $PY "$CONF/2026-09-04-display-items.py"

# --- 11b. EXP-037, descriptive half (revision 48) ---------------------------------------
resume exp037 "EXP-037 pooled-vs-worst-facility, descriptive (two CSVs)" \
    $PY "$CONF/2026-09-06-exp037-pooled-vs-worst.py" --budget "$BUDGET"

# --- 12. spatial null and figures ------------------------------------------------------
# Both spatial scripts also write their printed statistics to 2026-09-06-spatial-statistics.csv (revision 48).
run spatial "Spatial analysis (null)" $PY 03_code/src/spatial/2026-09-05-spatial-analysis.py
run spatial "Spatial Mantel test"     $PY 03_code/src/spatial/2026-09-05-spatial-mantel.py
# Revision 49 (D-030): the spatial leg recomputed on the paper's evaluation base. Read-only re-aggregation of
# the two 2026-06-21 spatial tables -- no model is fitted -- so it runs in the `spatial` step after them.
run spatial "Spatial statistics on the evaluation base (D-030, revision 49)" \
    $PY 03_code/src/spatial/2026-09-07-spatial-exclusion-base.py
run figures "Framework figure"        $PY 03_code/src/viz/framework_figure.py
run figures "F1' / F2' on the X08-excluded base (D-020 items 7-8, revision 48)" \
    $PY 03_code/src/viz/2026-09-06-figures-f1-f2.py
run figures "ESM figures S1-S2 on the corrected bases (revision 49)" \
    $PY 03_code/src/viz/2026-09-07-figures-esm.py

# --- 13. verify everything against the manifest ---------------------------------------
run verify "Verify outputs against the manifest" $PY 03_code/verify.py $SM

echo
echo "ALL STEPS COMPLETED. Logs in 07_logs/. Verification report above."
