#!/usr/bin/env python3
"""
EXP-031 — D05: the dynamic-facility threshold sweep (sigma = 0 / 2 / 5 / 10), both cities.

Prespecified in `04_experiments/2026-09-04-rphase5-PRESPECIFICATION.md` sections 0(c), 1.4, 3 gate 3, 5.

NO MODEL IS RE-FITTED, and that was established on the inputs first: `2026-09-02-run-core-methods.py`
evaluates EVERY facility and TAGS `dynamic` rather than filtering up front, so facilities 1 (sigma 0.00)
and 10 (sigma 3.34) are already in `2026-09-02-core-belgrade-gcal-per-facility.csv`. D05 is therefore a
re-aggregation, exactly like R-Phase 4 Stage 1 — not a four-way rerun of both cities.

GATED: the sigma >= 5 arm must reproduce `2026-09-04-x08-core-headline-excl.csv` to 4 dp before any other
arm is read (B17). The low-information exclusion is applied at EVERY threshold, from
`core.low_information_facilities` and nowhere else (B9) — so facility 1 can never enter a reported number
at any threshold, and neither can facility 8.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
import core                                                              # noqa: E402

TAB = ROOT / "05_results" / "tables"
PROC = ROOT / "01_data" / "processed"
OUT = TAB / "2026-09-04-d05-threshold-sweep.csv"
REF = TAB / "2026-09-04-x08-core-headline-excl.csv"
CITIES = [("belgrade", "y_t+15min", "use_15"), ("birmingham", "y_t+60min", "use_60")]
THRESHOLDS = [0.0, 2.0, 5.0, 10.0]
METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
PRIMARY = 5.0


def log(*a): print(*a, flush=True)


def sigma_and_exclusion(city, flag):
    df = pd.read_parquet(PROC / f"{city}_features_v2.parquet")
    d = df[df[flag]]
    sd = d[d.split == "train"].groupby("facility_id").occupancy.std()
    te = d[d.split == "test"]
    excl = core.low_information_facilities(te)
    return sd, list(excl)


def aggregate(city, hz, sd, excl, thr):
    d = pd.read_csv(TAB / f"2026-09-02-core-{city}-gcal-per-facility.csv")
    d = d[(d.horizon == hz) & (d.level == 0.90)]
    keep = set(sd[sd >= thr].index) - set(excl)
    d = d[d.facility_id.isin(keep)]
    rows = []
    for meth in METHODS:
        s = d[d.method == meth]
        if s.empty:
            continue
        rows.append(dict(
            city=city, horizon=hz, sigma_threshold=thr, method=meth,
            PICP=float(s.PICP.mean()), std=float(s.PICP.std()),
            MPIW=float(s.MPIW.mean()), Winkler=float(s.Winkler.mean()),
            ci_contains=float(((s.picp_ci_lo <= 0.90) & (s.picp_ci_hi >= 0.90)).mean()),
            safe=float((s.picp_ci_lo >= 0.88).mean()), n=int(s.facility_id.nunique()),
            facilities_added_vs_primary=";".join(map(str, sorted(
                keep - (set(sd[sd >= PRIMARY].index) - set(excl))))),
            excluded_low_information=";".join(map(str, sorted(excl))),
        ))
    return pd.DataFrame(rows)


def main():
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--overwrite", action="store_true",
                     help="permit rewriting this script's own output (used by run_all.sh)")
    _a = _ap.parse_args()
    ref = pd.read_csv(REF)
    allarms, gate_fail, gate_checks = [], 0, 0
    for city, hz, flag in CITIES:
        sd, excl = sigma_and_exclusion(city, flag)
        srt = np.sort(sd.values)
        log(f"[{city}] sigma min three = {np.round(srt[:3], 2).tolist()}  "
            f"low_information = {excl}")
        for thr in THRESHOLDS:
            allarms.append(aggregate(city, hz, sd, excl, thr))
        # ---- gate: the sigma >= 5 arm must reproduce the logged headline to 4 dp ------------------
        a = aggregate(city, hz, sd, excl, PRIMARY)
        r = ref[ref.city == city]
        m = a.merge(r, on=["city", "horizon", "method"], suffixes=("_new", "_ref"))
        for col in ["PICP", "std", "MPIW", "Winkler", "ci_contains", "safe", "n"]:
            x, y = m[f"{col}_new"].values.astype(float), m[f"{col}_ref"].values.astype(float)
            bad = ~np.isclose(x, y, atol=1e-4)
            gate_checks += len(x); gate_fail += int(bad.sum())
        log(f"[{city}] gate rows matched: {len(m)} of {len(r)}")
    log(f"[gate] {gate_checks} checks, {gate_fail} failures against {REF.name}")
    if gate_fail or gate_checks == 0:
        log("GATE FAILED — nothing written."); sys.exit(1)

    d = pd.concat(allarms, ignore_index=True)
    if OUT.exists() and not _a.overwrite:
        # 2026-09-05 (revision 44, EXP-035): see the identical note in
        # `2026-09-04-rphase5-esm-capability.py`. A bare exit here makes the step non-idempotent,
        # and `run_all.sh` runs single-shot steps on every pass, so a restarted replication fails
        # on a file the replicator's own run wrote. The runner passes --overwrite.
        log(f"REFUSING to overwrite {OUT.name}; pass --overwrite to rewrite it."); sys.exit(1)
    d.to_csv(OUT, index=False)
    log(f"[out] {OUT.name} ({len(d)} rows)\n")
    for city in d.city.unique():
        s = d[d.city == city]
        log(f"--- {city} ---")
        log(s.pivot_table(index="method", columns="sigma_threshold",
                          values=["PICP", "std", "n"]).round(4).to_string())
        prim = s[s.sigma_threshold == PRIMARY].set_index("method")
        for thr in THRESHOLDS:
            t = s[s.sigma_threshold == thr].set_index("method")
            dp = (t.PICP - prim.PICP).abs().max(); dd = (t["std"] - prim["std"]).abs().max()
            log(f"    sigma>={thr:>4}: n={int(t.n.iloc[0])}  added={t.facilities_added_vs_primary.iloc[0] or '(none)'}"
                f"  max |dPICP| vs primary = {dp:.4f}  max |dSD| = {dd:.4f}")
    log("\nALL DONE")


if __name__ == "__main__":
    main()
