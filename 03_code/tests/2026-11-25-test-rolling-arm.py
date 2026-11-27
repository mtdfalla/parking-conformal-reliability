#!/usr/bin/env python3
"""
EXP-045 arm A1 (external-audit finding T005): test of the rolling-pool fixed-alpha arm.

The arm is `core.adaptive_conformal_stream(..., gamma=0.0)`. Three checks on synthetic data, each with a
control that must fail:
  R1  gamma = 0 keeps the working level at alpha on every step.      Control: gamma = 0.05 moves it.
  R2  with a horizon longer than the stream nothing is released, so RS-CP equals split-CP exactly.
                                                                       Control: horizon 1 does not.
  R3  with releases, the quantile at each step is the conformal quantile of the last `window` scores
      of (calibration scores + matured scores), recomputed here independently.
                                                                       Control: a pool that ignores the
                                                                       window is not equal.
Exit 0 and "[rolling-arm] PASS" when all three hold and all three controls fail.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "conformal"))
import core  # noqa: E402

rng = np.random.default_rng(20261125)
n_cal, n = 120, 400
cal = np.abs(rng.normal(0, 1, n_cal))
yhat = rng.normal(0, 1, n)
y = yhat + rng.normal(0, 1.3, n)      # a scale shift, so the levels would move if gamma were not 0
alpha, h = 0.10, 3
fails = []


def check(name, ok, control_ok):
    print(f"[rolling-arm] {name}: {'ok' if ok else 'FAIL'}; control {'fails as it must' if not control_ok else 'DID NOT FAIL'}")
    if not ok or control_ok:
        fails.append(name)


# R1
_, _, d0 = core.adaptive_conformal_stream(cal, yhat, yhat, y, alpha, h, gamma=0.0, return_state=True)
_, _, d5 = core.adaptive_conformal_stream(cal, yhat, yhat, y, alpha, h, gamma=0.05, return_state=True)
check("R1 level fixed at alpha", bool(np.all(d0["alpha"] == alpha)), bool(np.all(d5["alpha"] == alpha)))

# R2
lo_r, hi_r = core.adaptive_conformal_stream(cal, yhat, yhat, y, alpha, n + 1, gamma=0.0)
lo_s, hi_s = core.split_conformal_interval(cal, yhat, alpha)
lo_1, hi_1 = core.adaptive_conformal_stream(cal, yhat, yhat, y, alpha, 1, gamma=0.0)
check("R2 no release equals split-CP", bool(np.array_equal(lo_r, lo_s) and np.array_equal(hi_r, hi_s)),
      bool(np.array_equal(lo_1, lo_s) and np.array_equal(hi_1, hi_s)))

# R3
window = len(cal)
q_ref = np.empty(n); q_bad = np.empty(n)
for i in range(n):
    matured = [abs(y[j] - yhat[j]) for j in range(i) if j + h <= i]
    pool = list(cal) + matured
    q_ref[i] = core.conformal_quantile(pool[-window:], alpha)
    q_bad[i] = core.conformal_quantile(pool, alpha)
check("R3 pool is the last window scores", bool(np.array_equal(d0["q"], q_ref)), bool(np.array_equal(d0["q"], q_bad)))

if fails:
    print(f"[rolling-arm] FAIL: {fails}")
    sys.exit(1)
print("[rolling-arm] PASS")
