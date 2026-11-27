#!/usr/bin/env python3
"""
EXP-045 arm A6 (external-audit finding T069): facility by time-of-day cell coverage for CQR and ACQR.

What it does
------------
Reads the shipped per-row coverage at level 0.90, `2026-11-22-core-belgrade-v3-gcal-rows-L90.csv`
(Belgrade y_t+15min), assigns each row the time-of-day bucket of `2026-09-03-tod-conditional.py`
(its `bucket_of`, on the hour of the issue timestamp) and scores every facility by bucket cell for the
four core methods. No model is refitted.

Paper base: `2026-09-04-phase4-inference.py::core_frame` (horizon, level 0.90, dynamic) with the
exclusion set of `2026-09-04-x08-reaggregate.py::exclusion_sets`, both imported. Cells are reported
with the min-cell rule of the ToD summary (n_cell >= 30) flagged, as Table III reads them.

Control: split-CP and ACI cells reproduce the shipped ToD cell table
`2026-09-03-tod-facility-bucket.csv` on the paper base (covered counts and n_cell exactly), and the
shipped summary figures (worst 0.516 and 0.672, 12 cells below 0.80 for each). A mismatch stops the
script with exit 1 before any CQR or ACQR number is written.

Birmingham: the cell count per bucket of the paper-base t+60 rows of
`2026-11-22-core-birmingham-v3-gcal-rows-L90.csv`, to document how the targets fall into buckets.

Output: 05_results/tables/2026-11-25-exp045-tod-cells.csv (one row per city, method, facility, bucket
cell, plus SUMMARY rows per method).
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
OUT = TAB / "2026-11-25-exp045-tod-cells.csv"
MIN_CELL = 30
METHODS = ["split-CP", "CQR", "ACI", "ACQR"]


def log(m):
    print(f"[tod-cells] {m}", flush=True)


def load_script(fname: str):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_")[:-3], HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cells_for(city: str, hz: str, facs: list, bucket_of) -> pd.DataFrame:
    r = pd.read_csv(TAB / f"2026-11-22-core-{city}-v3-gcal-rows-L90.csv")
    r = r[(r.horizon == hz) & (r.facility_id.isin(facs))].copy()
    r["bucket"] = [bucket_of(h) for h in pd.to_datetime(r.timestamp).dt.hour]
    g = r.groupby(["method", "facility_id", "bucket"]).covered.agg(["sum", "size"]).reset_index()
    g = g.rename(columns={"sum": "covered", "size": "n_cell"})
    g["PICP"] = g.covered / g.n_cell
    g.insert(0, "city", city); g.insert(1, "horizon", hz)
    g["thin"] = g.n_cell < MIN_CELL
    return g


def summary(g: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (city, hz, m), s in g.groupby(["city", "horizon", "method"], sort=False):
        rep = s[~s.thin]
        w = rep.loc[rep.PICP.idxmin()]
        out.append(dict(city=city, horizon=hz, method=m, facility_id=np.nan, bucket="SUMMARY",
                        covered=int(rep.covered.sum()), n_cell=int(rep.n_cell.sum()), PICP=float(w.PICP),
                        thin=int(s.thin.sum()), n_cells=len(rep), n_facilities=int(rep.facility_id.nunique()),
                        cells_below_080=int((rep.PICP < 0.80).sum()),
                        cells_below_085=int((rep.PICP < 0.85).sum()),
                        sd_PICP=float(rep.PICP.std(ddof=0)),
                        worst_facility=int(w.facility_id), worst_bucket=w.bucket))
    return pd.DataFrame(out)


def main():
    tod = load_script("2026-09-03-tod-conditional.py")
    p4 = load_script("2026-09-04-phase4-inference.py")
    ex = load_script("2026-09-04-x08-reaggregate.py").exclusion_sets()
    drop = {"belgrade": ex[("belgrade", "use_15")], "birmingham": ex[("birmingham", "use_60")]}
    log(f"exclusion sets (computed): {drop}; buckets {tod.BUCKETS}")
    base = {c: sorted(p4.core_frame(c, hz, drop[c]).facility_id.unique())
            for c, hz in [("belgrade", "y_t+15min"), ("birmingham", "y_t+60min")]}
    log(f"paper base: belgrade {len(base['belgrade'])} facilities, birmingham {len(base['birmingham'])}")

    bel = cells_for("belgrade", "y_t+15min", base["belgrade"], tod.bucket_of)

    # ---- control: split-CP and ACI against the shipped ToD cell table ----------------------------
    ship = pd.read_csv(TAB / "2026-09-03-tod-facility-bucket.csv")
    ship = ship[ship.facility_id.isin(base["belgrade"]) & ship.method.isin(["split-CP", "ACI"])].copy()
    ship["covered"] = (ship.PICP * ship.n_cell).round().astype(int)
    m = ship.merge(bel, on=["facility_id", "bucket", "method"], how="outer", suffixes=("_ship", "_new"),
                   indicator=True)
    m = m[m.method.isin(["split-CP", "ACI"])]
    bad = m[(m._merge != "both") | (m.covered_ship != m.covered_new) | (m.n_cell_ship != m.n_cell_new)]
    ok = bad.empty
    log(f"control 1, split-CP and ACI cells vs 2026-09-03-tod-facility-bucket.csv: {len(m)} cells, "
        f"{len(bad)} differ: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(bad.to_string())
    sb = summary(bel)
    want = {"split-CP": (0.516, 12), "ACI": (0.672, 12)}
    for meth, (wv, nb) in want.items():
        r = sb[sb.method == meth].iloc[0]
        c2 = round(r.PICP, 3) == wv and r.cells_below_080 == nb and r.n_cells == 105
        log(f"control 2, {meth}: worst {r.PICP!r} (want {wv}), below 0.80 {r.cells_below_080} (want {nb}), "
            f"cells {r.n_cells}: {'PASS' if c2 else 'FAIL'}")
        ok = ok and c2
    if not ok:
        log("CONTROL FAILED, nothing written"); sys.exit(1)

    bham = cells_for("birmingham", "y_t+60min", base["birmingham"], tod.bucket_of)
    out = pd.concat([bel, sb, bham, summary(bham)], ignore_index=True)
    out.to_csv(OUT, index=False)
    log(f"wrote {OUT.name} ({len(out)} rows)")
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 500):
        print(pd.concat([sb, summary(bham)]).to_string())
        bc = bham[bham.method == "split-CP"].groupby("bucket").agg(
            cells=("n_cell", "size"), rows=("n_cell", "sum"), min_rows=("n_cell", "min"),
            max_rows=("n_cell", "max")).reset_index()
        print("Birmingham t+60 cells per bucket (split-CP rows, same for every method):")
        print(bc.to_string())
        print(bham.groupby("method").n_cell.sum().to_string())


if __name__ == "__main__":
    main()
