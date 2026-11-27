#!/usr/bin/env python3
"""
EXP-045 arm A10 (T030), 2026-11-25: the sparse-group fallback of
`core.grouped_adaptive_conformal_stream` must use each own score ONCE.

The fallback pool of a group with fewer than `min_group` own scores is the own scores plus the other
groups' scores. Before the fix the function built `own + global_pool`, and `global_pool` (the default,
and every caller's `resid`) already holds the own scores, so they entered twice.

  F1  n_init of a sparse group equals the total pooled count (own once), with the explicit pool
  F2  the same with the default pool (global_pool=None)
  F3  the sparse group's first half-width equals the conformal quantile of the pooled scores taken
      once; the data are built so that a doubled own pool gives a different (larger) quantile
  F4  dense groups are untouched: their first half-width is their own pool's quantile
  F5  a global_pool that lacks the own scores is refused (ValueError), never silently extended

Control: run against the pre-T030 core.py (`--core <path> --expect-fail`); F1, F2, F3 and F5 must fail.
Run: python 2026-11-25-test-grouped-fallback.py [--core PATH] [--expect-fail]
"""
from __future__ import annotations
import argparse, importlib.util, sys
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--core", default=str(Path(__file__).resolve().parents[1] / "src" / "conformal" / "core.py"))
ap.add_argument("--expect-fail", action="store_true", help="control mode: exit 0 only if a check fails")
args = ap.parse_args()
spec = importlib.util.spec_from_file_location("core_under_test", args.core)
core = importlib.util.module_from_spec(spec); sys.modules[spec.name] = core; spec.loader.exec_module(core)
print(f"core under test: {args.core}")

FAIL = []
def check(name, cond, detail=""):
    ok = bool(cond)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not ok: FAIL.append(name)

rng = np.random.default_rng(20261125)
ALPHA, H, MIN_GROUP = 0.10, 3, 50
small_a = np.abs(rng.normal(0, 3, 200))
small_b = np.abs(rng.normal(0, 3, 200))
sparse_c = 50.0 + np.arange(30, dtype=float)         # 30 large own scores, below min_group
pools = {"a": small_a, "b": small_b, "c": sparse_c}
allpool = np.concatenate([small_a, small_b, sparse_c])   # 430 scores, each once
n = 300
grp = np.array(["a", "b", "c"])[rng.integers(0, 3, n)]
cen = rng.normal(50, 5, n); y = cen + rng.normal(0, 3, n)

q_once = core.conformal_quantile(allpool, ALPHA)
q_twice = core.conformal_quantile(np.concatenate([sparse_c, allpool]), ALPHA)
print(f"  design: quantile of pooled scores once = {q_once:.6f}, with own doubled = {q_twice:.6f}")
assert q_once != q_twice, "test design must separate the two pools"

def first_half_width(lo, hi, gk):
    i = int(np.flatnonzero(grp == gk)[0])
    return (hi[i] - lo[i]) / 2.0

# F1 explicit pool (what every caller passes: resid = all calibration scores)
lo1, hi1, d1 = core.grouped_adaptive_conformal_stream(
    pools, grp, cen, cen, y, ALPHA, H, gamma=0.05, global_pool=allpool, min_group=MIN_GROUP,
    clip_low=None, return_state=True)
gi = d1["group_init"]["c"]
check("F1 sparse group, explicit pool: n_init = own once + others", gi["fell_back"] and gi["n_init"] == 430,
      f"n_own={gi['n_own']}, n_init={gi['n_init']} (430 expected; 460 means own counted twice)")
# F2 default pool
lo2, hi2, d2 = core.grouped_adaptive_conformal_stream(
    pools, grp, cen, cen, y, ALPHA, H, gamma=0.05, min_group=MIN_GROUP, clip_low=None, return_state=True)
gi2 = d2["group_init"]["c"]
check("F2 sparse group, default pool: n_init = own once + others", gi2["fell_back"] and gi2["n_init"] == 430,
      f"n_init={gi2['n_init']}")
# F3 the quantile actually used
got = first_half_width(lo1, hi1, "c")
check("F3 sparse group opens on the quantile of the pooled scores taken once", abs(got - q_once) < 1e-12,
      f"first half-width {got:.6f}; once {q_once:.6f}, doubled {q_twice:.6f}")
# F4 dense groups untouched
ok4 = all(abs(first_half_width(lo1, hi1, k) - core.conformal_quantile(pools[k], ALPHA)) < 1e-12 for k in "ab")
check("F4 dense groups open on their own pool's quantile (fallback does not touch them)", ok4)
# F5 a pool without the own scores is refused
try:
    core.grouped_adaptive_conformal_stream(pools, grp, cen, cen, y, ALPHA, H, gamma=0.05,
                                           global_pool=np.concatenate([small_a, small_b]),
                                           min_group=MIN_GROUP)
    raised = False
except ValueError:
    raised = True
check("F5 a global_pool lacking the own scores raises ValueError", raised)

n_checks = 5
print(f"{n_checks - len(FAIL)} of {n_checks} checks passed")
if args.expect_fail:
    print("CONTROL: " + ("DETECTED (the core under test fails, as required)" if FAIL else "NOT DETECTED"))
    sys.exit(0 if FAIL else 1)
sys.exit(1 if FAIL else 0)
