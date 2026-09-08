#!/usr/bin/env python3
"""EXP-033 -- the before/after table for the NGBoost reseed, and the negative control that gates it.

B25's rule: a number that will be attributed to a cause gets a CSV naming its population at the moment
it is computed. This writes every changed cell of the regenerated E3 arm beside its superseded value,
and it runs prespecification section 4.3 -- the control that can REVERT the fix.

Populations, stated here and not chosen after the fact:
  * per-facility rows: arm `A3_v2_daychunk`, both cities, all facilities present in the file.
  * `published`: the base every reported E3 number uses -- dynamic & !degenerate & status ok, minus
    `core.low_information_facilities` (Belgrade 21 of 24; Birmingham excludes nothing, 28).

Tolerances are the R-Phase 6 table, not re-derived here: PICP and counts EXACT; MPIW/Winkler relative
1e-12; bootstrap CI bounds relative 1e-9.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
TAB = ROOT / "05_results" / "tables"
SUP = TAB / "_superseded" / "2026-09-05-pre-reseed"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

ARM = "A3_v2_daychunk"
NG = ["NGBoost", "NGBoost-conformal"]
OTHER = ["EnbPI", "AgACI-style", "ACI-crosscheck"]
TOL_REL_TIGHT, TOL_REL_CI = 1e-12, 1e-9
CITY = {"belgrade": "use_15", "birmingham": "use_60"}


def rel(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = np.abs(a - b); s = np.maximum(np.abs(a), np.abs(b))
    return np.where(s > 0, d / np.where(s > 0, s, 1.0), d)


def excluded(ds, use):
    """The D-018 exclusion, computed from the DATA on that window's TEST rows only -- exactly as
    `2026-09-04-x08-reaggregate.py` computes it. One definition, never hardcoded (B9)."""
    d = pd.read_parquet(ROOT / "01_data" / "processed" / f"{ds}_features_v2.parquet")
    te = d[d.split == "test"]
    return set(core.low_information_facilities(te[te[use]]))


def main() -> int:
    rows, checks, fails, msgs = [], 0, 0, []
    for ds, use in CITY.items():
        f = f"2026-09-03-e3-{ds}-per-facility.csv"
        old = pd.read_csv(SUP / f); new = pd.read_csv(TAB / f)
        old = old[old.arm == ARM]; new = new[new.arm == ARM]
        m = old.merge(new, on=["facility_id", "method"], how="outer",
                      suffixes=("_old", "_new"), indicator=True)
        if (m["_merge"] != "both").any():
            fails += int((m["_merge"] != "both").sum())
            msgs.append(f"{ds}: {(m['_merge'] != 'both').sum()} row(s) in only one file (branch N6)")
        # ---- 4.3 NEGATIVE CONTROL on the non-NGBoost methods -------------------------------
        g = m[m.method.isin(OTHER)]
        for c, tol in (("PICP", 0.0), ("MPIW", TOL_REL_TIGHT), ("Winkler", TOL_REL_TIGHT),
                       ("picp_lo", TOL_REL_CI), ("picp_hi", TOL_REL_CI)):
            x, y = g[c + "_old"], g[c + "_new"]
            keep = ~(x.isna() & y.isna())
            r = rel(x[keep], y[keep]) if tol > 0 else np.abs(
                np.asarray(x[keep], float) - np.asarray(y[keep], float))
            checks += int(keep.sum())
            bad = r > tol
            if bad.any():
                fails += int(bad.sum())
                w = g[keep][bad][["facility_id", "method", c + "_old", c + "_new"]]
                msgs.append(f"{ds}: control column '{c}' -- {int(bad.sum())} beyond tolerance\n"
                            + w.to_string(index=False))
        for c in ("n_test", "cal_score_max"):
            x, y = g[c + "_old"], g[c + "_new"]
            keep = ~(x.isna() & y.isna())
            checks += int(keep.sum())
            bad = np.asarray(x[keep], float) != np.asarray(y[keep], float)
            if bad.any():
                fails += int(bad.sum()); msgs.append(f"{ds}: control column '{c}' changed")
        # ---- the before/after rows -----------------------------------------------------------
        ex = excluded(ds, use)
        for _, r_ in m[m.method.isin(NG)].iterrows():
            pub = (bool(r_.get("dynamic_new", False)) and r_.get("degenerate_new") is not True
                   and str(r_.get("status_new", "ok")) in ("ok", "nan")
                   and int(r_.facility_id) not in ex)
            rows.append(dict(dataset=ds, facility_id=int(r_.facility_id), method=r_.method,
                             in_published_base=pub,
                             PICP_before=r_.PICP_old, PICP_after=r_.PICP_new,
                             dPICP=r_.PICP_new - r_.PICP_old,
                             MPIW_before=r_.MPIW_old, MPIW_after=r_.MPIW_new,
                             Winkler_before=r_.Winkler_old, Winkler_after=r_.Winkler_new,
                             rel_dWinkler=float(rel(r_.Winkler_old, r_.Winkler_new))))
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "2026-09-05-ngboost-reseed-before-after.csv", index=False)

    print(f"4.3 NEGATIVE CONTROL (non-NGBoost methods): {checks} checks, {fails} failed")
    for s in msgs:
        print("      " + s.replace("\n", "\n      "))
    print()
    pub = out[out.in_published_base]
    print("PUBLISHED BASE ONLY -- mean PICP before -> after, and the largest single-facility move:")
    for (ds, meth), g in pub.groupby(["dataset", "method"]):
        print(f"  {ds:11s} {meth:18s} n={len(g):2d}  "
              f"{g.PICP_before.mean():.4f} -> {g.PICP_after.mean():.4f}  "
              f"(mean dPICP {g.PICP_after.mean()-g.PICP_before.mean():+.5f}; "
              f"max |dPICP| at one facility {g.dPICP.abs().max():.4f})")
    print(f"\nwrote 2026-09-05-ngboost-reseed-before-after.csv ({len(out)} rows)")
    if fails:
        print("\nBRANCH N4 -- the seeding leaked outside the NGBoost fit. REVERT.")
        return 1
    print("\n4.3 PASS -- every non-NGBoost cell reproduces within the R-Phase 6 tolerance table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
