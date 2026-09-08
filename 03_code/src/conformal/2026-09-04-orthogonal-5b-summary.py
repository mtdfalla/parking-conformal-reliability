#!/usr/bin/env python3
"""EXP-028 summary — the task-5b dose-response, per arm.

Definitions are EXP-022's, unchanged and reconciled against its logged figures in EXP-027:
    excess_sd         = sqrt(max(sd_partition^2 - sd_random^2, 0))     [noise floor is PER METHOD, B1]
    structure_removed = 1 - excess_m^2 / excess_splitCP^2              [VARIANCE basis]
Population per the prespecification: dynamic on the unit's own training window, not degenerate,
NOT low-information on the scored window (D-018), cells with n_cell >= 30.
A clipped excess of exactly 0 is printed as 'floor' -- it means at or below the matched noise floor,
which is a statement about resolution, not a perfect result.
"""
from pathlib import Path
import numpy as np, pandas as pd

TAB = Path(__file__).resolve().parents[3]/"05_results"/"tables"
CELLS = TAB/"2026-09-04-orthogonal-5b-cells.csv"
SUM = TAB/"2026-09-04-orthogonal-5b-summary.csv"
METHODS = ["split-CP", "Mondrian-split-CP", "ACI", "ToD-ACI"]
MIN_CELL = 30


def main() -> None:
    c = pd.read_csv(CELLS)
    c = c[(c.dynamic) & (c.degenerate != True) & (c.low_info != True)
          & (~c.method.isin(["SKIPPED-thin", "ToD-ACI==ACI"]))]
    c = c.dropna(subset=["PICP"])
    c = c[c.n_cell >= MIN_CELL]

    out = []
    for (arm, fold), g in c.groupby(["arm", "fold"]):
        rand = [p for p in g.partition.unique() if p.startswith("random_")][0]
        floor = {m: float(g[(g.partition == rand) & (g.method == m)].PICP.std(ddof=0))
                 for m in METHODS}
        for part in [p for p in g.partition.unique() if not p.startswith("random_")]:
            pp = g[g.partition == part]
            v = float(pp.cramers_v.dropna().mean())
            ex = {}
            for m in METHODS:
                s = pp[pp.method == m]
                if s.empty:
                    continue
                ex[m] = float(np.sqrt(max(s.PICP.std(ddof=0) ** 2 - floor[m] ** 2, 0.0)))
            for m in METHODS:
                s = pp[pp.method == m]
                if s.empty:
                    continue
                base = ex.get("split-CP", np.nan)
                out.append(dict(
                    arm=arm, fold=fold, partition=part, cramers_v=round(v, 3), method=m,
                    n_facilities=int(s.facility_id.nunique()), n_cells=len(s),
                    mean_PICP=round(float(s.PICP.mean()), 4),
                    sd_PICP=round(float(s.PICP.std(ddof=0)), 4),
                    min_PICP=round(float(s.PICP.min()), 4),
                    cells_below_080=int((s.PICP < 0.80).sum()),
                    noise_floor_sd=round(floor[m], 4),
                    excess_sd=round(ex[m], 4),
                    structure_removed=(round(1 - ex[m] ** 2 / base ** 2, 3)
                                       if base and base > 0 else np.nan),
                    MPIW=round(float(s.MPIW.mean()), 2)))
    d = pd.DataFrame(out)
    d.to_csv(SUM, index=False)
    print(f"wrote {SUM.name}: {len(d)} rows\n")
    for arm in d.arm.unique():
        print(f"=== {arm} ===")
        a = d[d.arm == arm]
        for (fold, part), g in a.groupby(["fold", "partition"], sort=False):
            v = g.cramers_v.iloc[0]
            bits = []
            for _, r in g.iterrows():
                e = "floor" if r.excess_sd == 0 else f"{r.excess_sd:.4f}"
                bits.append(f"{r.method}={e}")
            print(f"  {fold} {part:18s} V={v:.3f} n_fac={int(g.n_facilities.iloc[0]):2d}  " + "  ".join(bits))
        print()


if __name__ == "__main__":
    main()
