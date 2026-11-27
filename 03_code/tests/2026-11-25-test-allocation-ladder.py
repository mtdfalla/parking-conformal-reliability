#!/usr/bin/env python3
"""EXP-045 arm A2 (T009, T010, T011, T053): tests for the allocation-ladder successors.

  L1  `run_seed_rel(..., extra=...)` scores the shipped three policies exactly as `extra=None` does,
      on the same requests, so adding policies cannot move a shipped number
  L2  the added policies are scored on the same requests (same assigned distances where bounds agree)
  L3  `frames_identical`, the reproduction gate, passes identical frames and FAILS on a changed
      integer count, a changed float, a changed string and a changed shape (control: it can fail)
  L4  `frames_identical` counts a one-ulp float difference as storage precision, not as a mismatch
  L5  `cell_metrics` gives the hand-computed paired mean, sd, SE, seed count and share
  L6  `day_scopes` puts "all" first and partitions the slots by calendar day
  L7  `slot_diag` gives the hand-computed miss rates on a tiny matrix

Run: python 2026-11-25-test-allocation-ladder.py   (from anywhere, exit 0 means pass)
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

CONF = Path(__file__).resolve().parents[1] / "src" / "conformal"
sys.path.insert(0, str(CONF))
_s = importlib.util.spec_from_file_location("rel45", CONF / "2026-11-25-relative-threshold-allocation.py")
REL = importlib.util.module_from_spec(_s); _s.loader.exec_module(REL)

FAIL = []
def check(name, cond, detail=""):
    ok = bool(cond)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok: FAIL.append(name)


# ---- synthetic panel ----------------------------------------------------------------------------
rng = np.random.default_rng(7)
F, S_ = 6, 40
base = list(range(101, 101 + F))
coords = pd.DataFrame({"latitude": 44.80 + rng.uniform(0, 0.02, F),
                       "longitude": 20.45 + rng.uniform(0, 0.03, F)}, index=base)
cap = {f: float(c) for f, c in zip(base, rng.integers(80, 400, F))}
capv = np.array([cap[f] for f in base])
slots = pd.date_range("2017-03-18 12:00", periods=S_ // 2, freq="15min").append(
    pd.date_range("2017-03-19 12:00", periods=S_ // 2, freq="15min"))
YT = capv[None, :] * rng.uniform(0.6, 1.0, (S_, F))
YH = YT + rng.normal(0, 8, (S_, F))
UU = YH + rng.uniform(2, 15, (S_, F))
X = {"CQR-RAW": YH + 3.0, "SPLIT-CQR": YH + 7.0, "RF-SPLITCP": YH + 9.0}
anchor = base[:2]
m = float(np.mean(UU - YH))

print("L1/L2 the added policies do not move the shipped three")
for th in (0.85, 0.90, 0.95):
    for seed in (1, 2, 3):
        old = REL.run_seed_rel(seed, base, coords, cap, slots, YH, UU, YT, anchor, m, th)
        new = REL.run_seed_rel(seed, base, coords, cap, slots, YH, UU, YT, anchor, m, th, extra=X)
        same = all(o[k] == n[k] or (np.isnan(o[k]) and np.isnan(n[k]))
                   for o, n in zip(old, new[:3]) for k in o if isinstance(o[k], float))
        check(f"theta {th} seed {seed}: shipped three identical, 6 policies scored",
              same and [r["policy"] for r in new] == list(REL.POLICIES) and len(old) == 3)
# same requests: a policy whose bound equals POINT's must give POINT's numbers exactly
Xp = {"CQR-RAW": YH.copy(), "SPLIT-CQR": UU.copy(), "RF-SPLITCP": YH + m}
new = REL.run_seed_rel(4, base, coords, cap, slots, YH, UU, YT, anchor, m, 0.9, extra=Xp)
keys = ["bad_assignments_per_request", "mean_straight_line_km", "abstention_rate", "upper_miss_assigned"]
check("L2 a bound equal to POINT, INTERVAL or MARGIN reproduces that policy on the same requests",
      all(new[i][k] == new[j][k] for i, j in ((3, 0), (4, 1), (5, 2)) for k in keys))

print("L3/L4 the reproduction gate can fail, and treats one ulp as storage precision")
ref = pd.DataFrame({"policy": ["POINT", "INTERVAL"], "n_assigned": [600, 598], "x": [0.1, 1.377653861589198]})
check("identical frames pass", REL.frames_identical(ref, ref.copy(), "t")[:2] == (0, 0))
m1 = ref.copy(); m1.loc[1, "n_assigned"] = 597
check("CONTROL a changed integer count fails", REL.frames_identical(ref, m1, "t")[0] == 1)
m2 = ref.copy(); m2.loc[0, "x"] = 0.1 + 1e-6
check("CONTROL a changed float fails", REL.frames_identical(ref, m2, "t")[0] == 1)
m3 = ref.copy(); m3.loc[0, "policy"] = "MARGIN"
check("CONTROL a changed string fails", REL.frames_identical(ref, m3, "t")[0] == 1)
check("CONTROL a dropped row fails", REL.frames_identical(ref, ref.iloc[:1], "t")[0] > 0)
m4 = ref.copy(); m4.loc[1, "x"] = np.nextafter(ref.x[1], 2.0)
r4 = REL.frames_identical(ref, m4, "t")
check("one-ulp float difference counted as storage precision only", r4[:2] == (0, 1), str(r4))

print("L5 cell_metrics against hand computation")
pb = np.array([10, 12, 9, 15]) / 600; pi = np.array([1, 2, 0, 1]) / 600; pr = np.array([4, 2, 3, 5]) / 600
rows = []
for s, (a, b, c) in enumerate(zip(pb, pi, pr), start=1):
    for p, v in (("POINT", a), ("INTERVAL", b), ("CQR-RAW", c)):
        rows.append(dict(seed=s, policy=p, bad_assignments_per_request=v, mean_straight_line_km=1.0,
                         abstention_rate=0.0, upper_miss_assigned=0.05))
M = pd.DataFrame(REL.cell_metrics(pd.DataFrame(rows), n_req=600))
get = lambda p, c, k: float(M[(M.policy == p) & (M.comparator == c) & (M.metric == k)].value.iloc[0])
d = np.array([9, 10, 9, 14.0])
check("paired mean POINT minus INTERVAL", np.isclose(get("INTERVAL", "POINT", "d_bad_per600_mean"), d.mean()))
check("paired SE", np.isclose(get("INTERVAL", "POINT", "d_bad_per600_se"), d.std(ddof=1) / 2))
check("seeds where INTERVAL is better", get("INTERVAL", "POINT", "seeds_policy_better") == 4)
dr = np.array([6, 10, 6, 10.0])
check("share of the POINT-to-INTERVAL reduction", np.isclose(
    get("CQR-RAW", "POINT", "share_of_point_to_interval_reduction"), dr.mean() / d.mean()))
check("INTERVAL against CQR-RAW: 3 seeds better, 1 tied (seed 2 is 2 against 2)",
      get("INTERVAL", "CQR-RAW", "seeds_policy_better") == 3 and get("INTERVAL", "CQR-RAW", "seeds_tied") == 1)

print("L6 day_scopes")
sc = REL.day_scopes("weekend", slots)
check("weekend: all, then two days that partition the slots",
      [s[0] for s in sc] == ["all", "2017-03-18", "2017-03-19"] and sc[0][1].all()
      and (sc[1][1] ^ sc[2][1]).all() and sc[1][1].sum() == S_ // 2)
check("weekday: all only", [s[0] for s in REL.day_scopes("weekday", slots)] == ["all"])

print("L7 slot_diag")
yt = np.array([[5.0, 9.0], [7.0, 1.0]]); bar = np.array([[8.0, 8.0]])
B = {"POINT": np.array([[6.0, 7.0], [6.0, 2.0]])}
r = REL.slot_diag(B, yt, bar, yt >= bar)
check("withdraw, miss all, miss offered, event offered",
      r["withdraw_rate_POINT"] == 0.0 and r["upper_miss_all_POINT"] == 0.5
      and r["upper_miss_offered_POINT"] == 0.5 and r["event_rate_offered_POINT"] == 0.25)

print("\nFAILED: " + ", ".join(FAIL) if FAIL else "\nALL PASS")
sys.exit(1 if FAIL else 0)
