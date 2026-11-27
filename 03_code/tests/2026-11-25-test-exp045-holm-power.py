#!/usr/bin/env python3
"""Test and controls for 2026-11-25-exp045-facility-sample-size-holm.py (EXP-045 arm A13, T021, T022).

  python 2026-11-25-test-exp045-holm-power.py

1. The vectorised Holm adjustment equals phase4 holm() exactly on random rows with ties.
   Control: a Bonferroni adjustment fails the same check.
2. Revision 61 (59b review note 8): the test RUNS the successor, in-process, into a temporary folder, and compares
   its FULL output (every row, the "holm" rows included) and its settings sidecar with the shipped references in
   05_results/reference/ under verify.py's own tolerance rule (and reports byte identity). The holm-mode output
   without its "holm" rows, and the first-step output, must equal the shipped EXP-044 table byte for byte.
   Control: the same successor with its Holm step replaced by Bonferroni (one function swapped, nothing else)
   must FAIL the full-output comparison, in the "holm" rows only, so the comparison can detect a code change.
3. On the first contrast of each city (whose joint draw is its own first-step draw), Holm power lies between
   the first-step power and the unadjusted 0.05 power at every n, as it must on identical draws.
4. Revision 61: an independent re-derivation of every "holm" power_at_n row and n_for_80 row. The joint
   facility draws are re-drawn from the seed, the Wilcoxon p-values recomputed, and each replicate adjusted with
   phase4 holm() row by row (not the vectorised holm_adjust). Every value must equal the shipped table exactly.
"""
import tempfile
import importlib.util
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "03_code" / "src" / "conformal"
TAB = ROOT / "05_results" / "tables"
SHIPPED = TAB / "2026-11-23-exp044-facility-sample-size.csv"
HOLM = TAB / "2026-11-25-exp045-facility-sample-size-holm.csv"
FIRST = TAB / "2026-11-25-exp045-facility-sample-size-first-step.csv"

fails = 0


def check(name, ok):
    global fails
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    fails += not ok


argv = sys.argv
sys.argv = ["x", "/tmp/never-written.csv", "--mode", "first-step"]
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location("e45", SRC / "2026-11-25-exp045-facility-sample-size-holm.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
sys.argv = argv

# 1. Holm adjustment
rng = np.random.default_rng(7)
P = rng.uniform(0, 0.2, size=(2000, 4))
P[::5, 1] = P[::5, 0]                                   # ties
P[::7] = np.round(P[::7], 2)
ref = np.array([E.P4.holm(list(row)) for row in P])
check("holm_adjust equals phase4 holm() on 2000 rows", np.array_equal(E.holm_adjust(P), ref))
check("CONTROL: Bonferroni does not equal phase4 holm()", not np.array_equal(np.minimum(1, 4 * P), ref))

# 2. the successor's full output against the shipped references (revision 61)
sys.path.insert(0, str(ROOT / "03_code"))
import verify as V                                       # the shipped tolerance rule, not a new one
REF = ROOT / "05_results" / "reference"
REF_HOLM = REF / "2026-11-25-exp045-facility-sample-size-holm.csv"
REF_SET = REF / "2026-11-25-exp045-facility-sample-size-holm-settings.csv"
REF_SHIP = REF / "2026-11-23-exp044-facility-sample-size.csv"
tmp = Path(tempfile.mkdtemp(prefix="holm-test-"))


def run_successor(out, mode):
    E.MODE, E.OUT = mode, out
    E._ARGS.overwrite = True
    buf = io.StringIO(); so = sys.stdout; sys.stdout = buf
    try:
        E.main()
    finally:
        sys.stdout = so
    return out


ship = REF_SHIP.read_bytes()
got = run_successor(tmp / "holm.csv", "holm")
side = tmp / "holm-settings.csv"
f_full = V.compare_csv(got, REF_HOLM)
check("successor holm-mode FULL output equals the shipped reference (verify.py tolerance rule)", not f_full)
check("successor settings sidecar equals the shipped reference", not V.compare_csv(side, REF_SET))
print(f"       byte-identical: holm {got.read_bytes() == REF_HOLM.read_bytes()}, "
      f"settings {side.read_bytes() == REF_SET.read_bytes()}")
h = pd.read_csv(got, dtype=str, keep_default_na=False)
check("holm-mode output minus holm rows is byte-identical to the shipped EXP-044 table",
      h[h.threshold != "holm"].to_csv(index=False).encode() == ship)
first = run_successor(tmp / "first.csv", "first-step")
check("first-step output is byte-identical to the shipped EXP-044 table", first.read_bytes() == ship)
_real = E.holm_adjust
E.holm_adjust = lambda P: np.minimum(1.0, P * P.shape[1])   # CONTROL: Bonferroni in the joint step
try:
    mut = run_successor(tmp / "mutant.csv", "holm")
finally:
    E.holm_adjust = _real
f_mut = V.compare_csv(mut, REF_HOLM)
m = pd.read_csv(mut, dtype=str, keep_default_na=False); r = pd.read_csv(REF_HOLM, dtype=str, keep_default_na=False)
diff_rows = (m != r).any(axis=1)
check(f"CONTROL: the Bonferroni mutant fails the full-output comparison ({int(diff_rows.sum())} rows differ)", bool(f_mut))
check("CONTROL: the mutant differs in holm rows only", bool(diff_rows.any()) and set(m[diff_rows].threshold) == {"holm"})

# 3. bounds on identical draws
d = pd.read_csv(REF_HOLM, float_precision="round_trip")
for city in ["belgrade", "birmingham"]:
    c = "ACI vs split-CP"
    q = d[(d.city == city) & (d.item == c) & (d.quantity == "power_at_n")].pivot(index="n", columns="threshold",
                                                                                values="value")
    check(f"{city} {c}: primary <= holm <= secondary at every n",
          bool(((q.primary <= q.holm) & (q.holm <= q.secondary)).all()))

# 4. independent re-derivation of the holm power rows (revision 61)
from scipy import stats
pop, con = E.vectors()
rng = np.random.default_rng(E.SEED)
joint = {}
for (city, c), (va, vb) in con.items():                  # the successor's draw order: one dict per contrast
    n0 = len(va)
    idx = {n: rng.integers(0, n0, size=(E.B, n)) for n in E.N_GRID + [n0]}
    joint.setdefault(city, idx)
n_bad, n_chk = 0, 0
for city in dict.fromkeys(cc for cc, _ in con):
    names = [c for cc, c in con if cc == city]
    D = [con[(city, c)][0] - con[(city, c)][1] for c in names]
    R = [x - x.mean() for x in D]
    for n in E.N_GRID:
        Xs = [R[j][joint[city][n]] + D[j].mean() for j in range(len(names))]
        P = np.column_stack([stats.wilcoxon(X, axis=1, method="approx").pvalue for X in Xs])
        A = np.array([E.P4.holm(list(row)) for row in P])
        for k, c in enumerate(names):
            v = float(((A[:, k] < E.HOLM_ALPHA) & (Xs[k].mean(axis=1) < 0)).mean())
            row = d[(d.city == city) & (d.item == c) & (d.threshold == "holm") & (d.quantity == "power_at_n") & (d.n == n)]
            n_chk += 1; n_bad += int(len(row) != 1 or float(row.value.iloc[0]) != v)
    for c in names:
        pw = d[(d.city == city) & (d.item == c) & (d.threshold == "holm") & (d.quantity == "power_at_n")].sort_values("n")
        hit = pw[pw.value >= E.POWER]
        n80 = float(hit.n.iloc[0]) if len(hit) else np.nan
        tab = d[(d.city == city) & (d.item == c) & (d.threshold == "holm") & (d.quantity == "n_for_80")].value.iloc[0]
        n_chk += 1; n_bad += int(not ((np.isnan(n80) and np.isnan(tab)) or n80 == tab))
check(f"independent re-derivation (phase4 holm, row by row) equals the shipped holm rows: {n_chk} values, {n_bad} differ",
      n_bad == 0)
import shutil
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if fails else 0)
