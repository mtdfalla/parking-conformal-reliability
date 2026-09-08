#!/usr/bin/env python3
"""EXP-027 addendum — EXP-022's DERIVED dose-response, recomputed under the D-018 exclusion.

The excess-sd figures and the "structure removed" percentages are derived quantities: they live in the
EXPERIMENTS_LOG entry, not in any CSV, so the batch's before/after table would otherwise miss them.

Definitions carried over from EXP-022 unchanged (B1: the noise floor is per METHOD, not shared; the
`random_5` partition is the matched floor for every partition, as in the original entry):
    excess_sd          = sqrt(max(sd_partition^2 - sd_random5^2, 0))
    structure_removed  = 1 - (excess_ToD-ACI^2 / excess_split-CP^2)     [VARIANCE basis]
Both verified to reproduce the logged EXP-022 figures (0.0889/0.0087/99%, 0.0961/0.0424/81%,
0.0522/0.0386/45%) from the control arm before the filtered arm is read.
"""
from pathlib import Path
import numpy as np
import pandas as pd

TAB = Path(__file__).resolve().parents[3] / "05_results" / "tables"
PARTS = ["time_of_day", "occupancy_tercile", "day_of_week"]
METHODS = ["split-CP", "Mondrian-split-CP", "ACI", "ToD-ACI"]


def excess_frame(tag: str) -> pd.DataFrame:
    s = pd.read_csv(TAB / f"2026-09-04-x08-orthogonal-summary-{tag}.csv")
    floor = s[s.partition == "random_5"].set_index("method").sd_PICP
    out = []
    for p in PARTS:
        pp = s[s.partition == p].set_index("method")
        v = float(pp.cramers_v_vs_tod.iloc[0])
        ex = {m: float(np.sqrt(max(pp.loc[m].sd_PICP ** 2 - floor[m] ** 2, 0.0)))
              for m in METHODS if m in pp.index}
        for m, e in ex.items():
            base = ex["split-CP"]
            out.append(dict(arm=tag, partition=p, cramers_v_vs_tod=round(v, 3), method=m,
                            noise_floor_sd=round(float(floor[m]), 4),
                            excess_sd=round(e, 4),
                            structure_removed_vs_splitCP=(
                                round(1 - (e ** 2) / (base ** 2), 3) if base > 0 else np.nan)))
    return pd.DataFrame(out)


def main() -> None:
    a, b = excess_frame("control"), excess_frame("excl")
    m = a.drop(columns=["arm"]).merge(b.drop(columns=["arm"]),
                                      on=["partition", "method"], suffixes=("_before", "_after"))
    out = TAB / "2026-09-04-x08-orthogonal-excess.csv"
    m.to_csv(out, index=False)
    print(f"wrote {out.name}\n")
    hdr = f"{'partition':18s} {'method':18s} {'V b->a':>13s} {'excess sd b->a':>17s} {'removed b->a':>15s}"
    print(hdr); print("-" * len(hdr))
    for _, r in m.iterrows():
        print(f"{r.partition:18s} {r.method:18s} "
              f"{r.cramers_v_vs_tod_before:.3f}->{r.cramers_v_vs_tod_after:.3f}  "
              f"{r.excess_sd_before:.4f}->{r.excess_sd_after:.4f}   "
              f"{r.structure_removed_vs_splitCP_before:>6.1%}->{r.structure_removed_vs_splitCP_after:>6.1%}")


if __name__ == "__main__":
    main()
