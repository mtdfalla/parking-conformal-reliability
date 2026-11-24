#!/usr/bin/env python3
"""
Core checks for the revision 55/56 additions to `core.py` (register rows 4.1, 4.2, item 2.7; review findings 5, 6, 7).
Each check runs on the core under test AND, as its positive control (C29), on a version known to be wrong.
The control must make the check FAIL; a check that passes a wrong implementation is blind and the suite fails.

  V1  final-band rule: an inverted band is empty (covers nothing, even its midpoint), width 0       — row 4.2
  V2  final-band rule leaves every lo <= hi band bit for bit unchanged                               — row 4.2
  V3  count_inverted counts exactly the bands with lo > hi                                           — row 4.2
  V4  count_alpha_clipped counts exactly the steps on a projection bound                             — row 4.1
  V5  count_q_saturated counts exactly the steps whose quantile is the pool maximum by saturation    — finding 6
  V6  q-saturation binds before the projection bound (the two counters differ, as the review found)  — finding 6
  V7  gamma selection seeds cal-B only with scores observable at its first step (gap = horizon - 1)  — item 2.7
  V8  at horizon 1 the gamma selection is unchanged (no gap, the same pool as before)                — item 2.7 sanity

Run: python 2026-11-22-test_conformal_core_v3.py [--core PATH] [--old-core PATH]
"""
from __future__ import annotations
import argparse, importlib.util, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--core", default=str(HERE.parent / "src" / "conformal" / "core.py"))
ap.add_argument("--old-core", default=None, help="pre-fix core.py used as the positive control (default: the hash-locked one)")
args = ap.parse_args()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m

# The positive control needs the pre-fix core. Before promotion it is the hash-locked 03_code/src/conformal/
# core.py; after promotion it is the retired copy. The suite refuses to run if both resolve to the same file.
code_dir = next(p for p in HERE.parents if p.name == "03_code")
_cands = [code_dir / "src" / "conformal" / "_retired" / "2026-09-02-core-pre-v3.py",
          code_dir / "src" / "conformal" / "core.py"]
old_path = Path(args.old_core) if args.old_core else next(c for c in _cands if c.is_file() and
                                                           c.resolve() != Path(args.core).resolve())
args.core = str(Path(args.core).resolve()); old_path = old_path.resolve()
if old_path == Path(args.core): sys.exit("[core-v3] the control core is the core under test")
core = load(args.core, "core_under_test")
old = load(old_path, "core_old")
print(f"[core-v3] under test: {args.core}; control: {old_path}")

FAIL = []
def check(name, cond, detail=""):
    ok = bool(cond)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    if not ok: FAIL.append(name)

rng = np.random.default_rng(42)

# ---------------------------------------------------------------- V1-V3 final-band rule
def v1(mod):
    y = np.array([5.0, 5.0, 1.0]); lo = np.array([6.0, 4.0, 0.0]); hi = np.array([4.0, 6.0, 2.0])
    p, w, _ = mod.interval_metrics(y, lo, hi, 0.1)     # row 0 inverted, y at its midpoint
    return abs(p - 2/3) < 1e-12 and abs(w - (0 + 2 + 2) / 3) < 1e-12
def v2(mod):
    ok = True
    for _ in range(2000):
        n = rng.integers(1, 40); y = rng.normal(size=n) * 10
        lo = rng.normal(size=n) * 10; hi = lo + np.abs(rng.normal(size=n)) * 5
        a = mod.interval_metrics(y, lo, hi, 0.1); b = old.interval_metrics(y, lo, hi, 0.1)
        ok &= (a == b)
    return ok
def v3(mod, lo, hi):
    return mod.count_inverted(lo, hi) == int(np.sum(lo > hi))

print("=== V1-V3  final-band rule (row 4.2) ===")
check("V1 inverted band is empty: covers nothing (even its midpoint), width 0", v1(core))
check("V1 control: the pre-fix metric counts the midpoint as covered and a negative width", not v1(old))
check("V2 lo <= hi bands bit for bit unchanged against the pre-fix metric (2,000 random trials)", v2(core))
lo = rng.normal(size=5000); hi = lo + rng.normal(size=5000)
check("V3 count_inverted == number of lo > hi", v3(core, lo, hi), f"{int(np.sum(lo > hi))} of 5000")
class _Wrong:  # a counter that uses >= would count touching bands as empty
    count_inverted = staticmethod(lambda lo, hi: int(np.sum(np.asarray(lo) >= np.asarray(hi))))
lo2 = np.r_[lo, np.zeros(50)]; hi2 = np.r_[hi, np.zeros(50)]
check("V3 control: a '>=' counter is caught on 50 zero-width bands", v3(core, lo2, hi2) and not v3(_Wrong, lo2, hi2))

# ---------------------------------------------------------------- V4-V6 counters
print("\n=== V4-V6  clip-binding and quantile saturation (row 4.1, finding 6) ===")
B = (1e-3, 1 - 1e-3)
# 30 steps on the low bound, 20 on the high bound, 40 just INSIDE the bounds (5e-5 away), 500 interior
near = np.r_[np.full(20, B[0] + 5e-5), np.full(20, B[1] - 5e-5)]
a = np.r_[np.full(30, B[0]), np.full(20, B[1]), near, rng.uniform(0.002, 0.99, 500)]
check("V4 count_alpha_clipped == steps on a bound (40 steps 5e-5 inside the bounds not counted)",
      core.count_alpha_clipped(a) == 50, f"{core.count_alpha_clipped(a)} of 50")
tolerant = lambda x: int(np.sum((x < B[0] + 1e-4) | (x > B[1] - 1e-4)))   # a counter with a tolerance band
check("V4 control: a tolerance-band counter is caught (it counts the near-bound steps)", tolerant(a) != 50,
      f"tolerant counter gives {tolerant(a)}")

from fractions import Fraction
def exact_sat(alpha, pool):
    # Independent of the float formula: the order statistic the level asks for, in exact rational arithmetic,
    # lies beyond the pool, so core.conformal_k caps it at n (the pool maximum).
    c = 0
    for al, n in zip(alpha, pool):
        k = math.ceil(Fraction(int(n) + 1) * (1 - Fraction(float(al))))
        c += int(k > n)
    return c
alpha = rng.uniform(0.0005, 0.03, 4000); pool = rng.integers(40, 300, 4000)
got = core.count_q_saturated(alpha, pool)
check("V5 count_q_saturated == exact rational count of the level asking past the pool", got == exact_sat(alpha, pool),
      f"{got} of 4000")
capped = sum(1 for al, n in zip(alpha, pool) if core.conformal_k(int(n), float(al)) == n)
check("V5 every saturated step has its quantile at the pool maximum (conformal_k == n)", capped >= got,
      f"{capped} steps at k = n, {got} of them saturated")
over = int(np.sum(alpha < 0.01))
check("V5 control: an over-counting variant (alpha < 0.01) is caught", over != got, f"variant gives {over}")
wrong_ge = int(np.sum(np.ceil((pool + 1.0) * (1.0 - alpha)) >= pool))
check("V5 control: a '>=' variant (which also counts the exact k = n case) disagrees", wrong_ge != got,
      f"'>=' gives {wrong_ge}")
# The review's synthetic: an ACI stream driven to the low bound
st_y = np.r_[rng.normal(size=400), rng.normal(size=600) * 6]
lo_, hi_, dg = core.adaptive_conformal_stream(np.abs(rng.normal(size=120)), np.zeros(1000), np.zeros(1000), st_y,
                                               0.10, 1, gamma=0.05, return_state=True)
n_clip = core.count_alpha_clipped(dg["alpha"]); n_sat = core.count_q_saturated(dg["alpha"], dg["pool_size"])
check("V6 saturation binds before the bound: n_q_saturated > n_alpha_clipped on a hard shift, and the "
      "stream's own count agrees with the exact rational count",
      n_sat > n_clip > 0 and n_sat == exact_sat(dg["alpha"], dg["pool_size"]), f"saturated {n_sat}, clipped {n_clip}")

# ---------------------------------------------------------------- V7-V8 gamma-selection gap
print("\n=== V7-V8  gamma-selection seed pool (item 2.7) ===")
def probe(mod, h, n=400):
    seen = {}
    real = mod.adaptive_conformal_stream
    def spy(cal_scores, *a, **k):
        seen.setdefault("pool", np.array(cal_scores, float)); return real(cal_scores, *a, **k)
    mod.adaptive_conformal_stream = spy
    try:
        y = rng.normal(size=n); s = np.abs(y) + np.arange(n) * 1e-9     # distinct scores, so content is identifiable
        mod.select_gamma_on_calibration(s, np.zeros(n), np.zeros(n), y, 0.1, h)
    finally:
        mod.adaptive_conformal_stream = real
    cut = int(n * 0.5)
    pool = seen["pool"]
    # Content, not only length (review finding 2): the seed pool must be EXACTLY rows 0 .. cut-h, every one of
    # which resolves (row i at i + h) by cal-B's first step, row `cut`.
    rows = [int(np.flatnonzero(s == v)[0]) for v in pool]
    ok = bool(rows) and max(rows) + h <= cut and np.array_equal(pool, s[:cut - (h - 1)])
    return len(pool), cut, ok
_s = np.arange(400.0)
check("V7 control: the content test rejects a pool of the right length from the wrong rows (s[gap:cut])",
      not np.array_equal(_s[2:200], _s[:200 - 2]))
for h in (2, 3, 6):
    pool_n, cut, ok = probe(core, h)
    check(f"V7 h={h}: every seed score observable at cal-B's first step (pool {pool_n}, cut {cut})",
          ok and pool_n == cut - (h - 1))
    pool_o, _, ok_o = probe(old, h)
    check(f"V7 control h={h}: the pre-fix selection is caught seeding unobservable scores (pool {pool_o})", not ok_o)
pool_n, cut, ok = probe(core, 1); pool_o, _, _ = probe(old, 1)
check("V8 h=1: no gap, the same seed pool as the pre-fix selection", ok and pool_n == pool_o == cut)
y = rng.normal(size=400); s = np.abs(y)
ga, _ = core.select_gamma_on_calibration(s, np.zeros(400), np.zeros(400), y, 0.1, 1)
gb, _ = old.select_gamma_on_calibration(s, np.zeros(400), np.zeros(400), y, 0.1, 1)
check("V8 h=1: the chosen gamma is identical to the pre-fix selection", ga == gb, f"{ga} vs {gb}")

print(f"\n[core-v3] {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + "; ".join(FAIL)); sys.exit(1)
print("[core-v3] PASS")
