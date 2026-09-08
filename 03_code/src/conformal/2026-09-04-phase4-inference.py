#!/usr/bin/env python3
"""EXP-030 / R-Phase 4 — the two-level inference redesign (I01, I02, I03, I04, I06, D04).

Prespecified in `04_experiments/2026-09-04-rphase4-inference-PRESPECIFICATION.md`, written before any
number here was computed. Nothing in this file may be changed on the basis of its own output.

WHY THERE IS NO RE-FIT
----------------------
Audit I06 flagged `B = 500` with a fixed 20-row block. The logged R-Phase 3 run does not use that
design: `2026-09-02-run-core-methods.py` sets `BOOT_B = 10_000` and derives the block from cadence
(`core.block_length_for_cadence(cadence, 3.0)` -> 36 rows Belgrade, 6 Birmingham). So the per-facility
CIs on disk are already correct and R-Phase 4 is re-aggregation plus inference, exactly as the
remediation plan's fix-class table predicted. What is genuinely missing from I06 is multiplicity, which
is added here.

THE GATE IS THE NEGATIVE CONTROL (B11, B17, and the EXP-027 pattern)
--------------------------------------------------------------------
`--filter off` recomputes every aggregate from the logged per-facility CSVs with the exclusion OFF and
asserts it equals `2026-09-02-corrected-headline-gcal.csv` to 4 dp. If that fails, this file does not
match the logged aggregation and its filtered output is worthless. Nothing is patched into agreement,
and no filtered number is read until the control passes.

ONE DEFINITION (B9)
-------------------
The exclusion comes from `core.low_information_facilities`, reached by importing EXP-027's
`exclusion_sets()` rather than re-implementing it.

Nothing logged is overwritten. Outputs: 2026-09-04-phase4-{gate,population,facility,contrasts}.csv
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
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
sys.path.insert(0, str(HERE))
import core  # noqa: E402

# ---- prespecified constants, section 2 of the prespecification -------------------------
EPS = 0.02
NOMINAL = 0.90
ALPHA = 0.05
B_BOOT = 10_000
SEED = 42
CORE_METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
E3_METHODS = ["EnbPI", "AgACI-style", "NGBoost", "NGBoost-conformal"]  # exploratory, no p-values
ROWS = [("belgrade", "y_t+15min", "use_15"), ("birmingham", "y_t+60min", "use_60")]
CONTRASTS = [("ACI", "split-CP"), ("ACI", "CQR"), ("ACQR", "CQR"), ("ACQR", "split-CP")]


def log(m):
    print(f"[phase4] {m}", flush=True)


def load_script(fname: str):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_")[:-3], HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- inference primitives --------------------------------------------------------------

def t_legs(x: np.ndarray):
    """Facility-clustered t-interval. Returns (mean, sd, se, lo90, hi90, lower95_onesided, tost_p)."""
    n = len(x)
    m, sd = float(np.mean(x)), float(np.std(x, ddof=1))
    se = sd / np.sqrt(n)
    tcrit = stats.t.ppf(0.95, n - 1)          # 90% two-sided == TOST at alpha=0.05
    lo, hi = m - tcrit * se, m + tcrit * se
    lower95 = m - tcrit * se                   # one-sided 95% lower bound: same critical value
    p_lo = stats.t.sf((m - (NOMINAL - EPS)) / se, n - 1)   # H0: mean <= 0.88
    p_hi = stats.t.sf(((NOMINAL + EPS) - m) / se, n - 1)   # H0: mean >= 0.92
    return m, sd, se, float(lo), float(hi), float(lower95), float(max(p_lo, p_hi))


def boot_legs(x: np.ndarray, seed: int = SEED):
    """Facility bootstrap, resampling facilities with replacement. (lo90, hi90, lower95)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    idx = rng.integers(0, n, size=(B_BOOT, n))
    means = x[idx].mean(axis=1)
    return (float(np.percentile(means, 5)), float(np.percentile(means, 95)),
            float(np.percentile(means, 5)))


def boot_diff(d: np.ndarray, seed: int = SEED):
    """Paired facility bootstrap on a per-facility difference. (mean, lo95, hi95, p_two_sided)."""
    rng = np.random.default_rng(seed)
    n = len(d)
    idx = rng.integers(0, n, size=(B_BOOT, n))
    means = d[idx].mean(axis=1)
    p = 2.0 * min((means >= 0).mean(), (means <= 0).mean())
    return float(np.mean(d)), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float(p)


def holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, order preserved."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m, dtype=float)
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return [float(v) for v in adj]


# ---- data ------------------------------------------------------------------------------

def core_frame(city: str, hz: str, drop: list) -> pd.DataFrame:
    d = pd.read_csv(TAB / f"2026-09-02-core-{city}-gcal-per-facility.csv")
    d = d[(d.horizon == hz) & (d.level == 0.90) & (d.dynamic)]
    if drop:
        d = d[~d.facility_id.isin(drop)]
    # 2026-09-05 (revision 44, EXP-035): SORT BEFORE ANY BOOTSTRAP. The facility-clustered moving-block
    # bootstrap resamples the per-facility vector IN FILE ORDER, so the CI bounds depended on the order
    # of rows in the input CSV. A from-scratch run writes the E3 arms in a different order from the
    # archived file (`A3_v2_daychunk` first rather than `A12_v1_paired` first), and the four exploratory
    # E3 rows' bootstrap bounds moved by up to 1e-3 relative while mean_PICP, sd_PICP and every
    # t-based bound were BIT-IDENTICAL -- which is exactly the signature of an order dependence and not
    # of a numerical one. Sorting by facility_id makes the bounds a function of the data alone. This is
    # EXP-032's order finding one level deeper: there a row order broke a COMPARISON, here it reached a
    # COMPUTED number. Lesson C15.
    d = d.sort_values("facility_id", kind="stable").reset_index(drop=True)
    return d


def e3_frame(city: str, hz: str, drop: list) -> pd.DataFrame:
    d = pd.read_csv(TAB / f"2026-09-03-e3-{city}-per-facility.csv")
    d = d[(d.arm == "A3_v2_daychunk") & (d.dynamic) & (d.degenerate != True) & (d.status == "ok")
          & (d.horizon == hz) & (d.level == 0.9)]
    if drop:
        d = d[~d.facility_id.isin(drop)]
    # 2026-09-05 (revision 44, EXP-035): SORT BEFORE ANY BOOTSTRAP. The facility-clustered moving-block
    # bootstrap resamples the per-facility vector IN FILE ORDER, so the CI bounds depended on the order
    # of rows in the input CSV. A from-scratch run writes the E3 arms in a different order from the
    # archived file (`A3_v2_daychunk` first rather than `A12_v1_paired` first), and the four exploratory
    # E3 rows' bootstrap bounds moved by up to 1e-3 relative while mean_PICP, sd_PICP and every
    # t-based bound were BIT-IDENTICAL -- which is exactly the signature of an order dependence and not
    # of a numerical one. Sorting by facility_id makes the bounds a function of the data alone. This is
    # EXP-032's order finding one level deeper: there a row order broke a COMPARISON, here it reached a
    # COMPUTED number. Lesson C15.
    d = d.sort_values("facility_id", kind="stable").reset_index(drop=True)
    return d


# ---- the gate --------------------------------------------------------------------------

def logged_path(name: str) -> Path:
    """Locate an ARCHIVED logged artifact that no step regenerates.

    2026-09-05 (revision 44, EXP-035). `2026-09-02-corrected-headline-gcal.csv` was produced ad hoc in an
    earlier stage and has no writer anywhere in the tree (the same provenance class as
    `2026-09-03-e3-summary.csv`; see `2026-09-04-x08-reaggregate.py`'s header). In the REPOSITORY it sits
    in `05_results/tables/`, so this gate found it. In the SHIPPED PACKAGE `05_results/tables/` is the
    replicator's own empty output directory and our outputs live in `05_results/reference/`, so a
    from-scratch run raised FileNotFoundError here and the step failed. Found by the clean-room run, not
    by reading the code (C12).

    Preferring tables/ and falling back to reference/ is deliberate: the replicator's own file wins where
    one exists, and the archived reference is used only where nothing regenerates it. It must NEVER be
    inverted, and the archived file must never be copied INTO tables/ — pre-seeding a replicator's output
    directory with our numbers would let a run "reproduce" a file we handed them.
    """
    p = TAB / name
    return p if p.exists() else (ROOT / "05_results" / "reference" / name)


def gate(out_csv: Path) -> bool:
    """Reproduce the logged headline summary with the exclusion OFF, to 4 dp."""
    logged = pd.read_csv(logged_path("2026-09-02-corrected-headline-gcal.csv"))
    checks, fails = [], 0
    for city, hz, _ in ROWS:
        d = core_frame(city, hz, [])
        for meth in CORE_METHODS:
            s = d[d.method == meth]
            L = logged[(logged.city == city) & (logged.horizon == hz) & (logged.method == meth)].iloc[0]
            for stat, got in (("PICP", s.PICP.mean()), ("std", s.PICP.std()),
                              ("MPIW", s.MPIW.mean()), ("Winkler", s.Winkler.mean()),
                              ("ci_contains", ((s.picp_ci_lo <= 0.90) & (s.picp_ci_hi >= 0.90)).mean()),
                              ("safe", (s.picp_ci_lo >= 0.88).mean()),
                              ("n", float(s.facility_id.nunique()))):
                exp = float(L[stat])
                ok = abs(float(got) - exp) < 5e-5
                fails += (not ok)
                checks.append(dict(city=city, horizon=hz, method=meth, statistic=stat,
                                   logged=exp, recomputed=float(got), ok=bool(ok)))
    pd.DataFrame(checks).to_csv(out_csv, index=False)
    log(f"GATE: {len(checks)} checks, {fails} failures -> {out_csv.name}")
    return fails == 0


# ---- stage 1 ---------------------------------------------------------------------------

def population(drop_map: dict) -> pd.DataFrame:
    out = []
    for city, hz, _ in ROWS:
        drop = drop_map.get(city, [])
        core_d = core_frame(city, hz, drop)
        e3_d = e3_frame(city, hz, drop)
        prim = []
        for meth in CORE_METHODS:
            x = core_d[core_d.method == meth].PICP.dropna().values
            m, sd, se, lo, hi, low95, tost_p = t_legs(x)
            blo, bhi, blow95 = boot_legs(x)
            prim.append(dict(
                city=city, horizon=hz, method=meth, family="P-primary", exploratory=False,
                n_fac=len(x), mean_PICP=m, sd_PICP=sd, se=se,
                t_lo90=lo, t_hi90=hi, t_lower95=low95,
                boot_lo90=blo, boot_hi90=bhi, boot_lower95=blow95,
                EXACT_t=bool(lo >= NOMINAL - EPS and hi <= NOMINAL + EPS),
                EXACT_boot=bool(blo >= NOMINAL - EPS and bhi <= NOMINAL + EPS),
                SAFE_t=bool(low95 >= NOMINAL - EPS), SAFE_boot=bool(blow95 >= NOMINAL - EPS),
                tost_p_raw=tost_p, mean_Winkler=float(core_d[core_d.method == meth].Winkler.mean())))
        adj = holm([r["tost_p_raw"] for r in prim])
        for r, a in zip(prim, adj):
            r["tost_p_holm"] = a
            r["EXACT_holm"] = bool(a < ALPHA)
        out.extend(prim)
        for meth in E3_METHODS:
            x = e3_d[e3_d.method == meth].PICP.dropna().values
            if len(x) < 3:
                continue
            m, sd, se, lo, hi, low95, _ = t_legs(x)
            blo, bhi, blow95 = boot_legs(x)
            out.append(dict(
                city=city, horizon=hz, method=meth, family="exploratory", exploratory=True,
                n_fac=len(x), mean_PICP=m, sd_PICP=sd, se=se,
                t_lo90=lo, t_hi90=hi, t_lower95=low95,
                boot_lo90=blo, boot_hi90=bhi, boot_lower95=blow95,
                EXACT_t=bool(lo >= NOMINAL - EPS and hi <= NOMINAL + EPS),
                EXACT_boot=bool(blo >= NOMINAL - EPS and bhi <= NOMINAL + EPS),
                SAFE_t=bool(low95 >= NOMINAL - EPS), SAFE_boot=bool(blow95 >= NOMINAL - EPS),
                tost_p_raw=np.nan, tost_p_holm=np.nan, EXACT_holm=None,
                mean_Winkler=float(e3_d[e3_d.method == meth].Winkler.mean())))
    return pd.DataFrame(out)


def facility(drop_map: dict) -> pd.DataFrame:
    out = []
    for city, hz, _ in ROWS:
        d = core_frame(city, hz, drop_map.get(city, []))
        for meth in CORE_METHODS:
            s = d[d.method == meth].dropna(subset=["PICP"])
            hw = (s.picp_ci_hi - s.picp_ci_lo) / 2.0
            worst = s.loc[s.PICP.idxmin()]
            out.append(dict(
                city=city, horizon=hz, method=meth, n_fac=int(s.facility_id.nunique()),
                sd_PICP=float(s.PICP.std()),
                worst_facility=int(worst.facility_id), worst_PICP=float(worst.PICP),
                frac_unsafe=float((s.picp_ci_lo < NOMINAL - EPS).mean()),
                frac_below_nominal=float((s.PICP < NOMINAL).mean()),
                median_CI_halfwidth=float(hw.median()), max_CI_halfwidth=float(hw.max()),
                RETIRED_ci_contains_nominal=float(((s.picp_ci_lo <= NOMINAL)
                                                   & (s.picp_ci_hi >= NOMINAL)).mean()),
                equivalence_claimed=False))
    return pd.DataFrame(out)


def contrasts(drop_map: dict) -> pd.DataFrame:
    out = []
    for city, hz, _ in ROWS:
        d = core_frame(city, hz, drop_map.get(city, []))
        for fam, col, transform in (("D-dispersion", "PICP", lambda v: np.abs(v - NOMINAL)),
                                    ("E-efficiency", "Winkler", lambda v: v)):
            block = []
            for a, b in CONTRASTS:
                sa = d[d.method == a].set_index("facility_id")[col].dropna()
                sb = d[d.method == b].set_index("facility_id")[col].dropna()
                idx = sa.index.intersection(sb.index)
                va, vb = transform(sa.loc[idx].values), transform(sb.loc[idx].values)
                diff = va - vb
                w_p = float(stats.wilcoxon(va, vb).pvalue)
                mdiff, blo, bhi, bp = boot_diff(diff)
                block.append(dict(
                    city=city, horizon=hz, family=fam, contrast=f"{a} vs {b}",
                    n_fac=len(idx), mean_a=float(np.mean(va)), mean_b=float(np.mean(vb)),
                    mean_diff=mdiff, boot_lo95=blo, boot_hi95=bhi, boot_p=bp,
                    pct_facilities_favouring_a=float((diff < 0).mean() * 100.0),
                    wilcoxon_p_raw=w_p))
            adj = holm([r["wilcoxon_p_raw"] for r in block])
            for r, a_ in zip(block, adj):
                r["wilcoxon_p_holm"] = a_
                r["significant_holm_005"] = bool(a_ < ALPHA)
            out.extend(block)
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", choices=["on", "off"], required=True,
                    help="'off' runs the gate only: it must reproduce the logged summary to 4 dp")
    a = ap.parse_args()

    ok = gate(TAB / "2026-09-04-phase4-gate.csv")
    if a.filter == "off":
        log("control arm only; no filtered number was computed or read.")
        log("ALL DONE" if ok else "GATE FAILED — stop.")
        return
    if not ok:
        log("GATE FAILED — refusing to compute the filtered arm.")
        sys.exit(1)

    reagg = load_script("2026-09-04-x08-reaggregate.py")
    ex = reagg.exclusion_sets()
    drop_map = {"belgrade": ex[("belgrade", "use_15")], "birmingham": ex[("birmingham", "use_60")]}
    log(f"exclusion sets (computed, never hardcoded): {drop_map}")

    population(drop_map).to_csv(TAB / "2026-09-04-phase4-population.csv", index=False)
    facility(drop_map).to_csv(TAB / "2026-09-04-phase4-facility.csv", index=False)
    contrasts(drop_map).to_csv(TAB / "2026-09-04-phase4-contrasts.csv", index=False)
    log("wrote 2026-09-04-phase4-{population,facility,contrasts}.csv")
    log("ALL DONE")


if __name__ == "__main__":
    main()
