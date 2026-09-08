#!/usr/bin/env python3
"""EXP-034 — the paired summary and the gate for the relative-threshold allocation run.

Prespecified statistics only (`2026-09-05-rphase-C-PRESPECIFICATION.md` section 2): bad assignments PER
REQUEST as the primary, abstention rate and mean straight-line distance beside it, MARGIN as the control,
20 paired seeds, and the number of seeds in which the sign holds. No p-value: the seeds vary the requests
on one shared panel and are not independent replicates of the world.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
TAB = ROOT / "05_results" / "tables"
S = pd.read_csv(TAB / "2026-09-05-rel-alloc-seeds.csv")
S0 = pd.read_csv(TAB / "2026-09-05-rel-alloc-section0.csv")

# ---- GATE 3: the imported machinery must be the EXP-029 machinery -------------------------------
cap_ref = pd.read_csv(TAB / "2026-09-04-vignette-capacity-proxy.csv").dropna(subset=["cap_train"])
import importlib.util
spec = importlib.util.spec_from_file_location(
    "vign", ROOT / "03_code" / "src" / "conformal" / "2026-09-04-allocation-vignette.py")
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)
cur = V.phase_a(*V.load()[:1], V.load()[2], V.load()[3], 1e9, 0.0).dropna(subset=["cap_train"])
m = cap_ref.merge(cur, on="facility_id", suffixes=("_ref", "_now"))
gate3_bad = int((np.abs(m.cap_train_ref - m.cap_train_now) > 0).sum()) + \
            int((np.abs(m.gamma_ref - m.gamma_now) > 0).sum())
print(f"GATE 3 (import reproduces the EXP-029 panel): {len(m)} facilities, "
      f"{gate3_bad} mismatches on capacity proxy and gamma")
gate4_bad = int((S0.point_only_withdrawn_slots != 0).sum())
print(f"GATE 4 (POINT-only withdrawals must be 0, arithmetic): {gate4_bad} violations")
if gate3_bad or gate4_bad:
    print("GATE FAILED — branch X. Nothing is reported."); sys.exit(1)

# ---- the paired contrasts ------------------------------------------------------------------------
P = S.pivot_table(index=["window", "theta", "seed"], columns="policy",
                  values=["bad_assignments_per_request", "abstention_rate", "mean_straight_line_km"])
rows = []
for (w, th), g in P.groupby(level=[0, 1]):
    bad = g["bad_assignments_per_request"]; ab = g["abstention_rate"]; km = g["mean_straight_line_km"]
    d_iv = bad.POINT - bad.INTERVAL          # >0 means INTERVAL makes FEWER bad assignments
    d_mg = bad.POINT - bad.MARGIN
    d_iv_mg = bad.MARGIN - bad.INTERVAL      # >0 means INTERVAL beats the matched-conservatism control
    s0 = S0[(S0.window == w) & (np.isclose(S0.theta, th))].iloc[0]
    rows.append(dict(
        window=w, theta=th, n_seeds=len(g), facilities_with_event=int(s0.facilities_with_event),
        event_rate=float(s0.event_rate),
        bad_POINT=bad.POINT.mean(), bad_INTERVAL=bad.INTERVAL.mean(), bad_MARGIN=bad.MARGIN.mean(),
        d_point_minus_interval=d_iv.mean(), d_seed_min=d_iv.min(), d_seed_max=d_iv.max(),
        seeds_sign_holds=int((d_iv > 0).sum()),
        rel_reduction_vs_point=float(d_iv.mean() / bad.POINT.mean()) if bad.POINT.mean() else np.nan,
        d_point_minus_margin=d_mg.mean(),
        d_margin_minus_interval=d_iv_mg.mean(), seeds_beats_margin=int((d_iv_mg > 0).sum()),
        abst_POINT=ab.POINT.mean(), abst_INTERVAL=ab.INTERVAL.mean(), abst_MARGIN=ab.MARGIN.mean(),
        abst_cost_pp=100 * (ab.INTERVAL.mean() - ab.POINT.mean()),
        km_POINT=km.POINT.mean(), km_INTERVAL=km.INTERVAL.mean(), km_MARGIN=km.MARGIN.mean()))
D = pd.DataFrame(rows).sort_values(["window", "theta"])
D.to_csv(TAB / "2026-09-05-rel-alloc-summary.csv", index=False)

pd.set_option("display.width", 250)
print("\n=== PAIRED SUMMARY (20 seeds, identical requests within a seed) ===")
print(D[["window", "theta", "facilities_with_event", "bad_POINT", "bad_INTERVAL", "bad_MARGIN",
         "d_point_minus_interval", "seeds_sign_holds", "rel_reduction_vs_point",
         "d_margin_minus_interval", "seeds_beats_margin",
         "abst_POINT", "abst_INTERVAL", "abst_MARGIN", "abst_cost_pp"]].round(4).to_string(index=False))
print("\nwrote 2026-09-05-rel-alloc-summary.csv")
