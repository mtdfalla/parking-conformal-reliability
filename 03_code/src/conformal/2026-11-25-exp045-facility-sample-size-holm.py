#!/usr/bin/env python3
"""SUCCESSOR, 2026-11-25, EXP-045 arm A13 (findings T021, T022, with T014), built from
2026-11-23-exp044-facility-sample-size.py by tools/make_infer_a13_exp045_holm.py. What changed and why:
  1. --mode holm (default) adds E1 rows with threshold "holm": in each replicate the Holm procedure (family
     alpha 0.05, phase4's rule) is applied jointly to the four D-dispersion contrasts of a city. Facilities are
     resampled jointly, one B x n index draw applied to all four facility-aligned contrast vectors, so the
     contrasts keep their correlation. For a candidate effect delta on contrast k, only contrast k is shifted
     (centred residuals minus delta) and the other three stay at their centred residuals plus their observed
     means. Detection of k = Holm-adjusted p of k below 0.05 and the replicate mean of k negative (T021).
     The joint draw is the index draw the original already makes for the first contrast of the city, so the
     generator stream, and with it every E1 first-step, E2 and E3 row, is unchanged.
  2. --mode first-step writes only the original rows (first Holm step 0.0125, and 0.05). It is the control:
     it must reproduce 2026-11-23-exp044-facility-sample-size.csv byte for byte.
  3. In holm mode the settings (B, seed, grids, test method, thresholds, Monte Carlo error) are written to a
     sidecar <output stem>-settings.csv so the ESM can state them (T022).
  4. The output path defaults to a 2026-11-25 name and an existing file is never overwritten.
  --B overrides B for a timing probe only, never for a result.

Original header follows.

EXP-044: facility sample-size guidance for the paper's two-level inference (D-041, A2).

Prespecified in `04_experiments/2026-11-23-facility-sample-size-PRESPECIFICATION.md`, written before any
number here was computed. Nothing in this file may be changed on the basis of its own output.

No model is fitted. The per-facility vectors come from the paper's own inference script
(`2026-09-04-phase4-inference.py`: `core_frame`, the exclusion sets, `t_legs`), imported, not re-implemented.
Gate first: the observed vectors must reproduce the logged population and contrast rows to 1e-9.
"""
from __future__ import annotations

import argparse
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
_AP = argparse.ArgumentParser()
_AP.add_argument("out", nargs="?", default=None)
_AP.add_argument("--mode", choices=["holm", "first-step"], default="holm")
_AP.add_argument("--B", type=int, default=None, help="timing probe only")
_AP.add_argument("--overwrite", action="store_true", help="replace existing outputs (run_all.sh)")
_ARGS, _ = _AP.parse_known_args()
MODE = _ARGS.mode
OUT = Path(_ARGS.out) if _ARGS.out else (TAB / ("2026-11-25-exp045-facility-sample-size-holm.csv" if MODE == "holm"
                                                 else "2026-11-25-exp045-facility-sample-size-first-step.csv"))

SEED, B = 20261123, 4000
if _ARGS.B:
    B = _ARGS.B  # timing probe only, never a result
HOLM_ALPHA = 0.05
IDS, JOINT = {}, {}
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
            IDS[(city, f"{a} vs {b}")] = [int(i) for i in idx]
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


def holm_adjust(P):
    """Row-wise Holm adjusted p-values of a B x m array, order preserved (the rule of phase4 holm())."""
    m = P.shape[1]
    order = np.argsort(P, axis=1, kind="stable")
    ps = np.take_along_axis(P, order, axis=1)
    adj_s = np.minimum(1.0, np.maximum.accumulate(ps * (m - np.arange(m))[None, :], axis=1))
    adj = np.empty_like(P)
    np.put_along_axis(adj, order, adj_s, axis=1)
    return adj


def e1_holm_rows(city, names, con, add):
    """E1 under Holm over the four contrasts of a city, on the joint facility draws of JOINT[city]."""
    ids = [IDS[(city, c)] for c in names]
    if any(i != ids[0] for i in ids):
        raise SystemExit(f"[exp044] {city}: contrasts are not facility-aligned, joint resampling impossible")
    D = [con[(city, c)][0] - con[(city, c)][1] for c in names]
    R = [d - d.mean() for d in D]
    obs = [-float(d.mean()) for d in D]
    n0, J, K = len(D[0]), JOINT[city], len(names)

    def p_of(X):
        return stats.wilcoxon(X, axis=1, method="approx").pvalue

    def at_obs(n):                                        # every contrast at its observed mean
        Xs = [R[j][J[n]] - obs[j] for j in range(K)]
        return Xs, np.column_stack([p_of(X) for X in Xs])

    cache = {n: at_obs(n) for n in N_GRID + ([] if n0 in N_GRID else [n0])}
    for k, c in enumerate(names):
        n80 = None
        for n in N_GRID:
            Xs, P = cache[n]
            v = float(((holm_adjust(P)[:, k] < HOLM_ALPHA) & (Xs[k].mean(axis=1) < 0)).mean())
            add(city, "E1", c, "holm", "power_at_n", n, v)
            if n80 is None and v >= POWER:
                n80 = n
        add(city, "E1", c, "holm", "n_for_80", n0, n80 if n80 is not None else np.nan)
        _, P0 = cache[n0]
        mde = None
        for delta in DELTA_GRID:
            X = R[k][J[n0]] - delta
            P = P0.copy()
            P[:, k] = p_of(X)
            if float(((holm_adjust(P)[:, k] < HOLM_ALPHA) & (X.mean(axis=1) < 0)).mean()) >= POWER:
                mde = float(delta)
                break
        add(city, "E1", c, "holm", "mde_at_paper_n", n0, mde if mde is not None else np.nan)


def settings_rows(pop, con):
    n_fac = {city: len(x) for (city, _), x in pop.items()}
    mc = float(np.sqrt(POWER * (1 - POWER) / B))
    S = [("experiment", "EXP-045 arm A13, successor of EXP-044"),
         ("B", B), ("seed", SEED), ("generator", "numpy default_rng (PCG64)"),
         ("facility_counts_paper", ", ".join(f"{c} {n}" for c, n in n_fac.items())),
         ("n_grid", " ".join(str(n) for n in N_GRID)),
         ("delta_grid_E1", f"{DELTA_GRID[0]:.4f} to {DELTA_GRID[-1]:.4f} step 0.0005"),
         ("mu_grid_E2", f"{MU_GRID[0]:.4f} to {MU_GRID[-1]:.4f} step 0.0005"),
         ("resampling", "observed facility-level values resampled with replacement, iid over facilities, "
                        "location shift (plug-in, conditional on the test window, no shared time shocks)"),
         ("E1_test", "Wilcoxon signed-rank, two-sided, normal approximation with tie correction "
                     "(scipy wilcoxon method approx, zero_method wilcox)"),
         ("E1_detection", "adjusted or raw p below the threshold and replicate mean difference negative"),
         ("E1_threshold_holm", "Holm over the four D-dispersion contrasts of a city, family alpha 0.05, "
                               "facilities resampled jointly, other contrasts at their observed means"),
         ("E1_threshold_primary", "0.0125, the first Holm step (Bonferroni over four), conservative"),
         ("E1_threshold_secondary", "0.05 unadjusted, the most favourable case"),
         ("E2_rule", "one-sided 95% facility-clustered t lower bound at or above 0.88"),
         ("E3_test", "TOST, two one-sided t tests, margin 0.02 around 0.90, mean set to 0.90"),
         ("E3_thresholds", "primary 0.0125 (first Holm step over four methods), secondary 0.05"),
         ("power_target", POWER),
         ("mc_se_power_at_0.80", mc),
         ("esm_settings_line",
          f"Power was estimated by resampling the observed facility-level values with replacement "
          f"(B = {B} replicates per cell, seed {SEED}, facility counts {', '.join(str(n) for n in N_GRID)}). "
          f"Paired contrasts used the two-sided Wilcoxon signed-rank test with its normal approximation, "
          f"Holm-adjusted jointly over the four contrasts of a city on joint facility resamples. "
          f"Effects were searched from 0 to 0.06 in steps of 0.0005 and mean coverage from 0.88 to 0.93 in "
          f"steps of 0.0005. The Monte Carlo standard error of a power estimate near 0.80 is {mc:.4f}.")]
    return pd.DataFrame(S, columns=["setting", "value"])


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
        JOINT.setdefault(city, idx)                       # the first contrast's draw serves the joint Holm
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

    if MODE == "holm":
        for city in dict.fromkeys(c for c, _ in con):
            e1_holm_rows(city, [c for cc, c in con if cc == city], con, add)

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
    side = OUT.with_name(OUT.stem + "-settings.csv")
    for p in [OUT] + ([side] if MODE == "holm" else []):
        if p.exists() and not _ARGS.overwrite:
            log(f"{p} exists: not overwritten.")
            sys.exit(1)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    log(f"wrote {OUT.name}: {len(rows)} rows (mode {MODE}, B {B})")
    if MODE == "holm":
        st = settings_rows(pop, con)
        st.to_csv(side, index=False)
        log(f"wrote {side.name}: {len(st)} rows")
    log("ALL DONE")


if __name__ == "__main__":
    main()
