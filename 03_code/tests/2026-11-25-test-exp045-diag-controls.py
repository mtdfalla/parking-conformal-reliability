#!/usr/bin/env python3
"""Negative controls for the in-script controls of EXP-045 arms A6, A8 and A9.

Each new script stops with exit 1 and writes nothing when its control fails. This test feeds each
script one deliberately wrong input and requires exactly that behaviour, so the controls are shown
able to fail:
  A6 (2026-11-25-exp045-tod-cells.py): buckets on the target time (issue + 15 min) instead of the
     issue time. The split-CP and ACI cells must no longer reproduce the shipped ToD cell table.
  A8 (2026-11-25-exp045-normalised-winkler.py): the X08 exclusion not applied. The raw Winkler means
     must no longer equal the shipped X08 core headline.
  A9 (2026-11-25-exp045-representativeness.py): every test stream one row short. The stream lengths
     and timestamps must no longer match the shipped per-facility and per-row tables.
Run from the project root. Exit 0 only if all three controls fail as required.
"""
import importlib.util, sys, types
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "03_code" / "src" / "conformal"
TAB = ROOT / "05_results" / "tables"


def load(fname):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_")[:-3], CONF / fname)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def expect_stop(name, m, outs):
    for o in outs:
        setattr(m, o, TAB / f"_negctl_{name}_{o}.csv")
    code = 0
    try:
        m.main()
    except SystemExit as e:
        code = e.code
    written = [o for o in outs if getattr(m, o).exists()]
    for o in written:
        getattr(m, o).unlink()
    ok = code == 1 and not written
    print(f"{name}: exit {code}, outputs written {written}: {'control FAILS as required' if ok else 'BROKEN'}")
    return ok


res = []
m = load("2026-11-25-exp045-tod-cells.py")
_to = m.pd.to_datetime
m.pd = types.ModuleType("pandas_shifted"); m.pd.__dict__.update(pd.__dict__)   # a proxy, pandas itself untouched
m.pd.to_datetime = lambda x, *a, **k: (_to(x, *a, **k) + pd.Timedelta(minutes=15)
                                       if isinstance(x, pd.Series) else _to(x, *a, **k))
res.append(expect_stop("A6", m, ["OUT"]))

m = load("2026-11-25-exp045-normalised-winkler.py")
_ls = m.load_script
def _ls2(f):
    mod = _ls(f)
    if "x08" in f:
        e = mod.exclusion_sets
        mod.exclusion_sets = lambda: {k: [] for k in e()}
    return mod
m.load_script = _ls2
res.append(expect_stop("A8", m, ["OUT"]))

m = load("2026-11-25-exp045-representativeness.py")
_st = m.streams
m.streams = lambda df, hz, hmin: {f: t[:-1] for f, t in _st(df, hz, hmin).items()}
res.append(expect_stop("A9", m, ["OUT_RE", "OUT_HR", "OUT_LAG"]))

print("ALL PASS" if all(res) else "FAILED")
sys.exit(0 if all(res) else 1)
