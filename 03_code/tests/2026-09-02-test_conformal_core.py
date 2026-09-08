#!/usr/bin/env python3
"""
R-Phase 2 gate — property tests for `03_code/src/conformal/core.py` (D-014, EXP-017).

Each test names the audit issue it defends. The suite must exit 0 before any experiment script is
repointed at the core, and it is re-run before every result-generating rerun.

  P1  conformal quantile equals the hand-computed k-th order statistic          — C01
  P2  regression witness: the retired np.quantile path returned the (k+1)-th    — C01
  P3  the conformal quantile is monotone in alpha                              — C01 sanity
  P4  the adaptive state stays inside its projection under adversarial streams  — C02
  P5  ReleaseQueue refuses same-step release and fires exactly at i + h         — C06/C07
  P6  NO LOOKAHEAD: perturbing y at t cannot change any bound before t + h      — C06/C07 (the key test)
  P7  lower <= upper everywhere                                                 — general
  P8  bitwise determinism under repeated calls                                  — R01 reproducibility
  P9  synthetic shift: the recursion recovers nominal coverage, split-CP does not — validates the method
  P10 ACI is the ACQR recursion with a degenerate band                          — comparability of the two
  P11 Winkler reduces to mean width when everything is covered                  — metric correctness
  P12 the moving-block bootstrap CI is honest on iid data                       — I06
  P13 quantile-crossing repair is counted, not silent                           — audit 3.5
  P18 calendar-day chunks partition the stream exactly, one date per chunk      — C07
  P19 batch release never hands over an outcome that has not matured            — C07 (the key test)
  P20 held-back rows carry forward and are released exactly once                — C07
  P21 reduction: at h = 1 the matured rule releases the whole chunk             — C07 sanity

Run: python 2026-09-02-test_conformal_core.py
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "conformal"))
import core

FAIL = []
def check(name, cond, detail=""):
    ok = bool(cond)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    if not ok: FAIL.append(name)

rng = np.random.default_rng(42)
SIZES = [10, 50, 100, 200, 766, 1839]
ALPHAS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30]

print("=== P1-P3  conformal quantile (C01) ===")
ok1 = ok2 = ok3 = True
bugged = 0
for n in SIZES:
    pool = np.sort(rng.random(n))
    for a in ALPHAS:
        k = min(math.ceil((n + 1) * (1 - a)), n)
        ok1 &= (core.conformal_k(n, a) == k)
        ok1 &= (core.conformal_quantile(pool, a) == pool[k - 1])
        # the retired path, reproduced here so the regression stays visible
        lv = min(1.0, k / n)
        old = float(np.max(pool)) if lv >= 1 else float(np.quantile(pool, lv, method="higher"))
        if old != pool[k - 1]:
            bugged += 1
            ok2 &= (old == pool[k]) if k < n else True   # it selected exactly one rank too high
    qs = [core.conformal_quantile(pool, a) for a in sorted(ALPHAS, reverse=True)]
    ok3 &= all(x <= y for x, y in zip(qs, qs[1:]))
check("P1 quantile == hand-computed k-th order statistic", ok1, f"{len(SIZES)*len(ALPHAS)} configurations")
check("P2 retired np.quantile path was one rank too high", ok2 and bugged > 0,
      f"reproduced in {bugged}/{len(SIZES)*len(ALPHAS)} configurations; core is correct in all")
check("P3 quantile monotone non-decreasing as alpha falls", ok3)

print("\n=== P4-P5  adaptive state and release queue (C02, C06/C07) ===")
for stream, label in [([1] * 500, "all-miss"), ([0] * 500, "all-cover")]:
    st = core.AdaptiveState(alpha_target=0.10, gamma=0.05, bounds=(1e-3, 1 - 1e-3))
    for e in stream: st.update(e)
    check(f"P4 state stays in projection under {label}", 1e-3 <= st.alpha <= 1 - 1e-3,
          f"final alpha = {st.alpha:.6f}")
st_unproj = core.AdaptiveState(alpha_target=0.10, gamma=0.05, bounds=None)
for e in [1] * 500: st_unproj.update(e)
check("P4 unprojected variant does drift (so projection is doing work)", st_unproj.alpha < 0.0,
      f"unprojected alpha = {st_unproj.alpha:.3f}")

q = core.ReleaseQueue()
try:
    q.schedule(5, 5, "x"); same_step_rejected = False
except ValueError:
    same_step_rejected = True
check("P5 ReleaseQueue rejects release at the issue step", same_step_rejected)
q = core.ReleaseQueue()
for i in range(10): q.schedule(i + 3, i, i)
fired = {i: q.pop(i) for i in range(13)}
check("P5 payloads fire exactly h steps late",
      all(fired[i + 3] == [i] for i in range(10)) and all(fired[i] == [] for i in range(3)))

print("\n=== P6  no lookahead (the key test) ===")
n, h = 400, 3
cal = np.abs(rng.normal(0, 1, 300))
yhat = np.zeros(n)
y = rng.normal(0, 1, n)
lo0, hi0 = core.adaptive_conformal_stream(cal, yhat, yhat, y, 0.10, h, clip_low=None)
t = 150
y2 = y.copy(); y2[t] += 50.0                      # a violent perturbation at index t
lo1, hi1 = core.adaptive_conformal_stream(cal, yhat, yhat, y2, 0.10, h, clip_low=None)
check("P6 bounds before t+h are bit-identical after perturbing y[t]",
      np.array_equal(lo0[:t + h], lo1[:t + h]) and np.array_equal(hi0[:t + h], hi1[:t + h]),
      f"first divergence at index {int(np.argmax(hi0 != hi1))} (expected {t + h})")
check("P6 the perturbation does reach the stream at t+h", not np.array_equal(hi0, hi1),
      "otherwise the feedback path would be dead")
_, _, diag = core.adaptive_conformal_stream(cal, yhat, yhat, y, 0.10, h, clip_low=None, return_state=True)
check("P6 every release index equals issue + h",
      all(rel == iss + h for iss, rel in diag["released_at"]),
      f"{len(diag['released_at'])} releases audited")

print("\n=== P7-P8, P10-P11  invariants ===")
check("P7 lower <= upper everywhere", bool(np.all(lo0 <= hi0)))
a1 = core.adaptive_conformal_stream(cal, yhat, yhat, y, 0.10, h)
a2 = core.adaptive_conformal_stream(cal, yhat, yhat, y, 0.10, h)
check("P8 repeated calls are bitwise identical",
      np.array_equal(a1[0], a2[0]) and np.array_equal(a1[1], a2[1]))
yh = rng.normal(0, 1, n)
res = np.abs(rng.normal(0, 1, 300))
aci = core.adaptive_conformal_stream(res, yh, yh, y, 0.10, h, clip_low=None)
acqr_degenerate = core.adaptive_conformal_stream(
    res, yh, yh, y, 0.10, h, clip_low=None,
    score_fn=lambda yi, l, u: max(l - yi, yi - u))
check("P10 ACI == ACQR recursion with a degenerate band",
      np.array_equal(aci[0], acqr_degenerate[0]) and np.array_equal(aci[1], acqr_degenerate[1]))
yc = np.zeros(50); loc = -np.ones(50); hic = np.ones(50)
check("P11 Winkler == mean width when all covered",
      abs(core.winkler_score(yc, loc, hic, 0.10) - 2.0) < 1e-12)

print("\n=== P9  synthetic distribution shift ===")
n_cal, n_te = 500, 3000
cal_s = np.abs(rng.normal(0, 1.0, n_cal))                    # calibrated on sigma = 1
sigma = np.where(np.arange(n_te) < n_te // 2, 1.0, 3.0)      # test doubles-then-triples the scale
y_te = rng.normal(0, sigma)
yhat_te = np.zeros(n_te)
s_lo, s_hi = core.split_conformal_interval(cal_s, yhat_te, 0.10, clip_low=None)
a_lo, a_hi = core.adaptive_conformal_stream(cal_s, yhat_te, yhat_te, y_te, 0.10, 1,
                                            window=n_cal, clip_low=None)
picp_split = float(np.mean((y_te >= s_lo) & (y_te <= s_hi)))
picp_aci = float(np.mean((y_te >= a_lo) & (y_te <= a_hi)))
check("P9 split-CP under-covers under the shift", picp_split < 0.85, f"PICP {picp_split:.3f}")
check("P9 the adaptive recursion recovers ~nominal coverage", abs(picp_aci - 0.90) < 0.02,
      f"PICP {picp_aci:.3f}")

print("\n=== P12-P13  inference helpers (I06, quantile crossing) ===")
iid = (rng.random(4000) < 0.90).astype(float)
lo_ci, hi_ci = core.moving_block_bootstrap_ci(iid, B=2000, block=20, seed=42)
check("P12 bootstrap CI brackets the empirical mean", lo_ci < iid.mean() < hi_ci,
      f"[{lo_ci:.4f}, {hi_ci:.4f}] around {iid.mean():.4f}")
check("P12 block length derives from cadence, not row count",
      core.block_length_for_cadence(5, 3.0) == 36 and core.block_length_for_cadence(30, 3.0) == 6,
      "3 h = 36 rows at Belgrade's 5-min cadence, 6 rows at Birmingham's 30-min cadence "
      "(the retired fixed block of 20 rows meant 100 min vs 600 min)")
ql = np.array([1.0, 5.0, 2.0]); qh = np.array([2.0, 3.0, 4.0])
rl, rh, ncross = core.repair_quantile_crossing(ql, qh)
check("P13 crossings repaired and counted", ncross == 1 and bool(np.all(rl <= rh)), f"{ncross} crossing")

# ---------------------------------------------------------------------------------------------
# P14-P17  group-conditional adaptive stream (C05)  — added 2026-09-03 with R-Phase 3b task 2
# ---------------------------------------------------------------------------------------------
print("\n=== P14-P17  group-conditional stream (C05) ===")
rng_g = np.random.default_rng(7)
n_g = 600
grp = np.array(["a", "b", "c"])[rng_g.integers(0, 3, n_g)]
cen = rng_g.normal(50, 5, n_g)
y_g = cen + rng_g.normal(0, 3, n_g)
cal_a = np.abs(rng_g.normal(0, 3, 300))

# P14 reduction: one group, pool == cal_scores, must be BIT-IDENTICAL to the ungrouped stream.
lo_u, hi_u = core.adaptive_conformal_stream(cal_a, cen, cen, y_g, 0.10, 3, gamma=0.05)
lo_g, hi_g = core.grouped_adaptive_conformal_stream(
    {"only": cal_a}, ["only"] * n_g, cen, cen, y_g, 0.10, 3, gamma=0.05, min_group=1)
check("P14 grouped stream with ONE group reduces exactly to the ungrouped stream",
      np.array_equal(lo_u, lo_g) and np.array_equal(hi_u, hi_g),
      "bit-identical bounds — the grouping machinery adds no drift")

# P15 feedback routes to the ISSUING group, not the group occupying step t+h.
pools = {k: np.abs(rng_g.normal(0, 3, 200)) for k in ["a", "b", "c"]}
lo0, hi0, d0 = core.grouped_adaptive_conformal_stream(
    pools, grp, cen, cen, y_g, 0.10, 3, gamma=0.05, min_group=1, return_state=True)
t_p = next(i for i in range(100, 300) if (y_g[i] >= lo0[i]) and (y_g[i] <= hi0[i]))
y_p = y_g.copy(); y_p[t_p] += 400.0
lo1, hi1, d1 = core.grouped_adaptive_conformal_stream(
    pools, grp, cen, cen, y_p, 0.10, 3, gamma=0.05, min_group=1, return_state=True)
diff_idx = np.flatnonzero(hi0 != hi1)
issuing = grp[t_p]
check("P15 grouped: bounds before t+h are bit-identical after perturbing y[t]",
      np.array_equal(lo0[:t_p + 3], lo1[:t_p + 3]) and np.array_equal(hi0[:t_p + 3], hi1[:t_p + 3]))
check("P15 grouped: every changed step belongs to the ISSUING group",
      diff_idx.size > 0 and all(grp[i] == issuing for i in diff_idx),
      f"perturbed a step in group '{issuing}'; {diff_idx.size} changed steps, all in '{issuing}'")
# The release lands at t+h, but a group's pool only moves a BOUND the next time that group is
# scheduled -- the two coincide only when step t+h happens to belong to the issuing group. The exact
# property is therefore: first change == first step at or after t+h belonging to the issuing group.
nxt_own = next(i for i in range(t_p + 3, n_g) if grp[i] == issuing)
check("P15 grouped: the first change is the first step >= t+h in the issuing group",
      diff_idx.size > 0 and diff_idx[0] == nxt_own and nxt_own >= t_p + 3,
      f"t+h = {t_p + 3} (group '{grp[t_p + 3]}'); next '{issuing}' step = {nxt_own}; first change = {diff_idx[0]}")

# P16 sparse-group shrinkage fallback fires, is recorded, and leaves dense groups untouched.
sparse = {"a": np.abs(rng_g.normal(0, 3, 200)), "b": np.abs(rng_g.normal(0, 3, 200)),
          "c": np.abs(rng_g.normal(0, 3, 5))}
_, _, d2 = core.grouped_adaptive_conformal_stream(
    sparse, grp, cen, cen, y_g, 0.10, 3, gamma=0.05, min_group=50, return_state=True)
gi = d2["group_init"]
check("P16 sparse group falls back and dense groups do not",
      gi["c"]["fell_back"] and not gi["a"]["fell_back"] and not gi["b"]["fell_back"],
      f"c: n_own={gi['c']['n_own']} -> n_init={gi['c']['n_init']}; a/b keep their own pools")
check("P16 fallback is a UNION, not a replacement (own scores are retained)",
      gi["c"]["n_init"] == gi["c"]["n_own"] + 405,
      "own 5 + global 405 = 410 — the group's own evidence is not discarded")

# P17 each group really does carry its own pool: identical groups but different pools must differ.
# Exact property, no tuned threshold: at each group's FIRST appearance no feedback has matured, so its
# half-width must equal the conformal quantile of THAT GROUP'S OWN pool. Under the retired global-pool
# initialisation all three would instead share one quantile. (Mean widths across the whole stream are
# NOT 3x apart even with a 3x pool, because the ACI recursion corrects the level back toward target --
# that is the mechanism working, so it would be the wrong thing to assert.)
scaled = {"a": cal_a * 3.0, "b": cal_a, "c": cal_a * 0.5}
lo_s, hi_s = core.grouped_adaptive_conformal_stream(
    scaled, grp, cen, cen, y_g, 0.10, 3, gamma=0.05, min_group=1)
first_ok, detail = True, []
for gk in ["a", "b", "c"]:
    fi = int(np.flatnonzero(grp == gk)[0])
    expect = core.conformal_quantile(scaled[gk], 0.10)
    got = (hi_s[fi] - lo_s[fi]) / 2
    first_ok &= abs(got - expect) < 1e-12
    detail.append(f"{gk}:{got:.4f}")
check("P17 each group opens on ITS OWN calibration quantile, not a shared global one",
      first_ok, "first-step half-widths " + ", ".join(detail) +
      " — each equals its own pool's quantile to 1e-12")

# ---------------------------------------------------------------------------------------------
# P18-P21  batch release scheduling (C07)  — added 2026-09-03 with R-Phase 3b task 4
# ---------------------------------------------------------------------------------------------
print("\n=== P18-P21  batch release scheduling (C07) ===")

import pandas as pd  # noqa: E402

# An uneven, realistic stream: 4 calendar days with DIFFERENT retained-row counts, which is exactly
# the situation in which the archived fixed-row chunking drifts out of alignment with the calendar.
counts = [37, 52, 41, 48]
stamps = []
for day, c in enumerate(counts):
    base = pd.Timestamp("2017-03-18") + pd.Timedelta(days=day)
    stamps += [base + pd.Timedelta(minutes=5 * k) for k in range(c)]
stamps = pd.Series(stamps)
n_b = len(stamps)
chunks = core.calendar_day_chunks(stamps.values)

starts = [s for s, _ in chunks]; ends = [e for _, e in chunks]
check("P18 calendar-day chunks partition the stream exactly (contiguous, complete, disjoint)",
      len(chunks) == len(counts) and starts[0] == 0 and ends[-1] == n_b
      and all(ends[i] == starts[i + 1] for i in range(len(chunks) - 1))
      and [e - s for s, e in chunks] == counts,
      f"{len(chunks)} chunks of sizes {[e - s for s, e in chunks]} (expected {counts})")
check("P18 each chunk holds exactly one calendar date",
      all(stamps.iloc[s:e].dt.date.nunique() == 1 for s, e in chunks),
      "no chunk spans a day boundary")

# P19 the decisive one: replay the release schedule and assert nothing immature is ever handed over.
for h_b in [1, 2, 3, 6]:
    released, violations, released_rows = 0, [], []
    for (s, e) in chunks:
        end = core.matured_release_end(e, h_b, released, n_b)
        for i in range(released, end):
            released_rows.append(i)
            if i + h_b > e:                      # outcome not observable at the boundary
                violations.append((i, e))
        released = end
    check(f"P19 h={h_b}: no outcome is released before it matures",
          not violations,
          f"released {len(released_rows)} rows across {len(chunks)} chunks, 0 premature")
    check(f"P20 h={h_b}: every released row is released exactly once, in order",
          released_rows == sorted(set(released_rows)),
          f"{len(released_rows)} rows, strictly increasing, no duplicates")

# P19 negative control: the ARCHIVED fixed-row scheme must FAIL this same assertion, or the test is
# vacuous. This is the property version of the black-box witness in 2026-09-03-e3-baselines.py.
arch_chunks = core.fixed_row_chunks(n_b, 40)
arch_viol = [(i, e) for (s, e) in arch_chunks for i in range(s, e) if i + 3 > e]
check("P19 negative control: the archived fixed-row + whole-chunk scheme DOES violate it",
      len(arch_viol) > 0,
      f"{len(arch_viol)} premature releases at h=3 — the gate can actually detect C07")

# P21 reduction: at h = 1 every row in a chunk has matured by that chunk's boundary.
red_ok = all(core.matured_release_end(e, 1, s, n_b) == e for s, e in chunks)
check("P21 reduction: at h=1 the matured rule releases the whole chunk",
      red_ok, "matured_release_end(e, 1, ...) == e for every chunk")

# --------------------------------------------------------------------------------------
# P22-P24 — the X08 data-quality exclusion (revision 38, D-018). One tested definition, so the
# seven experiments it is applied to cannot each invent their own.
# --------------------------------------------------------------------------------------
import pandas as _pd

check("P22 a constant series is low-information",
      core.is_low_information([5.0] * 500), "1 distinct value < 10")
check("P22 a two-valued series is low-information (the actual X08 case: 0.0 and 109.0)",
      core.is_low_information([0.0] * 450 + [109.0] * 565), "2 distinct values < 10")
check("P22 a healthy series is NOT low-information",
      not core.is_low_information(list(range(64)) * 16), "64 distinct values >= 10")
check("P22 an all-NaN window is low-information rather than crashing",
      core.is_low_information([float("nan")] * 20), "empty after NaN drop -> True")
check("P22 NaNs do not mask a healthy series",
      not core.is_low_information(list(range(30)) + [float("nan")] * 30), "30 distinct values")

# P23 NEGATIVE CONTROL — the rule must be able to NOT fire. A filter that flags everything would
# satisfy every assertion above while destroying the analysis. (B11.)
_healthy = _pd.DataFrame({"facility_id": [1] * 100 + [2] * 100,
                          "occupancy": list(range(100)) + list(range(100))})
check("P23 negative control: the rule flags NOTHING on a frame of healthy facilities",
      core.low_information_facilities(_healthy) == [],
      "no facility excluded when none is degenerate — the filter can decline to fire")

_mixed = _pd.DataFrame({"facility_id": [1] * 100 + [2] * 100 + [3] * 100,
                        "occupancy": list(range(100)) + [7.0] * 100 + [0.0] * 50 + [9.0] * 50})
check("P23 the rule selects exactly the degenerate facilities and no others",
      core.low_information_facilities(_mixed) == [2, 3],
      "facility 1 (100 distinct) kept; 2 (1 distinct) and 3 (2 distinct) excluded")

# P24 THRESHOLD INSENSITIVITY — the property that makes this a data-quality rule rather than a tuned
# one (B16). On the real Belgrade test split the selection must be identical for every cutoff in
# [3, 60], because the distinct-value gap there is 2 -> 64.
_pq = Path(__file__).resolve().parents[2] / "01_data" / "processed" / "belgrade_features_v2.parquet"
if _pq.exists():
    _d = _pd.read_parquet(_pq)
    _te = _d[_d.split == "test"]
    _te = _te[_te["use_15"]] if "use_15" in _te.columns else _te
    _sel = {t: core.low_information_facilities(_te, min_distinct=t) for t in (3, 10, 30, 60)}
    check("P24 the X08 selection is identical for every threshold in [3, 60]",
          len({tuple(v) for v in _sel.values()}) == 1,
          f"all thresholds select {_sel[10]} — the cutoff carries no discretion")
    _counts = sorted(_te.groupby("facility_id").occupancy.nunique().values)
    check("P24 and the gap that guarantees it is still present in the data",
          _counts[1] < 3 <= 60 < _counts[2],
          f"distinct-value counts rise {_counts[0]} -> {_counts[1]} -> {_counts[2]}")
else:
    check("P24 SKIPPED — belgrade_features_v2.parquet not present", True, "no data to check against")

print("\n" + ("ALL CHECKS PASSED" if not FAIL else f"{len(FAIL)} CHECK(S) FAILED: {FAIL}"))
sys.exit(1 if FAIL else 0)
