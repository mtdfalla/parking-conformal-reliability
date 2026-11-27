#!/usr/bin/env python3
"""EXP-045 arm A3 (external-audit finding T006): test of the canonical spatial successors.

1. Positive control. `2026-11-25-spatial-analysis.py --check-only shipped` refits every spatial facility on the
   canonical pipeline and must reproduce the ACI covered count of
   `2026-11-22-core-belgrade-v3-gcal-per-facility.csv` (t+15, level 0.90) at every facility: exit 0.
2. Negative control. `--check-only fixed005` runs the same refit at the retired fixed gamma 0.05 and must
   fail (exit 1), so the control is shown able to fail.
3. Consistency. The `published_21` rows of `2026-11-25-spatial-statistics-exclusion-base.csv` (re-aggregated
   from the stored pairwise tables) must equal the values the two fitting scripts wrote to
   `2026-11-25-spatial-statistics.csv` for the same 21 facilities.
Run from the project root.
"""
import subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SP = ROOT / "03_code" / "src" / "spatial" / "2026-11-25-spatial-analysis.py"
TAB = ROOT / "05_results" / "tables"
fails = 0

for mode, want in (("shipped", 0), ("fixed005", 1)):
    r = subprocess.run([sys.executable, str(SP), "--check-only", mode], cwd=ROOT, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() + r.stderr.splitlines() if "CONTROL" in l]
    ok = r.returncode == want
    fails += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] --check-only {mode}: exit {r.returncode} (expected {want}) | {tail[-1] if tail else ''}")

S = pd.read_csv(TAB / "2026-11-25-spatial-statistics.csv", dtype=str, keep_default_na=False)
E = pd.read_csv(TAB / "2026-11-25-spatial-statistics-exclusion-base.csv", dtype=str, keep_default_na=False)
E = E[E.population == "published_21"].set_index("statistic")
pairs = [("2026-11-25-spatial-analysis.py", "morans_I_mean_aci_halfwidth", True),
         ("2026-11-25-spatial-mantel.py", "mantel_r_distance_vs_residcorr", True),
         ("2026-11-25-spatial-mantel.py", "mean_pairwise_resid_corr", False),
         ("2026-11-25-spatial-mantel.py", "mean_pairwise_raw_occupancy_corr", False),
         ("2026-11-25-spatial-analysis.py", "mean_resid_corr_near_lt2km", False),
         ("2026-11-25-spatial-analysis.py", "mean_resid_corr_far_gt5km", False),
         ("2026-11-25-spatial-analysis.py", "spearman_rho_residcorr_vs_distance_naive", True)]
for script, stat, has_p in pairs:
    a = S[(S.script == script) & (S.statistic == stat)].iloc[0]
    b = E.loc[stat]
    ok = abs(float(a.value) - float(b.value)) < 5e-7 and (not has_p or abs(float(a.p_value) - float(b.p_value)) < 5e-7)
    fails += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] {stat}: fit {a.value} p {a.p_value} | re-aggregated {b.value} p {b.p_value}")

print("ALL PASS" if not fails else f"{fails} FAILURE(S)")
sys.exit(1 if fails else 0)
