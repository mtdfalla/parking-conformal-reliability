#!/usr/bin/env python3
"""
EXP-012 — Paired inferential comparison between conformal methods (prior review, major issue 3).

For each city/horizon at the 90% level, methods are compared on the SAME facilities (paired):
  * Winkler score (strictly proper; efficiency+validity combined)
  * |coverage gap| = |PICP - 0.90| (per-facility reliability)
Tests: Wilcoxon signed-rank across facilities + facility-bootstrap 90% CI on the mean difference.
Outputs one tidy CSV: 05_results/tables/2026-08-04-paired-tests.csv
"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[3]; TAB = ROOT/"05_results"/"tables"
SEED = 42; TARGET = 0.90
PAIRS = [("ACI", "split-CP"), ("ACI", "CQR"), ("ACQR", "ACI"), ("ACQR", "CQR"), ("ACQR", "split-CP")]

def boot_ci_mean(d, B=10000, seed=SEED):
    rng = np.random.default_rng(seed); n = len(d)
    ms = rng.choice(d, size=(B, n), replace=True).mean(axis=1)
    return float(np.percentile(ms, 5)), float(np.percentile(ms, 95))

rows = []
for city in ["belgrade", "birmingham"]:
    base = pd.read_csv(TAB/f"2026-06-25-corr-{city}-per-facility.csv")
    acqr = pd.read_csv(TAB/f"2026-08-04-acqr-{city}-per-facility.csv")
    d = pd.concat([base, acqr], ignore_index=True)
    d = d[d.level == TARGET].copy()
    d["absgap"] = (d.PICP - TARGET).abs()
    for hz in sorted(d.horizon.unique()):
        dd = d[d.horizon == hz]
        wide_w = dd.pivot_table(index="facility_id", columns="method", values="Winkler")
        wide_g = dd.pivot_table(index="facility_id", columns="method", values="absgap")
        for metric, wide in [("Winkler", wide_w), ("abs_cov_gap", wide_g)]:
            for m1, m2 in PAIRS:
                if m1 not in wide.columns or m2 not in wide.columns: continue
                sub = wide[[m1, m2]].dropna()
                diff = (sub[m1] - sub[m2]).values   # negative = m1 better (lower)
                if len(diff) < 5: continue
                try:
                    stat, p = wilcoxon(diff, zero_method="wilcox", alternative="two-sided")
                except ValueError:
                    p = np.nan
                lo, hi = boot_ci_mean(diff)
                rows.append(dict(city=city, horizon=hz, metric=metric, m1=m1, m2=m2,
                                 n=len(diff), mean_diff=float(diff.mean()),
                                 median_diff=float(np.median(diff)),
                                 ci_lo=lo, ci_hi=hi, wilcoxon_p=float(p),
                                 m1_better_frac=float(np.mean(diff < 0))))
out = pd.DataFrame(rows).round(4)
out.to_csv(TAB/"2026-08-04-paired-tests.csv", index=False)

# Readable digest
sig = lambda p: "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
for metric in ["Winkler", "abs_cov_gap"]:
    print(f"\n===== {metric} (m1 - m2; negative favors m1) =====")
    for _, r in out[out.metric == metric].iterrows():
        print(f"{r.city:10} {r.horizon:10} {r.m1:5} vs {r.m2:8} "
              f"mean {r.mean_diff:+8.2f} [90% CI {r.ci_lo:+8.2f},{r.ci_hi:+8.2f}] "
              f"p={r.wilcoxon_p:.4f} {sig(r.wilcoxon_p):4} m1-better {r.m1_better_frac:.0%}")
