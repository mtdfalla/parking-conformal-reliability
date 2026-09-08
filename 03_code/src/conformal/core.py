#!/usr/bin/env python3
"""
core.py — the single tested implementation of every conformal primitive in this project.

Created 2026-09-02 (R-Phase 2, D-014). Naming note: project convention is to date new files, but this
module must be importable (`from core import ...`), and a leading date makes an illegal Python identifier.
The date lives here and in EXPERIMENTS_LOG (EXP-017) instead.

WHY THIS MODULE EXISTS
----------------------
Before this, six scripts each carried their own copy of the split-conformal quantile and the delay-aware
ACI recursion, with subtly different semantics. The external audit found three consequences:

  C01  The adaptive path computed k = ceil((n+1)(1-a)), converted it to a LEVEL k/m, and called
       np.quantile(pool, k/m, method="higher"). For k < m that returns virtual index ceil((m-1)k/m) = k,
       i.e. the (k+1)-th order statistic instead of the k-th. Reproduced in 35 of 36 (m, alpha)
       configurations tested. Direction: adaptive intervals came out ONE ORDER STATISTIC TOO WIDE, so the
       bug penalised ACI/ACQR on Winkler. split-CP and CQR used the correct path and were unaffected.
       -> `conformal_quantile` indexes the sorted array directly. Never use np.quantile for this.

  C02  The effective alpha was clipped only where it was read; the stored state kept drifting outside
       [0,1], contradicting the manuscript's "clips alpha_t to [1e-3, 1-1e-3]".
       -> `AdaptiveState` projects the STATE on every update. The projection is a documented parameter.

  C06  One robustness script updated the state immediately instead of after h steps, so a published claim
       was produced outside the paper's own causal protocol.
       -> There is exactly one recursion here, `adaptive_conformal_stream`, and it always releases
          feedback through `ReleaseQueue`. There is no immediate-update code path to reach by accident.

CONVENTIONS FIXED HERE (and asserted by the property tests)
-----------------------------------------------------------
* Nonconformity scores are ADDITIVE and the interval is [center_lo - q, center_hi + q].
    - plain ACI : center_lo = center_hi = yhat,        score_i = |y_i - yhat_i|
    - ACQR      : center_lo = qlo_i, center_hi = qhi_i, score_i = max(qlo_i - y_i, y_i - qhi_i)
  One recursion serves both; this is what makes them comparable.
* A forecast issued at stream index i has its outcome observed at index i + h. Its score AND its coverage
  indicator enter the state at index i + h, popped at the TOP of that step, so a bound issued at step
  i + h may use it. Nothing earlier can.
* Coverage indicators are evaluated against the UNCLIPPED bounds (the convention EXP-010/011 used), while
  the returned lower bound is clipped at `clip_low`. Clipping is a display/decision constraint, not a
  calibration event; conflating them would let the clip silently alter the alpha trajectory.

Run `python ../../tests/2026-09-02-test_conformal_core.py` after any change to this file.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

__all__ = [
    "conformal_quantile", "conformal_k", "AdaptiveState", "ReleaseQueue",
    "split_conformal_interval", "cqr_interval", "adaptive_conformal_stream",
    "select_gamma_on_calibration", "GAMMA_GRID",
    "winkler_score", "interval_metrics", "moving_block_bootstrap_ci",
    "block_length_for_cadence", "repair_quantile_crossing",
    "calendar_day_chunks", "fixed_row_chunks", "matured_release_end",
    "MIN_DISTINCT_READINGS", "is_low_information", "low_information_facilities",
]

# --------------------------------------------------------------------------------------
# 1. Split-conformal quantile — the C01 fix
# --------------------------------------------------------------------------------------

def conformal_k(n: int, alpha: float) -> int:
    """Rank of the conformal quantile: k = min(ceil((n+1)(1-alpha)), n), 1-indexed."""
    if n <= 0:
        raise ValueError("conformal_k: need at least one calibration score")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"conformal_k: alpha must be in (0,1), got {alpha}")
    return min(int(math.ceil((n + 1) * (1.0 - alpha))), n)


def conformal_quantile(scores: Sequence[float], alpha: float) -> float:
    """The k-th smallest score, k = ceil((n+1)(1-alpha)) capped at n.

    Indexes the sorted array directly. Do NOT reimplement with np.quantile: for k < n the
    ``method="higher"`` interpolation returns the (k+1)-th order statistic (audit issue C01).
    """
    s = np.sort(np.asarray(scores, dtype=float))
    return float(s[conformal_k(len(s), alpha) - 1])


def split_conformal_interval(cal_scores, yhat, alpha, clip_low=0.0):
    """Constant-width split-conformal band around a point forecast."""
    q = conformal_quantile(cal_scores, alpha)
    yhat = np.asarray(yhat, dtype=float)
    lo = yhat - q
    return (np.maximum(lo, clip_low) if clip_low is not None else lo), yhat + q


def cqr_interval(cal_scores, qlo, qhi, alpha, clip_low=0.0):
    """Conformalized quantile regression: the CQR margin added symmetrically to a quantile band."""
    q = conformal_quantile(cal_scores, alpha)
    qlo = np.asarray(qlo, dtype=float); qhi = np.asarray(qhi, dtype=float)
    lo = qlo - q
    return (np.maximum(lo, clip_low) if clip_low is not None else lo), qhi + q


# --------------------------------------------------------------------------------------
# 2. Adaptive state and release queue — the C02 and C06 fixes
# --------------------------------------------------------------------------------------

@dataclass
class AdaptiveState:
    """Gibbs-Candes adaptive miscoverage level with a PROJECTED state.

    alpha_{t+1} = Proj_[lo,hi]( alpha_t + gamma * (alpha_target - err_t) )

    The projection is applied to the stored state, not merely to the value read at query time, so the
    trajectory cannot drift far outside the feasible range and then take many steps to return (C02).
    Set ``bounds=None`` to recover the unprojected textbook recursion for sensitivity analysis.
    """
    alpha_target: float
    gamma: float = 0.05
    bounds: tuple[float, float] | None = (1e-3, 1.0 - 1e-3)
    alpha: float = field(init=False)
    trajectory: list[float] = field(default_factory=list, repr=False)

    def __post_init__(self):
        if not (0.0 < self.alpha_target < 1.0):
            raise ValueError("alpha_target must be in (0,1)")
        self.alpha = self._project(self.alpha_target)

    def _project(self, a: float) -> float:
        if self.bounds is None:
            return a
        lo, hi = self.bounds
        return min(max(a, lo), hi)

    def effective_alpha(self) -> float:
        """Level to use for the current quantile. Always inside (0,1) so a quantile is well defined."""
        lo, hi = self.bounds if self.bounds is not None else (1e-12, 1.0 - 1e-12)
        return min(max(self.alpha, lo), hi)

    def update(self, err: int) -> float:
        """err = 1 if the matured observation fell OUTSIDE its interval, else 0."""
        self.alpha = self._project(self.alpha + self.gamma * (self.alpha_target - err))
        self.trajectory.append(self.alpha)
        return self.alpha


class ReleaseQueue:
    """Feedback scheduled by the index at which it becomes observable.

    A forecast issued at index i for horizon h is resolved at index i + h; nothing may consult it before.
    ``schedule`` is the only way in and ``pop`` the only way out, so a lookahead requires deliberately
    passing a wrong index rather than merely forgetting a delay.
    """

    def __init__(self):
        self._q: dict[int, list] = {}
        self.released_at: list[tuple[int, int]] = []   # (issue_index, release_index), for auditing

    def schedule(self, release_index: int, issue_index: int, payload) -> None:
        if release_index <= issue_index:
            raise ValueError(f"release_index {release_index} must exceed issue_index {issue_index}")
        self._q.setdefault(release_index, []).append((issue_index, payload))

    def pop(self, index: int) -> list:
        items = self._q.pop(index, [])
        for issue_index, _ in items:
            self.released_at.append((issue_index, index))
        return [payload for _, payload in items]

    def __len__(self) -> int:
        return sum(len(v) for v in self._q.values())


# --------------------------------------------------------------------------------------
# 3. The one adaptive recursion
# --------------------------------------------------------------------------------------

def adaptive_conformal_stream(
    cal_scores,
    center_lo,
    center_hi,
    y,
    alpha: float,
    horizon: int,
    gamma: float = 0.05,
    window: int | None = None,
    bounds: tuple[float, float] | None = (1e-3, 1.0 - 1e-3),
    clip_low: float | None = 0.0,
    score_fn: Callable[[float, float, float], float] | None = None,
    return_state: bool = False,
):
    """Delay-aware adaptive conformal intervals. Serves both ACI and ACQR.

    Parameters
    ----------
    cal_scores : initial score pool (calibration nonconformity scores).
    center_lo, center_hi : per-step band centres. Equal arrays give plain ACI; a CQR band gives ACQR.
    y : realised outcomes, aligned with the centres.
    alpha : target miscoverage.
    horizon : h, in stream steps. Feedback from step i is released at step i + h.
    window : sliding score-window length; ``None`` uses len(cal_scores) (the project default).
    bounds : projection interval for the adaptive state; ``None`` disables projection.
    clip_low : lower bound clip applied to the RETURNED interval only, never to the coverage indicator.
    score_fn : (y_i, lo_i, hi_i) -> score. Default max(lo_i - y_i, y_i - hi_i), which reduces to
               |y - yhat| when lo == hi, so ACI and ACQR share one definition.

    Returns
    -------
    (lo, hi) or (lo, hi, diagnostics) when ``return_state``.
    """
    if score_fn is None:
        score_fn = lambda yi, lo_i, hi_i: max(lo_i - yi, yi - hi_i)

    center_lo = np.asarray(center_lo, dtype=float)
    center_hi = np.asarray(center_hi, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(y)
    if not (len(center_lo) == len(center_hi) == n):
        raise ValueError("center_lo, center_hi and y must be the same length")
    if horizon < 1:
        raise ValueError("horizon must be >= 1 step")

    scores = list(np.asarray(cal_scores, dtype=float))
    if not scores:
        raise ValueError("cal_scores must be non-empty")
    window = window or len(scores)

    state = AdaptiveState(alpha_target=alpha, gamma=gamma, bounds=bounds)
    queue = ReleaseQueue()
    lo = np.empty(n); hi = np.empty(n)
    diag = {"alpha": np.empty(n), "q": np.empty(n), "pool_size": np.empty(n, dtype=int)}

    for i in range(n):
        for (score_i, err_i) in queue.pop(i):          # matured feedback, before this step's bound
            scores.append(score_i)
            state.update(err_i)

        a_eff = state.effective_alpha()
        pool = scores[-window:]
        q = conformal_quantile(pool, a_eff)

        lo_raw = center_lo[i] - q
        hi[i] = center_hi[i] + q
        lo[i] = max(lo_raw, clip_low) if clip_low is not None else lo_raw

        covered = (y[i] >= lo_raw) and (y[i] <= hi[i])   # unclipped, by convention
        queue.schedule(i + horizon, i, (score_fn(y[i], center_lo[i], center_hi[i]), 0 if covered else 1))

        diag["alpha"][i] = a_eff; diag["q"][i] = q; diag["pool_size"][i] = len(pool)

    if return_state:
        diag["released_at"] = queue.released_at
        diag["alpha_trajectory"] = np.asarray(state.trajectory)
        return lo, hi, diag
    return lo, hi


# --------------------------------------------------------------------------------------
# 4. Metrics and inference helpers
# --------------------------------------------------------------------------------------

def winkler_score(y, lo, hi, alpha) -> float:
    """Winkler / interval score (Gneiting & Raftery 2007). Strictly proper; lower is better."""
    y = np.asarray(y, float); lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    s = (hi - lo).astype(float)
    below = y < lo; above = y > hi
    s[below] += (2.0 / alpha) * (lo[below] - y[below])
    s[above] += (2.0 / alpha) * (y[above] - hi[above])
    return float(np.mean(s))


def interval_metrics(y, lo, hi, alpha) -> tuple[float, float, float]:
    """(PICP, MPIW, Winkler)."""
    y = np.asarray(y, float); lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return (float(np.mean((y >= lo) & (y <= hi))),
            float(np.mean(hi - lo)),
            winkler_score(y, lo, hi, alpha))


def block_length_for_cadence(cadence_minutes: float, hours: float = 3.0) -> int:
    """Block length for the moving-block bootstrap, expressed in TIME rather than rows (audit I06).

    The project previously used a fixed 20-row block in both cities, which is 100 minutes at Belgrade's
    5-min cadence and 600 minutes at Birmingham's 30-min cadence -- two very different dependence
    assumptions wearing the same number. Deriving the block from the cadence makes them comparable.

    Parametrised by cadence rather than steps-per-day on purpose: Birmingham is daytime-only, so
    "steps per day" would silently mean a 9.5-hour day there and a 24-hour day in Belgrade.

    >>> block_length_for_cadence(5, 3.0)    # Belgrade, 3 hours
    36
    >>> block_length_for_cadence(30, 3.0)   # Birmingham, 3 hours
    6
    """
    if cadence_minutes <= 0:
        raise ValueError("cadence_minutes must be positive")
    return max(2, int(round(hours * 60.0 / cadence_minutes)))


def moving_block_bootstrap_ci(indicator, B: int = 10_000, block: int = 20,
                              seed: int = 42, level: float = 0.90):
    """Percentile CI for a mean under serial dependence, via the moving-block bootstrap.

    Default B raised from the project's previous 500 to 10,000 (audit I06).
    """
    x = np.asarray(indicator, dtype=float)
    n = len(x)
    if n < block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = max(1, n // block)
    starts = rng.integers(0, n - block + 1, size=(B, n_blocks))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(B, -1)
    means = x[idx].mean(axis=1)
    tail = (1.0 - level) / 2.0 * 100.0
    return float(np.percentile(means, tail)), float(np.percentile(means, 100.0 - tail))


def repair_quantile_crossing(qlo, qhi):
    """Enforce qlo <= qhi elementwise; returns (qlo, qhi, n_crossings).

    Separately fitted lower/upper quantile models can cross. The audit asked for the frequency to be
    reported rather than silently repaired, so the count is returned.
    """
    qlo = np.asarray(qlo, float).copy(); qhi = np.asarray(qhi, float).copy()
    cross = qlo > qhi
    n = int(cross.sum())
    if n:
        mid = 0.5 * (qlo[cross] + qhi[cross])
        qlo[cross] = mid; qhi[cross] = mid
    return qlo, qhi, n


# --------------------------------------------------------------------------------------
# 5. Step-size selection — EXP-018 / R-Phase 3b
# --------------------------------------------------------------------------------------

GAMMA_GRID = (0.002, 0.005, 0.01, 0.02, 0.05, 0.1)


def select_gamma_on_calibration(cal_scores, center_lo_cal, center_hi_cal, y_cal, alpha, horizon,
                                grid=GAMMA_GRID, split_frac=0.5, window=None,
                                bounds=(1e-3, 1.0 - 1e-3), score_fn=None):
    """Choose the ACI step size gamma using ONLY calibration data.

    Why this exists
    ---------------
    EXP-018 showed that the coverage debt of delay-aware ACI is governed by a step-size x horizon
    interaction: at Belgrade, gamma = 0.05 costs 0.26 coverage points at h = 1 but 2.88 points at h = 6,
    while gamma = 0.005 holds ~0.90 at every horizon. Wang & Hyndman (2024) prove the corresponding
    theoretical statement -- the finite-sample coverage error bound grows with the forecast horizon.

    So gamma must be chosen per facility and horizon rather than fixed at a project-wide default. It must
    NOT be read off the test-set sensitivity surface: that is test-set tuning, the error class this
    revision exists to remove. This function therefore uses a NESTED TEMPORAL SPLIT of the calibration
    set -- an earlier segment cal-A seeds the score pool, a later segment cal-B is replayed as a
    pseudo-test stream, and gamma is scored there. The test set is never touched.

    The same nested split is what audit issue C04 requires for the trust/abstain thresholds, so both
    selections share one honest protocol.

    Selection rule: minimise |PICP(cal-B) - (1 - alpha)|, ties broken by lower Winkler score. Coverage is
    the primary criterion because gamma's job is calibration, not sharpness.

    Returns (gamma, diagnostics_dict).
    """
    y_cal = np.asarray(y_cal, dtype=float)
    center_lo_cal = np.asarray(center_lo_cal, dtype=float)
    center_hi_cal = np.asarray(center_hi_cal, dtype=float)
    cal_scores = np.asarray(cal_scores, dtype=float)

    n = len(y_cal)
    cut = int(n * split_frac)
    # cal-B must be long enough for the recursion to say anything, and must clear the delay
    if cut < 30 or (n - cut) < max(50, 10 * horizon):
        return grid[len(grid) // 2], {"reason": "calibration too short for nested selection",
                                      "n_cal": n, "gamma_grid": list(grid)}

    pool_a = cal_scores[:cut]
    target = 1.0 - alpha
    rows = []
    for g in grid:
        lo, hi = adaptive_conformal_stream(
            pool_a, center_lo_cal[cut:], center_hi_cal[cut:], y_cal[cut:],
            alpha, horizon, gamma=g, window=window, bounds=bounds,
            clip_low=None, score_fn=score_fn)
        picp, mpiw, wink = interval_metrics(y_cal[cut:], lo, hi, alpha)
        rows.append((abs(picp - target), wink, g, picp, mpiw))
    rows.sort()
    best = rows[0]
    return best[2], {"n_cal": n, "n_cal_a": cut, "n_cal_b": n - cut,
                     "chosen_gamma": best[2], "calB_picp": best[3], "calB_mpiw": best[4],
                     "grid_calB_picp": {g: p for _, _, g, p, _ in rows}}


# --------------------------------------------------------------------------------------
# 6. Group-conditional (Mondrian-style) adaptive stream — added 2026-09-03 for R-Phase 3b task 2
# --------------------------------------------------------------------------------------

def grouped_adaptive_conformal_stream(
    cal_scores_by_group,
    groups,
    center_lo,
    center_hi,
    y,
    alpha: float,
    horizon: int,
    gamma: float = 0.05,
    global_pool=None,
    min_group: int = 50,
    window: int | None = None,
    bounds: tuple[float, float] | None = (1e-3, 1.0 - 1e-3),
    clip_low: float | None = 0.0,
    score_fn: Callable[[float, float, float], float] | None = None,
    return_state: bool = False,
):
    """Group-conditional delay-aware adaptive conformal intervals (ToD-ACI and Mondrian-style ACI).

    Why this exists
    ---------------
    Audit issue C05: `run_cond_trust_corrected.py` initialised EVERY time-of-day bucket from the SAME
    global residual pool (`st = {nm: {"a": a, "sc": list(resid)} ...}`).  The adaptive state was per
    bucket, but the score pool was not, so calling the result "group-conditional (Mondrian-style)"
    overstated what was implemented.  Here each group starts from ITS OWN calibration scores.

    Sparse groups get a shrinkage fallback rather than a silent global pool: a group holding fewer than
    `min_group` own scores is initialised from its own scores UNION `global_pool`, and the fallback is
    recorded per group in the diagnostics so the counts can be reported (the audit asks for exactly this).

    Delay handling
    --------------
    One shared release queue carries the issuing group with each payload, so feedback from a forecast
    made at step i in group g returns to group g's state and pool at step i + h -- never to whichever
    group happens to occupy step i + h, and never earlier than i + h.

    Parameters
    ----------
    cal_scores_by_group : {group: sequence of that group's calibration scores}.
    groups : per-step group label, aligned with y.
    global_pool : scores used for the sparse-group fallback; defaults to all calibration scores pooled.
    min_group : own-score count below which the fallback is applied.
    window : per-group sliding window; ``None`` uses each group's own initial pool size.

    Returns
    -------
    (lo, hi) or (lo, hi, diagnostics) when ``return_state``.  Diagnostics carry `group_init`
    (per group: n_own, n_init, fell_back) so the sparse-bucket counts are reportable without a rerun.
    """
    if score_fn is None:
        score_fn = lambda yi, lo_i, hi_i: max(lo_i - yi, yi - hi_i)

    center_lo = np.asarray(center_lo, dtype=float)
    center_hi = np.asarray(center_hi, dtype=float)
    y = np.asarray(y, dtype=float)
    groups = list(groups)
    n = len(y)
    if not (len(center_lo) == len(center_hi) == n == len(groups)):
        raise ValueError("center_lo, center_hi, y and groups must be the same length")
    if horizon < 1:
        raise ValueError("horizon must be >= 1 step")

    if global_pool is None:
        gp = []
        for v in cal_scores_by_group.values():
            gp.extend(list(np.asarray(v, dtype=float)))
        global_pool = gp
    global_pool = list(np.asarray(global_pool, dtype=float))

    keys = set(cal_scores_by_group) | set(groups)
    pools, states, windows, ginfo = {}, {}, {}, {}
    for g in keys:
        own = list(np.asarray(cal_scores_by_group.get(g, []), dtype=float))
        fell_back = len(own) < min_group
        init = (own + global_pool) if fell_back else own
        if not init:
            raise ValueError(f"group {g!r} has no calibration scores and the global pool is empty")
        pools[g] = list(init)
        states[g] = AdaptiveState(alpha_target=alpha, gamma=gamma, bounds=bounds)
        windows[g] = window or len(init)
        ginfo[g] = {"n_own": len(own), "n_init": len(init), "fell_back": bool(fell_back)}

    queue = ReleaseQueue()
    lo = np.empty(n); hi = np.empty(n)
    diag = {"alpha": np.empty(n), "q": np.empty(n), "pool_size": np.empty(n, dtype=int),
            "group_init": ginfo}

    for i in range(n):
        for (grp_i, score_i, err_i) in queue.pop(i):     # route feedback to the ISSUING group
            pools[grp_i].append(score_i)
            states[grp_i].update(err_i)

        g = groups[i]
        a_eff = states[g].effective_alpha()
        pool = pools[g][-windows[g]:]
        q = conformal_quantile(pool, a_eff)

        lo_raw = center_lo[i] - q
        hi[i] = center_hi[i] + q
        lo[i] = max(lo_raw, clip_low) if clip_low is not None else lo_raw

        covered = (y[i] >= lo_raw) and (y[i] <= hi[i])
        queue.schedule(i + horizon, i, (g, score_fn(y[i], center_lo[i], center_hi[i]),
                                        0 if covered else 1))

        diag["alpha"][i] = a_eff; diag["q"][i] = q; diag["pool_size"][i] = len(pool)

    if return_state:
        diag["released_at"] = queue.released_at
        diag["alpha_final"] = {g: s.alpha for g, s in states.items()}
        return lo, hi, diag
    return lo, hi


# --------------------------------------------------------------------------------------
# 7. Batch release scheduling — added 2026-09-03 for R-Phase 3b task 4 (audit C07)
# --------------------------------------------------------------------------------------
#
# Why this lives in core rather than in the experiment script
# -----------------------------------------------------------
# `adaptive_conformal_stream` releases feedback one step at a time through `ReleaseQueue`. Batch
# methods (EnbPI via MAPIE, and the rolling-origin folds of task 5) instead refit or update on CHUNKS
# of the test stream, so they need the same maturity rule expressed over a chunk boundary. Audit issue
# C07 is precisely what happens when that rule is left implicit:
# `2026-08-04-e3-baselines.py` chunked by a FIXED ROW COUNT and released the WHOLE chunk, so the last
# h-1 rows of every chunk were handed over with outcomes that were not yet observable.
#
# Keeping the rule here means one definition of "matured", shared by the streaming and batch paths and
# covered by the property gate, instead of a second convention living in a script.

def calendar_day_chunks(timestamps) -> list[tuple[int, int]]:
    """Contiguous [start, end) blocks, one per calendar date, in stream order.

    The C07 fix: a chunk must be an ACTUAL day, not a fixed row count. After `dropna` and `use_{H}`
    filtering the number of retained rows per day varies, so `range(0, n, steps_day)` silently drifts
    out of alignment with the calendar -- and on Birmingham, whose sessions are daytime-only, a
    fixed count spans nights.
    """
    import pandas as pd
    d = pd.to_datetime(pd.Series(np.asarray(timestamps))).dt.date.values
    if len(d) == 0:
        return []
    out, start = [], 0
    for i in range(1, len(d)):
        if d[i] != d[i - 1]:
            out.append((start, i)); start = i
    out.append((start, len(d)))
    return out


def fixed_row_chunks(n: int, size: int) -> list[tuple[int, int]]:
    """The ARCHIVED scheme, retained only so the C07 delta can be measured against it."""
    if size < 1:
        raise ValueError("size must be >= 1")
    return [(s, min(s + size, n)) for s in range(0, n, size)]


def matured_release_end(chunk_end: int, horizon: int, already_released: int, n: int) -> int:
    """How far a batch method may release outcomes once the stream has reached `chunk_end`.

    A forecast issued at index i is resolved at i + horizon, so at index `chunk_end` the observable
    rows are exactly those with i + horizon <= chunk_end, i.e. i <= chunk_end - horizon. Returned as an
    exclusive end, monotone in `already_released` so held-back rows carry forward and are never lost.

    This is the same rule `ReleaseQueue` enforces per step; with horizon = 1 it degenerates to
    releasing the whole chunk, which is the reduction property the gate asserts (P21).
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1 step")
    return min(n, max(already_released, chunk_end - horizon + 1))


# --------------------------------------------------------------------------------------
# 7. Data-quality exclusion (X08) — added 2026-09-03, revision 38, per D-018
# --------------------------------------------------------------------------------------

MIN_DISTINCT_READINGS = 10


def is_low_information(occupancy, min_distinct: int = MIN_DISTINCT_READINGS) -> bool:
    """True if an occupancy window carries too few distinct readings to be a forecasting target.

    THE DEFECT THIS EXISTS FOR (X08, EXP-026). Belgrade facility 8 (`Garaza "Vukov spomenik"`) stops
    measuring partway through the record: it reports exactly 0.0 for 15-18 March and exactly 109.0 --
    its apparent capacity -- on 20 March, giving TWO distinct values across its entire 1,015-row test
    window. The pattern is in the raw export, so it is a source property, not a pipeline artifact.
    Forecasting a dead sensor is not a test of a forecaster, and because facility 8 is the
    worst-covered facility for EnbPI and NGBoost it was inflating those baselines' failure and
    flattering our own comparative claim.

    WHY THE RULE IS STATED THIS WAY. It is a function of the INPUT SERIES ALONE. It cannot see any
    method's predictions, coverage or score, which is what separates it from the forbidden repair of
    dropping a facility whose results are inconvenient. Callers must apply it to the evaluation window
    they are about to score, before fitting anything.

    WHY THE THRESHOLD IS NOT A TUNED PARAMETER. On the Belgrade test split the distinct-value counts
    are: facility 1 -> 1, facility 8 -> 2, and the NEXT LOWEST facility -> 64. Any threshold in
    [3, 60] selects exactly the same two facilities, so the choice of 10 carries no discretion. That
    gap is published alongside the rule (LESSONS_LOG B16: publish the gap, not just the threshold).
    If this is ever applied to a new dataset, RE-MEASURE the gap -- a rule whose selection changes
    when the cutoff moves slightly is a tuned rule wearing a data-quality costume.
    """
    v = np.asarray(occupancy, dtype=float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        return True
    return int(np.unique(v).size) < int(min_distinct)


def low_information_facilities(df, occupancy_col: str = "occupancy",
                               facility_col: str = "facility_id",
                               min_distinct: int = MIN_DISTINCT_READINGS) -> list:
    """The sorted facility ids to EXCLUDE from `df`, judged on `df`'s rows only.

    Pass the evaluation window (e.g. the test split, or one rolling-origin fold's test window), not the
    whole frame: a facility can be healthy in training and dead in test, which is exactly the X08 case
    (facility 8's training window has std 18.1 and passes every structural check).
    """
    out = []
    for fid, g in df.groupby(facility_col):
        if is_low_information(g[occupancy_col].values, min_distinct):
            out.append(fid)
    return sorted(out)
