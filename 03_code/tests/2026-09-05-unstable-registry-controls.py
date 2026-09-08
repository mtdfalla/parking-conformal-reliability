#!/usr/bin/env python3
"""Negative controls for the unstable-cell registry (revision 45, EXP-036).

The registry lets `verify.py` report a MEASURED nondeterministic cell as known-unstable instead of as a
failure. That is one edit away from being a relaxed tolerance, which is on this project's forbidden list,
so the mechanism gets controls that prove it can still FAIL (B11). A gate that can only pass shows
nothing.

Four controls, each asserting the OPPOSITE of the behaviour the registry provides:
  C1  a registered cell at a RECORDED value                 -> excused   (the feature works at all)
  C2  a registered cell at a THIRD value                    -> FAILURE   (it pins values, not cells)
  C3  a registered cell's PICP, an `exact`-class column     -> FAILURE   (exact is never excused)
  C4  an UNREGISTERED cell in the same file and column      -> FAILURE   (it is cell-scoped)

Usage: python 03_code/tests/2026-09-05-unstable-registry-controls.py
Exit code 0 iff all four behave as asserted.
"""
from __future__ import annotations
import importlib.util, shutil, sys, tempfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verifymod", ROOT / "03_code" / "verify.py")
V = importlib.util.module_from_spec(spec); sys.modules["verifymod"] = V; spec.loader.exec_module(V)

NAME = "2026-09-03-e3-belgrade-per-facility.csv"
REF = ROOT / "05_results" / "reference" / NAME
SEL = dict(arm="A3_v2_daychunk", facility_id=8, method="AgACI-style")

def run(label, mutate, expect_fail):
    d = pd.read_csv(REF)
    m = (d.arm == SEL["arm"]) & (d.facility_id == SEL["facility_id"]) & (d.method == SEL["method"])
    assert m.sum() == 1, f"{label}: selector matched {m.sum()} rows, expected 1"
    mutate(d, m)
    with tempfile.TemporaryDirectory() as td:
        gen = Path(td) / NAME
        d.to_csv(gen, index=False)
        fails = V.compare_csv(gen, REF)
    got_fail = len(fails) > 0
    ok = (got_fail == expect_fail)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: "
          f"{'failure reported' if got_fail else 'no failure'} "
          f"(expected {'failure' if expect_fail else 'no failure'})")
    if fails and not expect_fail:
        for f in fails: print(f"          unexpected: {f}")
    return ok

def main():
    rules = V.unstable_rules(NAME)
    assert rules, "registry has no rule for this file — build it first"
    vals = {r["column"]: r["values"] for r in rules}
    print(f"registry: {len(rules)} rule(s); MPIW values {vals['MPIW']}")
    print("negative controls for the unstable-cell registry:")
    ok = True
    # C1 — the OTHER recorded value must be excused
    other = vals["MPIW"][1]
    other_w = vals["Winkler"][1]
    def c1(d, m):
        d.loc[m, "MPIW"] = other; d.loc[m, "Winkler"] = other_w
    ok &= run("C1 registered cell at a recorded value", c1, expect_fail=False)
    # C2 — a third value must FAIL
    ok &= run("C2 registered cell at a THIRD value",
              lambda d, m: d.update(pd.DataFrame({"MPIW": {d.index[m][0]: 99.0}})), expect_fail=True)
    # C3 — PICP is `exact` class and must never be excused
    ok &= run("C3 registered cell, PICP perturbed",
              lambda d, m: d.update(pd.DataFrame({"PICP": {d.index[m][0]: 0.5}})), expect_fail=True)
    # C4 — an unregistered facility in the same file and column must FAIL
    def c4(d, m):
        m2 = (d.arm == SEL["arm"]) & (d.facility_id == 9) & (d.method == SEL["method"])
        assert m2.sum() == 1
        d.update(pd.DataFrame({"MPIW": {d.index[m2][0]: 99.0}}))
    ok &= run("C4 UNREGISTERED cell, same file and column", c4, expect_fail=True)
    print("ALL CONTROLS PASS" if ok else "CONTROLS FAILED")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
