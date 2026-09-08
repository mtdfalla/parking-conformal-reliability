#!/usr/bin/env python3
"""
EXP-031 (D') — analysis. Turns the leg-1/leg-2/sweep CSVs into the ESM table, PAIRED against the
no-injection baseline so that no withdrawal is attributed to the injection that would have happened
anyway (B3, B7 — the matched-comparator rule that EXP-024 and EXP-029 both turned on).

Reads only logged CSVs. Refits nothing. Writes `2026-09-04-failure-case-esm-summary.csv`.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
TAB = ROOT / "05_results" / "tables"
OUT = TAB / "2026-09-04-failure-case-esm-summary.csv"


def log(*a): print(*a, flush=True)


def main():
    l2 = pd.read_csv(TAB / "2026-09-04-failure-case-leg2-injection.csv")
    sw = pd.read_csv(TAB / "2026-09-04-failure-case-level-sweep.csv")
    base = l2[l2.arm == "none"].set_index("facility_id")
    rows = []
    for L, a in sw.groupby("level_frac_of_cap"):
        a = a.set_index("facility_id")
        fac = sorted(set(a.index) & set(base.index))
        a, b = a.loc[fac], base.loc[fac]
        # withdrawal caused BY the injection: withdraws under injection, does not under baseline,
        # or withdraws strictly earlier than it would have anyway.
        wi_inj, wi_base = a.step_interval.values, b.step_interval.values
        wp_inj, wp_base = a.step_point.values, b.step_point.values
        def caused(inj, bas):
            new = (inj >= 0) & (bas < 0)
            earlier = (inj >= 0) & (bas >= 0) & (inj < bas)
            return new, earlier
        ni, ei = caused(wi_inj, wi_base)
        np_, ep = caused(wp_inj, wp_base)
        both = (wi_inj >= 0) & (wp_inj >= 0)
        lead = (wp_inj - wi_inj)[both]
        only_int = (wi_inj >= 0) & (wp_inj < 0)
        # excess abstention over the SAME facility's no-injection baseline
        exc_i = (a.post_onset_frac_withdrawn_interval.values - b.post_onset_frac_withdrawn_interval.values)
        exc_p = (a.post_onset_frac_withdrawn_point.values - b.post_onset_frac_withdrawn_point.values)
        rows.append(dict(
            level_frac_of_cap=round(float(L), 4), n_facilities=len(fac),
            interval_withdraws=int((wi_inj >= 0).sum()), point_withdraws=int((wp_inj >= 0).sum()),
            interval_withdrawal_CAUSED_by_injection=int((ni | ei).sum()),
            point_withdrawal_CAUSED_by_injection=int((np_ | ep).sum()),
            n_interval_only=int(only_int.sum()),
            median_step_interval=(float(np.median(wi_inj[wi_inj >= 0])) if (wi_inj >= 0).any() else np.nan),
            median_step_point=(float(np.median(wp_inj[wp_inj >= 0])) if (wp_inj >= 0).any() else np.nan),
            n_lead_gt_0=int((lead > 0).sum()),
            median_lead_steps=(float(np.median(lead)) if len(lead) else np.nan),
            max_lead_steps=(float(lead.max()) if len(lead) else np.nan),
            median_lead_minutes=(float(np.median(lead)) * 5 if len(lead) else np.nan),
            mean_excess_abstention_interval=round(float(exc_i.mean()), 4),
            mean_excess_abstention_point=round(float(exc_p.mean()), 4),
            baseline_abstention_interval=round(float(b.post_onset_frac_withdrawn_interval.mean()), 4),
            baseline_abstention_point=round(float(b.post_onset_frac_withdrawn_point.mean()), 4),
        ))
    d = pd.DataFrame(rows).sort_values("level_frac_of_cap")
    d["baseline_arm"] = "no injection, same facility, same code path"
    d["lead_sign_note"] = "lead >= 0 by construction (U >= yhat); only the MAGNITUDE is empirical"
    d.to_csv(OUT, index=False)
    log(f"[out] {OUT.name} ({len(d)} rows)")
    cols = ["level_frac_of_cap", "interval_withdraws", "point_withdraws",
            "interval_withdrawal_CAUSED_by_injection", "point_withdrawal_CAUSED_by_injection",
            "n_interval_only", "median_lead_steps", "max_lead_steps",
            "mean_excess_abstention_interval", "mean_excess_abstention_point"]
    log(d[cols].to_string(index=False))
    log(f"\nbaseline (no injection): interval abstains on {d.baseline_abstention_interval.iloc[0]:.4f} "
        f"of post-onset slots, point on {d.baseline_abstention_point.iloc[0]:.4f}")
    log("ALL DONE")


if __name__ == "__main__":
    main()
