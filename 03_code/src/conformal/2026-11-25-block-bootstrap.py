#!/usr/bin/env python3
"""SUCCESSOR, 2026-11-25, EXP-045 arm A7 (findings T002, NEW-1, NEW-2), built from 2026-11-22-block-bootstrap-belgrade.py
by tools/make_infer_a7_block_bootstrap.py. What changed and why:
  1. --city belgrade|birmingham|both. Birmingham uses its paper base (t+60, level 0.90, dynamic, the computed
     low-information exclusion of phase4) and a 3 h block from core.block_length_for_cadence (6 rows at 30 min).
     The Belgrade constants of the original (t+15, block 36, exclusion [1, 8]) are now derived the same way and
     asserted equal to the original values.
  2. The exact verdict (90% interval inside [0.88, 0.92]) is written beside the safety verdict (NEW-1).
  3. The two rolling fixed-alpha arms of A1 (RS-CP, RS-CQR, files 2026-11-25-core-{city}-v3-rolling0-*) are
     bootstrapped on the same draws as the four methods.
  4. Control, run in every call that includes Belgrade: the four Belgrade rows, restricted to the original
     columns, must reproduce 2026-11-22-block-bootstrap-belgrade.csv byte for byte, or nothing is written.
  Each city gets a fresh generator with the seed, so a city's rows do not depend on which other city is run.

  python 2026-11-25-block-bootstrap.py --city both [--tab-dir DIR] [--seed 42] [--out FILE]

Original header follows.

Block-bootstrap sensitivity for the Belgrade population test (register row 3.4), exactly as prespecified
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
import importlib.util, sys
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
_p = HERE
while _p != _p.parent and not (_p / "01_data").is_dir():
    _p = _p.parent
ROOT = _p
LEVEL, B, SEED, CI = 0.90, 10_000, 42, 90.0
METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
RS_METHODS = ["RS-CP", "RS-CQR"]
SAFETY, EXACT_LO, EXACT_HI = 0.88, 0.88, 0.92
SRC = ROOT / "03_code" / "src" / "conformal"
sys.path.insert(0, str(SRC))
import core as CORE  # noqa: E402
_spec = importlib.util.spec_from_file_location("phase4_inference", SRC / "2026-09-04-phase4-inference.py")
P4 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(P4)
CITY = {"belgrade": dict(hz="y_t+15min", use="use_15", cadence=5),
        "birmingham": dict(hz="y_t+60min", use="use_60", cadence=30)}
SHIPPED = "2026-11-22-block-bootstrap-belgrade.csv"
SHIPPED_COLS = ["city", "horizon", "level", "method", "n_fac", "n_timestamps_axis", "n_timestamps_intersection",
                "block", "B", "seed", "ci", "mean_facility_PICP", "boot_lo", "boot_hi", "lower_below_safety_088"]

def log(m): print(f"[block-boot] {m}", flush=True)

def run_city(city, TAB, EX, SEED=SEED):
    HZ = CITY[city]["hz"]
    DROP = sorted(EX[(city, CITY[city]["use"])])
    BLOCK = CORE.block_length_for_cadence(CITY[city]["cadence"], 3.0)
    if city == "belgrade" and (DROP != [1, 8] or BLOCK != 36 or HZ != "y_t+15min"):
        raise SystemExit(f"[block-boot] Belgrade constants moved: drop {DROP}, block {BLOCK}, {HZ}")
    tag = f"2026-11-22-core-{city}-v3-gcal"
    rs_tag = f"2026-11-25-core-{city}-v3-rolling0"
    per = pd.read_csv(TAB / f"{tag}-per-facility.csv")
    per = per[(per.horizon == HZ) & (np.isclose(per.level, LEVEL)) & (per.method.isin(METHODS))]
    base = sorted(set(per[per.dynamic.astype(bool) & ~per.facility_id.isin(DROP)].facility_id))
    cf = P4.core_frame(city, HZ, DROP)
    if base != sorted(set(cf.facility_id)):
        raise SystemExit(f"[block-boot] {city}: base differs from phase4 core_frame")
    rs_per = pd.read_csv(TAB / f"{rs_tag}-per-facility.csv")
    rs_per = rs_per[(rs_per.horizon == HZ) & (np.isclose(rs_per.level, LEVEL)) & (rs_per.method.isin(RS_METHODS))]
    if base != sorted(set(rs_per[rs_per.dynamic.astype(bool) & ~rs_per.facility_id.isin(DROP)].facility_id)):
        raise SystemExit(f"[block-boot] {city}: rolling0 dynamic base differs from the gcal base")
    per = pd.concat([per, rs_per], ignore_index=True)
    rows = pd.read_csv(TAB / f"{tag}-rows-L90.csv", parse_dates=["timestamp"])
    rows = rows[(rows.horizon == HZ) & rows.facility_id.isin(base) & rows.method.isin(METHODS)]
    rows = rows.sort_values(["timestamp", "facility_id", "method"], kind="mergesort").reset_index(drop=True)

    axis = np.array(sorted(rows.timestamp.unique()))
    per_fac_ts = rows[rows.method == METHODS[0]].groupby("facility_id").timestamp.apply(set)
    n_inter = len(set.intersection(*per_fac_ts.values)) if len(per_fac_ts) else 0
    pos = {t: i for i, t in enumerate(axis)}
    T, F = len(axis), len(base); fidx = {f: j for j, f in enumerate(base)}
    log(f"{city}: {F} facilities, common axis {T} timestamps (intersection {n_inter}), block {BLOCK}, B {B}")
    # the rolling arms are read on the axis of the four methods, so the four methods' rows cannot move
    rs = pd.read_csv(TAB / f"{rs_tag}-rows-L90.csv", parse_dates=["timestamp"])
    rs = rs[(rs.horizon == HZ) & rs.facility_id.isin(base) & rs.method.isin(RS_METHODS)]
    rs = rs.sort_values(["timestamp", "facility_id", "method"], kind="mergesort").reset_index(drop=True)
    if not rs.timestamp.isin(set(axis)).all():
        raise SystemExit(f"[block-boot] {city}: rolling0 rows carry timestamps off the common axis")
    rows = pd.concat([rows, rs], ignore_index=True)

    # coverage and presence matrices, T x F, per method
    mats = {}
    for m in METHODS + RS_METHODS:
        r = rows[rows.method == m]
        cov = np.zeros((T, F)); pres = np.zeros((T, F))
        ti = r.timestamp.map(pos).values; fj = r.facility_id.map(fidx).values
        np.add.at(cov, (ti, fj), r.covered.values); np.add.at(pres, (ti, fj), 1)
        if pres.max() > 1: raise SystemExit(f"[block-boot] duplicate (timestamp, facility) rows for {m}")
        mats[m] = (cov, pres)
        if m in RS_METHODS and not np.array_equal(pres, mats[METHODS[0]][1]):
            raise SystemExit(f"[block-boot] {city}: {m} rows are not the same (timestamp, facility) cells as split-CP")

    # point estimate: must equal the canonical per-facility PICP (a reconciliation gate, C22)
    out = []
    rng = np.random.default_rng(SEED)
    n_blocks = int(np.ceil(T / BLOCK))
    starts = rng.integers(0, T - BLOCK + 1, size=(B, n_blocks))           # one draw, shared by all methods
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(B, -1)[:, :T]
    for m in METHODS + RS_METHODS:
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
        out.append(dict(city=city, horizon=HZ, level=LEVEL, method=m, n_fac=F, n_timestamps_axis=T,
                        n_timestamps_intersection=n_inter, block=BLOCK, B=B, seed=SEED, ci=CI,
                        mean_facility_PICP=point, boot_lo=lo, boot_hi=hi,
                        lower_below_safety_088=bool(lo < SAFETY),
                        safe_boot=bool(lo >= SAFETY), exact_boot=bool(lo >= EXACT_LO and hi <= EXACT_HI)))
        log(f"{m:9s} mean facility PICP {point:.4f}  {CI:.0f}% block-bootstrap [{lo:.4f}, {hi:.4f}]"
            f"  safe {lo >= SAFETY}  exact {lo >= EXACT_LO and hi <= EXACT_HI}")
    res = pd.DataFrame(out)
    if city == "belgrade":
        sc = res[res.method == "split-CP"].iloc[0]
        log("RULE (EXP-042 s. 8): split-CP lower bound " + ("BELOW 0.88: the keystone sentence gains "
            "'under facility-clustered inference'" if sc.lower_below_safety_088 else "at or above 0.88: no wording change"))
    return res


def control(res, TAB) -> bool:
    """The four Belgrade rows, original columns, must equal the shipped csv byte for byte."""
    ref = (TAB / SHIPPED).read_bytes()
    got = res[(res.city == "belgrade") & res.method.isin(METHODS)][SHIPPED_COLS].to_csv(index=False).encode()
    ok = got == ref
    log(f"CONTROL vs {SHIPPED}: " + ("PASS, byte-identical" if ok else "FAIL, differs"))
    return ok


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tab-dir", default=str(ROOT / "05_results" / "tables"))
    ap.add_argument("--city", choices=["belgrade", "birmingham", "both"], default="both")
    ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", default=None)
    ap.add_argument("--overwrite", action="store_true", help="replace an existing output (run_all.sh)")
    args = ap.parse_args(); TAB = Path(args.tab_dir)
    EX = P4.load_script("2026-09-04-x08-reaggregate.py").exclusion_sets()
    cities = ["belgrade", "birmingham"] if args.city == "both" else [args.city]
    res = pd.concat([run_city(c, TAB, EX, args.seed) for c in cities], ignore_index=True)
    if "belgrade" in cities and not control(res, TAB):
        raise SystemExit("[block-boot] CONTROL FAILED: nothing written.")
    name = "2026-11-25-block-bootstrap-" + ("both-cities" if args.city == "both" else args.city) + ".csv"
    dest = Path(args.out) if args.out else TAB / name
    if dest.exists() and not args.overwrite:
        raise SystemExit(f"[block-boot] {dest} exists: not overwritten.")
    res.to_csv(dest, index=False)
    log(f"wrote {dest.name}: {len(res)} rows")

if __name__ == "__main__":
    main()
