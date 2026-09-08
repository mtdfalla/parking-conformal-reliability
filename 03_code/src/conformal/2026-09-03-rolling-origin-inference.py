#!/usr/bin/env python3
"""
R-Phase 3b task 5 — facility-clustered inference for the rolling-origin run. Audit issue I04.
Companion to `2026-09-03-rolling-origin.py`. Logged as EXP-026.

WHY THIS IS A SEPARATE SCRIPT
-----------------------------
The run script emits per-fold-per-facility rows and takes no inferential position. All inference lives
here, so the estimand can be re-read against the prespecification without re-running any model.

THE DEFECT (I04). The archived script ran `wilcoxon` on 66 fold-facility rows. Each of 22 facilities
appears in 3 folds, so the 66 rows are not 66 independent replicates and the resulting p < 1e-10 is
anti-conservative. Fixed by taking the FACILITY as the unit: average |PICP - 0.90| within a facility
across its folds, then test at n = 22, Holm-corrected across the four prespecified contrasts, with a
facility-clustered bootstrap as confirmation.

The archived pooled test is recomputed here too — not as evidence, but so the size of its
anti-conservatism is measured rather than asserted.

Plan fixed in advance: `04_experiments/2026-09-03-rolling-origin-PRESPECIFICATION.md`.
Output: 05_results/tables/2026-09-03-rolling-origin-{foldsummary,inference}.csv
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
# Holm is implemented below rather than imported: it is six lines, and adding statsmodels would put an
# unpinned dependency in the critical path of a published p-value (LESSONS_LOG A13).

ROOT = Path(__file__).resolve().parents[3]
TAB = ROOT / "05_results" / "tables"
SRC = TAB / "2026-09-03-rolling-origin-belgrade.csv"
LEVEL = 0.90
SEED = 42
B = 10_000
CONTRASTS = [("ACI", "split-CP"), ("ACI", "CQR"), ("ACQR", "CQR"), ("ACQR", "split-CP")]


def log(m): print(f"[infer] {m}", flush=True)


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, order preserved."""
    p = np.asarray(pvals, float); m = len(p)
    order = np.argsort(p)
    adj = np.empty(m); running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * p[idx]
        running = max(running, val)
        adj[idx] = min(running, 1.0)
    return adj


def cluster_bootstrap(per_fac_a, per_fac_b, rng):
    """Resample FACILITIES with replacement (never fold-facility rows) and bootstrap the mean paired
    difference. Returns (mean_diff, lo95, hi95, two_sided_p)."""
    diff = per_fac_a - per_fac_b
    n = len(diff)
    boot = np.empty(B)
    for b in range(B):
        boot[b] = diff[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    # two-sided bootstrap p: how often the resampled mean sits on the other side of zero
    frac = min((boot >= 0).mean(), (boot <= 0).mean())
    return float(diff.mean()), float(lo), float(hi), float(min(1.0, 2 * frac))


def main():
    d = pd.read_csv(SRC)
    d = d[d.method != "SKIPPED-thin"]

    # ---- primary population, fixed in the prespecification --------------------------------------
    units = d.drop_duplicates(["fold", "facility_id"])
    dyn_all = sorted(set.intersection(*[set(g[g.dynamic_fold].facility_id)
                                        for _, g in units.groupby("fold")]))
    log(f"primary population: facilities dynamic in ALL folds, n={len(dyn_all)}")

    def arm(gamma_mode, facs, drop_degenerate=True):
        s = d[d.facility_id.isin(facs)]
        if drop_degenerate:
            s = s[~s.degenerate]
        # adaptive methods take the requested gamma arm; split-CP/CQR are gamma-free
        return s[(s.gamma_mode == gamma_mode) | (s.gamma_mode.isna()) | (s.gamma_mode == "n/a")]

    out_fold, out_inf = [], []

    # X08 (revision 38): facility 8's test window carries two distinct occupancy values. The exclusion
    # rule is NOT yet adopted, so the primary population still includes it and the excluded arm is
    # reported alongside as a robustness check. See EXP-026.
    x08 = [8]
    for gamma_mode in ["calibrated", "fixed05"]:
        for popname, facs in [("dynamic_all_folds", dyn_all),
                              ("dynamic_all_folds_x08excl", [f for f in dyn_all if f not in x08]),
                              ("all_facilities", sorted(units.facility_id.unique()))]:
            a = arm(gamma_mode, facs)
            if a.empty:
                continue
            # ---- fold-level descriptive summary --------------------------------------------
            for (fold, meth), g in a.groupby(["fold", "method"]):
                out_fold.append(dict(
                    gamma_mode=gamma_mode, population=popname, fold=fold, method=meth,
                    n_fac=len(g), mean_PICP=round(g.PICP.mean(), 4),
                    sd_PICP=round(g.PICP.std(ddof=0), 4),
                    min_PICP=round(g.PICP.min(), 4),
                    frac_within_02=round(float(np.mean(np.abs(g.PICP - LEVEL) <= 0.02)), 4),
                    mean_MPIW=round(g.MPIW.mean(), 3),
                    mean_Winkler=round(g.Winkler.mean(), 3)))

            if popname not in ("dynamic_all_folds", "dynamic_all_folds_x08excl"):
                continue  # inference on the prespecified population, plus the X08 robustness arm

            # ---- per-facility statistic: average |gap| WITHIN facility across folds ---------
            a = a.copy(); a["abs_gap"] = (a.PICP - LEVEL).abs()
            per_fac = a.pivot_table(index="facility_id", columns="method",
                                    values="abs_gap", aggfunc="mean")
            pooled = a.pivot_table(index=["fold", "facility_id"], columns="method",
                                   values="abs_gap")
            rng = np.random.default_rng(SEED)

            raw = []
            for m1, m2 in CONTRASTS:
                v1, v2 = per_fac[m1].values, per_fac[m2].values
                stat_p = wilcoxon(v1 - v2)[1]
                md, lo, hi, bp = cluster_bootstrap(v1, v2, rng)
                pv1, pv2 = pooled[m1].dropna().values, pooled[m2].dropna().values
                pooled_p = wilcoxon(pv1 - pv2)[1]
                raw.append(dict(gamma_mode=gamma_mode, population=popname, contrast=f"{m1} vs {m2}",
                                n_facilities=len(v1), n_pooled_rows=len(pv1),
                                mean_abs_gap_a=round(v1.mean(), 4),
                                mean_abs_gap_b=round(v2.mean(), 4),
                                mean_diff=round(md, 4),
                                boot_lo95=round(lo, 4), boot_hi95=round(hi, 4),
                                boot_p=bp, wilcoxon_p_facility=stat_p,
                                wilcoxon_p_pooled_ARCHIVED_STYLE=pooled_p,
                                pct_facilities_favouring_a=round(float(np.mean(v1 < v2)) * 100, 1)))
            adj = holm([r["wilcoxon_p_facility"] for r in raw])
            for r, aj in zip(raw, adj):
                r["wilcoxon_p_holm"] = aj
                r["significant_holm_005"] = bool(aj < 0.05)
                r["anticonservatism_ratio"] = (
                    round(float(r["wilcoxon_p_facility"] / r["wilcoxon_p_pooled_ARCHIVED_STYLE"]), 1)
                    if r["wilcoxon_p_pooled_ARCHIVED_STYLE"] > 0 else np.nan)
            out_inf.extend(raw)

    fs = pd.DataFrame(out_fold); fs.to_csv(TAB / "2026-09-03-rolling-origin-foldsummary.csv", index=False)
    inf = pd.DataFrame(out_inf); inf.to_csv(TAB / "2026-09-03-rolling-origin-inference.csv", index=False)
    log("wrote foldsummary + inference CSVs")

    pd.set_option("display.width", 200)
    print("\n=== FOLD SUMMARY — calibrated gamma, primary population ===")
    print(fs[(fs.gamma_mode == "calibrated") & (fs.population == "dynamic_all_folds")]
          .drop(columns=["gamma_mode", "population"]).to_string(index=False))
    print("\n=== INFERENCE (I04) — facility-clustered, calibrated arm ===")
    show = inf[inf.gamma_mode == "calibrated"][
        ["population", "contrast", "n_facilities", "mean_diff", "boot_lo95", "boot_hi95", "boot_p",
         "wilcoxon_p_facility", "wilcoxon_p_holm", "significant_holm_005",
         "wilcoxon_p_pooled_ARCHIVED_STYLE", "anticonservatism_ratio",
         "pct_facilities_favouring_a"]]
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
