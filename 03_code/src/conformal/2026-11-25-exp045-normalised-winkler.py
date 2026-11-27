#!/usr/bin/env python3
"""
EXP-045 arm A8 (external-audit finding T086): Winkler score normalised by facility capacity.

Each facility's Winkler score at level 0.90 is divided by that facility's training-window maximum
occupancy (all `split == "train"` rows of the feature table the core run reads for features v3:
`belgrade_features_v2.parquet`, `birmingham_features_v3.parquet`), so facilities of different size
enter the mean on one scale.

Paper base: `2026-09-04-phase4-inference.py::core_frame` (paper horizon, level 0.90, dynamic) minus
the exclusion set of `2026-09-04-x08-reaggregate.py::exclusion_sets`, both imported. Belgrade t+15
(21 facilities), Birmingham t+60 (28 facilities).

Methods: split-CP, CQR, ACI, ACQR from `2026-11-22-core-{city}-v3-gcal-per-facility.csv`, and the
rolling-pool fixed-alpha arms RS-CP and RS-CQR from `2026-11-25-core-{city}-v3-rolling0-per-facility.csv`
(EXP-045 arm A1). Control: the raw Winkler means of the four core methods equal the shipped X08 core
headline `2026-09-04-x08-core-headline-excl.csv` to 1e-9, and every method has the paper-base facility
set. A mismatch stops the script before anything is written.

Output: 05_results/tables/2026-11-25-exp045-normalised-winkler.csv, one row per city and method with
the raw and normalised mean Winkler and the rank of each.
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"; PROC = ROOT / "01_data" / "processed"
OUT = TAB / "2026-11-25-exp045-normalised-winkler.csv"
FEAT = {"belgrade": "belgrade_features_v2.parquet", "birmingham": "birmingham_features_v3.parquet"}
BASE = [("belgrade", "y_t+15min", "use_15"), ("birmingham", "y_t+60min", "use_60")]
CORE = ["split-CP", "CQR", "ACI", "ACQR"]; RS = ["RS-CP", "RS-CQR"]


def log(m):
    print(f"[norm-winkler] {m}", flush=True)


def load_script(fname: str):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_")[:-3], HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p4 = load_script("2026-09-04-phase4-inference.py")
    ex = load_script("2026-09-04-x08-reaggregate.py").exclusion_sets()
    head = pd.read_csv(TAB / "2026-09-04-x08-core-headline-excl.csv")
    out = []; ok = True
    for city, hz, flag in BASE:
        drop = ex[(city, flag)]
        core_d = p4.core_frame(city, hz, drop)
        facs = sorted(core_d.facility_id.unique())
        rs = pd.read_csv(TAB / f"2026-11-25-core-{city}-v3-rolling0-per-facility.csv")
        rs = rs[(rs.horizon == hz) & (rs.level == 0.90) & (rs.dynamic) & rs.method.isin(RS)
                & rs.facility_id.isin(facs)]
        d = pd.concat([core_d[core_d.method.isin(CORE)], rs], ignore_index=True)
        f = pd.read_parquet(PROC / FEAT[city], columns=["facility_id", "split", "occupancy"])
        cap = f[f.split == "train"].groupby("facility_id").occupancy.max()
        d["cap_train_max"] = d.facility_id.map(cap)
        d["W_norm"] = d.Winkler / d.cap_train_max
        log(f"{city} {hz}: drop {drop}, {len(facs)} facilities, train-max capacity "
            f"min {cap[facs].min()} max {cap[facs].max()}")
        for m in CORE + RS:
            s = d[d.method == m]
            if sorted(s.facility_id) != facs or s.W_norm.isna().any():
                log(f"CONTROL FAIL: {city} {m} facility set or capacity incomplete"); ok = False
            if m in CORE:
                h = head[(head.city == city) & (head.method == m)].iloc[0]
                dif = abs(float(s.Winkler.mean()) - float(h.Winkler))
                good = dif <= 1e-9 and int(h.n) == len(facs)
                log(f"control {city} {m}: raw Winkler {float(s.Winkler.mean())!r} vs headline {h.Winkler!r} "
                    f"(diff {dif:.2e}): {'PASS' if good else 'FAIL'}")
                ok = ok and good
            out.append(dict(city=city, horizon=hz, level=0.90, method=m, n_facilities=int(s.facility_id.nunique()),
                            Winkler_mean=float(s.Winkler.mean()), Winkler_norm_mean=float(s.W_norm.mean()),
                            Winkler_norm_median=float(s.W_norm.median()), Winkler_norm_sd=float(s.W_norm.std()),
                            source="2026-11-22 gcal" if m in CORE else "2026-11-25 rolling0"))
    if not ok:
        log("CONTROL FAILED, nothing written"); sys.exit(1)
    o = pd.DataFrame(out)
    for col, rk in [("Winkler_mean", "rank_raw_core4"), ("Winkler_norm_mean", "rank_norm_core4")]:
        o[rk] = np.nan
        for city in o.city.unique():
            sel = (o.city == city) & o.method.isin(CORE)
            o.loc[sel, rk] = o.loc[sel, col].rank(method="min")
    for col, rk in [("Winkler_mean", "rank_raw_all6"), ("Winkler_norm_mean", "rank_norm_all6")]:
        o[rk] = o.groupby("city")[col].rank(method="min")
    o.to_csv(OUT, index=False)
    log(f"wrote {OUT.name} ({len(o)} rows)")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(o.to_string())


if __name__ == "__main__":
    main()
