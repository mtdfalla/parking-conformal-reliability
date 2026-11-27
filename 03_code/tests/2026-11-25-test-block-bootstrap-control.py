#!/usr/bin/env python3
"""Control for 2026-11-25-block-bootstrap.py (EXP-045 arm A7, T002, NEW-2).

  python 2026-11-25-test-block-bootstrap-control.py

1. Seed 42, Belgrade: the in-script control (four Belgrade rows, original columns, byte-identical to
   2026-11-22-block-bootstrap-belgrade.csv) passes and a file is written.
2. CONTROL that must fail: seed 43 gives different draws, the in-script control fails, the script exits non-zero
   and writes nothing.
3. Birmingham run alone equals the Birmingham rows of the both-cities table (no dependence on run order).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPT = ROOT / "03_code" / "src" / "conformal" / "2026-11-25-block-bootstrap.py"
BOTH = ROOT / "05_results" / "tables" / "2026-11-25-block-bootstrap-both-cities.csv"
fails = 0


def check(name, ok):
    global fails
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    fails += not ok


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=SCRIPT.parent)


with tempfile.TemporaryDirectory() as t:
    a = Path(t) / "a.csv"
    r = run("--city", "belgrade", "--out", str(a))
    check("seed 42: control passes and the table is written",
          r.returncode == 0 and "PASS, byte-identical" in r.stdout and a.exists())
    b = Path(t) / "b.csv"
    r = run("--city", "belgrade", "--seed", "43", "--out", str(b))
    check("CONTROL seed 43: control fails, exit non-zero, nothing written",
          r.returncode != 0 and "FAIL, differs" in r.stdout and not b.exists())
    c = Path(t) / "c.csv"
    r = run("--city", "birmingham", "--out", str(c))
    both = pd.read_csv(BOTH, dtype=str)
    alone = pd.read_csv(c, dtype=str)
    check("Birmingham alone equals the Birmingham rows of the both-cities table",
          r.returncode == 0 and alone.equals(both[both.city == "birmingham"].reset_index(drop=True)))

print(f"{fails} failures")
sys.exit(1 if fails else 0)
