#!/usr/bin/env python3
"""EXP-044: facility sample-size guidance for the paper's two-level inference (D-041, A2).

Prespecified in `04_experiments/2026-11-23-facility-sample-size-PRESPECIFICATION.md`, written before any
number here was computed. Nothing in this file may be changed on the basis of its own output.

No model is fitted. The per-facility vectors come from the paper's own inference script
(`2026-09-04-phase4-inference.py`: `core_frame`, the exclusion sets, `t_legs`), imported, not re-implemented.
Gate first: the observed vectors must reproduce the logged population and contrast rows to 1e-9.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "05_results").is_dir() and (p / "03_code").is_dir())
SRC = ROOT / "03_code" / "src" / "conformal"
TAB = ROOT / "05_results" / "tables"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT / "04_experiments" / "2026-11-23-exp044" / "2026-11-23-exp044-facility-sample-size.csv")

SEED, B = 20261123, 4000
N_GRID = [10, 15, 21, 28, 40, 60, 80, 100, 150, 200]
DELTA_GRID = np.round(np.arange(0.0, 0.0600001, 0.0005), 4)
MU_GRID = np.round(np.arange(0.8800, 0.9300001, 0.0005), 4)
THR = {"primary": 0.05 / 4, "secondary": 0.05}
NOMINAL, EPS, POWER = 0.90, 0.02, 0.80


def load(path: Path, name: str):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P4 = load(SRC / "2026-09-04-phase4-inference.py", "phase4_inference")
EX = P4.load_script("2026-09-04-x08-reaggregate.py").exclusion_sets()
DROP = {"belgrade": EX[("belgrade", "use_15")], "birmingham": EX[("birmingham", "use_60")]}


def log(m):
    print(f"[exp044] {m}", flush=True)


def vectors():
    pop, con = {}, {}
    for city, hz, _ in P4.ROWS:
        d = P4.core_frame(city, hz, DROP[city])
        for m in P4.CORE_METHODS:
            pop[(city, m)] = d[d.method == m].PICP.dropna().values
        for a, b in P4.CONTRASTS:
            sa = d[d.method == a].set_index("facility_id").PICP.dropna()
            sb = d[d.method == b].set_index("facility_id").PICP.dropna()
            idx = sa.index.intersection(sb.index)
            va, vb = np.abs(sa.loc[idx].values - NOMINAL), np.abs(sb.loc[idx].values - NOMINAL)
            con[(city, f"{a} vs {b}")] = (va, vb)
    return pop, con


def gate(pop, con) -> bool:
    lp = pd.read_csv(TAB / "2026-09-04-phase4-population.csv")
    lc = pd.read_csv(TAB / "2026-09-04-phase4-contrasts.csv")
    fails = 0
    for (city, m), x in pop.items():
        L = lp[(lp.city == city) & (lp.method == m)].iloc[0]
        for got, exp in ((len(x), L.n_fac), (x.mean(), L.mean_PICP), (x.std(ddof=1), L.sd_PICP)):
            fails += abs(float(got) - float(exp)) > 1e-9
    for (city, c), (va, vb) in con.items():
        L = lc[(lc.city == city) & (lc.family == "D-dispersion") & (lc.contrast == c)].iloc[0]
        for got, exp in (((va - vb).mean(), L.mean_diff), (stats.wilcoxon(va, vb).pvalue, L.wilcoxon_p_raw)):
            fails += abs(float(got) - float(exp)) > 1e-9
    log(f"GATE: {2 * 3 * 4 + 2 * 2 * 4} checks, {fails} failures")
    return fails == 0


def e1_power(r, n, delta, rng_idx):
    X = r[rng_idx] - delta                                # B x n, adaptive better when negative
    p = stats.wilcoxon(X, axis=1, method="approx").pvalue
    neg = X.mean(axis=1) < 0
    return {k: float(((p < t) & neg).mean()) for k, t in THR.items()}


def safe_pass(X):
    n = X.shape[1]
    se = X.std(axis=1, ddof=1) / np.sqrt(n)
    return X.mean(axis=1) - stats.t.ppf(0.95, n - 1) * se >= NOMINAL - EPS


def tost_p(X):
    n = X.shape[1]
    m, se = X.mean(axis=1), X.std(axis=1, ddof=1) / np.sqrt(n)
    p_lo = stats.t.sf((m - (NOMINAL - EPS)) / se, n - 1)
    p_hi = stats.t.sf(((NOMINAL + EPS) - m) / se, n - 1)
    return np.maximum(p_lo, p_hi)


def main():
    pop, con = vectors()
    if not gate(pop, con):
        log("GATE FAILED: nothing written.")
        sys.exit(1)
    rng = np.random.default_rng(SEED)
    rows = []

    def add(city, fam, item, thr, qty, n, val):
        rows.append(dict(city=city, family=fam, item=item, threshold=thr, quantity=qty, n=n, value=val))

    for (city, c), (va, vb) in con.items():
        d = va - vb
        r, obs, n0 = d - d.mean(), -float(d.mean()), len(d)
        add(city, "E1", c, "", "observed_effect", n0, obs)
        idx = {n: rng.integers(0, n0, size=(B, n)) for n in N_GRID + [n0]}
        n80 = {k: None for k in THR}
        for n in N_GRID:
            pw = e1_power(r, n, obs, idx[n])
            for k, v in pw.items():
                add(city, "E1", c, k, "power_at_n", n, v)
                if n80[k] is None and v >= POWER:
                    n80[k] = n
        for k in THR:
            add(city, "E1", c, k, "n_for_80", n0, n80[k] if n80[k] is not None else np.nan)
        mde = {k: None for k in THR}
        for delta in DELTA_GRID:
            pw = e1_power(r, n0, delta, idx[n0])
            for k, v in pw.items():
                if mde[k] is None and v >= POWER:
                    mde[k] = float(delta)
            if all(v is not None for v in mde.values()):
                break
        for k in THR:
            add(city, "E1", c, k, "mde_at_paper_n", n0, mde[k] if mde[k] is not None else np.nan)

    for (city, m), x in pop.items():
        c0, n0 = x - x.mean(), len(x)
        idx = {n: rng.integers(0, n0, size=(B, n)) for n in N_GRID + [n0]}
        # 2026-11-23 fix after run 1: n0 is also on N_GRID, so run 1 wrote the paper-count row twice
        # (identical values, same draws). Each n is now visited once. No value changes.
        for n in N_GRID + ([] if n0 in N_GRID else [n0]):
            mde = next((float(mu - (NOMINAL - EPS)) for mu in MU_GRID
                        if safe_pass(c0[idx[n]] + mu).mean() >= POWER), np.nan)
            add(city, "E2", m, "", "mde_at_paper_n" if n == n0 else "mde_at_n", n, mde)
        n80 = {k: None for k in THR}
        for n in N_GRID:
            p = tost_p(c0[idx[n]] + NOMINAL)
            for k, t in THR.items():
                v = float((p < t).mean())
                add(city, "E3", m, k, "power_at_n", n, v)
                if n80[k] is None and v >= POWER:
                    n80[k] = n
        p0 = tost_p(c0[idx[n0]] + NOMINAL)
        for k, t in THR.items():
            add(city, "E3", m, k, "power_at_paper_n", n0, float((p0 < t).mean()))
            add(city, "E3", m, k, "n_for_80", n0, n80[k] if n80[k] is not None else np.nan)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    log(f"wrote {OUT.name}: {len(rows)} rows")
    log("ALL DONE")


if __name__ == "__main__":
    main()
