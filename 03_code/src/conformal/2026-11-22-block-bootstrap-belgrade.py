#!/usr/bin/env python3
"""Block-bootstrap sensitivity for the Belgrade population test (register row 3.4), exactly as prespecified
in EXP-042 section 8 (04_experiments/2026-11-22-birmingham-causal-rebuild-PRESPECIFICATION.md).

  python 2026-11-22-block-bootstrap-belgrade.py [--tab-dir DIR]

ESTIMAND     the mean over facilities of facility PICP, Belgrade, y_t+15min, level 0.90, per method
             (split-CP, CQR, ACI, ACQR, calibrated gamma).
POPULATION   the evaluation base of 21 facilities: dynamic (train sd >= 5) and not in the low-information
             exclusion (facilities 1 and 8, D-018), the same base as the population test of record.
RESAMPLING   moving blocks of 36 consecutive timestamps (3 h at the 5-min cadence) on the common test
             time axis, drawn SYNCHRONOUSLY: one draw of block starts per replicate, applied to every
             facility and every method, so dependence across facilities at a timestamp is preserved.
             B = 10,000, seed 42, percentile 90% interval. Rows sorted by timestamp then facility before
             resampling (C15).
COMMON AXIS  the sorted union of the 21 facilities' test timestamps. A facility's replicate PICP is its
             covered count over its rows at the drawn positions. When every facility has every timestamp,
             this is the intersection; the counts of both are written so a reader can see which held.
RULE         fixed in the prespecification: the row is reported whichever way it falls. If the split-CP
             lower bound is below 0.88, the keystone sentence gains "under facility-clustered inference".
             The test of record does not change.
INPUT        2026-11-22-core-belgrade-v3-gcal-rows-L90.csv and -per-facility.csv (the canonical runner).
OUTPUT       2026-11-22-block-bootstrap-belgrade.csv
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
_p = HERE
while _p != _p.parent and not (_p / "01_data").is_dir():
    _p = _p.parent
ROOT = _p
HZ, LEVEL, BLOCK, B, SEED, CI = "y_t+15min", 0.90, 36, 10_000, 42, 90.0
DROP = [1, 8]
METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
SAFETY = 0.88

def log(m): print(f"[block-boot] {m}", flush=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tab-dir", default=str(ROOT / "05_results" / "tables"))
    args = ap.parse_args(); TAB = Path(args.tab_dir)
    tag = "2026-11-22-core-belgrade-v3-gcal"
    per = pd.read_csv(TAB / f"{tag}-per-facility.csv")
    per = per[(per.horizon == HZ) & (np.isclose(per.level, LEVEL)) & (per.method.isin(METHODS))]
    base = sorted(set(per[per.dynamic.astype(bool) & ~per.facility_id.isin(DROP)].facility_id))
    rows = pd.read_csv(TAB / f"{tag}-rows-L90.csv", parse_dates=["timestamp"])
    rows = rows[(rows.horizon == HZ) & rows.facility_id.isin(base) & rows.method.isin(METHODS)]
    rows = rows.sort_values(["timestamp", "facility_id", "method"], kind="mergesort").reset_index(drop=True)

    axis = np.array(sorted(rows.timestamp.unique()))
    per_fac_ts = rows[rows.method == METHODS[0]].groupby("facility_id").timestamp.apply(set)
    n_inter = len(set.intersection(*per_fac_ts.values)) if len(per_fac_ts) else 0
    pos = {t: i for i, t in enumerate(axis)}
    T, F = len(axis), len(base); fidx = {f: j for j, f in enumerate(base)}
    log(f"{F} facilities, common axis {T} timestamps (intersection {n_inter}), block {BLOCK}, B {B}")

    # coverage and presence matrices, T x F, per method
    mats = {}
    for m in METHODS:
        r = rows[rows.method == m]
        cov = np.zeros((T, F)); pres = np.zeros((T, F))
        ti = r.timestamp.map(pos).values; fj = r.facility_id.map(fidx).values
        np.add.at(cov, (ti, fj), r.covered.values); np.add.at(pres, (ti, fj), 1)
        if pres.max() > 1: raise SystemExit(f"[block-boot] duplicate (timestamp, facility) rows for {m}")
        mats[m] = (cov, pres)

    # point estimate: must equal the canonical per-facility PICP (a reconciliation gate, C22)
    out = []
    rng = np.random.default_rng(SEED)
    n_blocks = int(np.ceil(T / BLOCK))
    starts = rng.integers(0, T - BLOCK + 1, size=(B, n_blocks))           # one draw, shared by all methods
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(B, -1)[:, :T]
    for m in METHODS:
        cov, pres = mats[m]
        fac_picp = cov.sum(0) / pres.sum(0)
        canon = per[(per.method == m) & per.facility_id.isin(base)].set_index("facility_id").PICP.reindex(base).values
        if not np.allclose(fac_picp, canon, atol=1e-12):
            raise SystemExit(f"[block-boot] {m}: per-row coverage does not reproduce the per-facility PICP")
        point = float(fac_picp.mean())
        reps = np.empty(B)
        for b in range(B):
            c = cov[idx[b]].sum(0); n = pres[idx[b]].sum(0)
            ok = n > 0
            reps[b] = float(np.mean(c[ok] / n[ok]))
        tail = (100.0 - CI) / 2.0
        lo, hi = float(np.percentile(reps, tail)), float(np.percentile(reps, 100.0 - tail))
        out.append(dict(city="belgrade", horizon=HZ, level=LEVEL, method=m, n_fac=F, n_timestamps_axis=T,
                        n_timestamps_intersection=n_inter, block=BLOCK, B=B, seed=SEED, ci=CI,
                        mean_facility_PICP=point, boot_lo=lo, boot_hi=hi,
                        lower_below_safety_088=bool(lo < SAFETY)))
        log(f"{m:9s} mean facility PICP {point:.4f}  {CI:.0f}% block-bootstrap [{lo:.4f}, {hi:.4f}]")
    res = pd.DataFrame(out)
    sc = res[res.method == "split-CP"].iloc[0]
    log("RULE (EXP-042 s. 8): split-CP lower bound " + ("BELOW 0.88: the keystone sentence gains "
        "'under facility-clustered inference'" if sc.lower_below_safety_088 else "at or above 0.88: no wording change"))
    res.to_csv(TAB / "2026-11-22-block-bootstrap-belgrade.csv", index=False)
    log("wrote 2026-11-22-block-bootstrap-belgrade.csv")

if __name__ == "__main__":
    main()
