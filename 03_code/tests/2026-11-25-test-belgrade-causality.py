#!/usr/bin/env python3
"""
EXP-045 arm A11 (T001), 2026-11-25: raw-perturbation causality test of the Belgrade feature builder.
The Birmingham test (2026-11-22-test-feature-causality.py) is not touched.

For each cut time c, every raw reading at or after c + 5 min (the first reading outside bin c) is
(a) shifted by +50 and, separately, (b) deleted. The builder is rerun on the perturbed raw data. No
input column (anchor, lags, rolling windows, calendar and the other non-target columns) of any row
retained in both builds with timestamp at or before c may change. Rows lost at or before c (their
targets lie after c and were deleted) are counted and printed, not treated as violations.

Cut times
  * the 17 cut times of the validation scratch script g1-leakage-timing/m3.py: 5 and 30 minutes before
    each of the 7 internal gap starts of facility 1, plus three ordinary times. All 17 lie on observed
    bins, so they test the history side only.
  * 14 in-gap cut times derived from the data: the first and the second missing bin of every internal
    gap (all facilities share the same 7 gaps). These are the bins the two-sided interpolation fills
    from the first reading after the gap, so they are where a leak would appear.

Positive control (--control): the predecessor builder with `limit=2` removed, so every internal gap is
interpolated two-sided and rows inside gaps keep inputs that depend on the post-gap reading. It must
be detected (at least one violation). The successor builder with the same change must also stop on
its own T001 guard.

Run:  python 2026-11-25-test-belgrade-causality.py [--builder PATH] [--part main|control|all]
Exit 0 when the main part has 0 violations and (if run) the control is detected.
"""
from __future__ import annotations
import argparse, contextlib, importlib.util, io, sys, tempfile, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
FEAT_DIR = ROOT / "03_code" / "src" / "features"
SUCCESSOR = FEAT_DIR / "2026-11-25-build_features_v2.py"
PREDECESSOR_NAME = "2026-09-02-build_features_v2.py"
RAW = ROOT / "01_data" / "processed" / "belgrade_long.parquet"

M3_GAPS = ["2017-03-06 00:45", "2017-03-07 01:10", "2017-03-09 15:20", "2017-03-12 08:25",
           "2017-03-15 03:20", "2017-03-18 19:40", "2017-03-19 10:55"]
M3_CUTS = ([pd.Timestamp(g) - pd.Timedelta(minutes=k) for g in M3_GAPS for k in (5, 30)] +
           list(pd.to_datetime(["2017-03-08 12:00", "2017-03-14 09:00", "2017-03-20 17:00"])))
FILL = 'occ_raw.interpolate(method="time", limit=2, limit_area="inside")'
FILL_TWO_SIDED = 'occ_raw.interpolate(method="time", limit_area="inside")'


def load_builder(source_text: str, work: Path, tag: str):
    d = work / tag / "src" / "features"           # depth so the builder's ROOT = parents[3] resolves
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"builder_{tag}.py"
    p.write_text(source_text)
    spec = importlib.util.spec_from_file_location(f"builder_{tag}", p)
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    out = work / f"out_{tag}"; out.mkdir(exist_ok=True)
    m.PROC = out; m.IN_PATH = out / "long.parquet"; m.OUT_PATH = out / "features.parquet"
    return m


def build(m, long: pd.DataFrame) -> pd.DataFrame:
    long.to_parquet(m.IN_PATH)
    with contextlib.redirect_stdout(io.StringIO()):
        m.main()
    return pd.read_parquet(m.OUT_PATH)


def in_gap_cuts(long: pd.DataFrame) -> list[pd.Timestamp]:
    cuts = set()
    for _, g in long.groupby("facility_id"):
        raw = g.set_index("timestamp").sort_index()["occupancy"].resample("5min").mean()
        na = raw.isna().values
        i, n = 0, len(na)
        while i < n:
            if na[i]:
                j = i
                while j < n and na[j]:
                    j += 1
                if i > 0 and j < n:                      # internal gap [i, j)
                    cuts.add(raw.index[i])
                    if j - i >= 2:
                        cuts.add(raw.index[i + 1])
                i = j
            else:
                i += 1
    return sorted(cuts)


def input_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("facility_id", "timestamp")
            and not c.startswith(("y_t+", "target_observed_", "target_interpolated_"))]


def run_cuts(m, long, base, cuts, label):
    cols = input_cols(base)
    viol, lines = 0, []
    for c in cuts:
        for mode in ("shift", "delete"):
            L = long.copy()
            late = L.timestamp >= c + pd.Timedelta(minutes=5)
            if mode == "shift":
                L.loc[late, "occupancy"] = L.loc[late, "occupancy"] + 50
            else:
                L = L[~late]
            p = build(m, L)
            a = base[base.timestamp <= c].set_index(["facility_id", "timestamp"]).sort_index()
            b = p[p.timestamp <= c].set_index(["facility_id", "timestamp"]).sort_index()
            common = a.index.intersection(b.index)
            A, B = a.loc[common, cols], b.loc[common, cols]
            changed = [x for x in cols if not (A[x].astype(str).values == B[x].astype(str).values).all()]
            nrow = int((A.astype(str).values != B.astype(str).values).any(axis=1).sum())
            lost, gained = len(a.index.difference(b.index)), len(b.index.difference(a.index))
            if changed:
                viol += 1
            lines.append(f"  {label} cut {c} {mode:6s} rows<=cut {len(a):6d} common {len(common):6d} "
                         f"lost {lost:4d} gained {gained:3d} rows with changed inputs {nrow:4d} "
                         f"changed cols {changed if changed else '-'}")
    return viol, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--builder", default=str(SUCCESSOR))
    ap.add_argument("--part", default="all", choices=["main", "control", "all"])
    args = ap.parse_args()
    long = pd.read_parquet(RAW)
    gcuts = in_gap_cuts(long)
    print(f"raw: {RAW.name}, {len(long)} readings, {long.facility_id.nunique()} facilities")
    print(f"cuts: {len(M3_CUTS)} from m3.py, {len(gcuts)} in-gap")
    ok = True
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        if args.part in ("main", "all"):
            t0 = time.time()
            m = load_builder(Path(args.builder).read_text(), work, "main")
            base = build(m, long)
            u = base["use_30"].values; ti = base["target_interpolated_30"].values
            print(f"[main] builder {args.builder}: {len(base)} rows; interpolated inputs on retained rows: "
                  f"{int(base['occ_interpolated'].sum())} anchor; t+30 interpolated targets among use_30 rows: "
                  f"{int((u & ti).sum())} ({int((u & ti & (base.split == 'test').values).sum())} in test)")
            v1, l1 = run_cuts(m, long, base, M3_CUTS, "m3")
            v2, l2 = run_cuts(m, long, base, gcuts, "gap")
            print("\n".join(l1 + l2))
            nper = 2 * (len(M3_CUTS) + len(gcuts))
            print(f"[main] violations: {v1} of {2*len(M3_CUTS)} perturbations at the m3 cuts, "
                  f"{v2} of {2*len(gcuts)} at the in-gap cuts ({time.time()-t0:.0f}s)")
            ok &= (v1 + v2 == 0)
            print(f"[main] {'PASS' if v1 + v2 == 0 else 'FAIL'}: {v1+v2} violations in {nper} perturbations")
        if args.part in ("control", "all"):
            t0 = time.time()
            pred = (FEAT_DIR / PREDECESSOR_NAME).read_text()
            assert pred.count(FILL) == 1, "predecessor fill line not found"
            mc = load_builder(pred.replace(FILL, FILL_TWO_SIDED), work, "control")
            basec = build(mc, long)
            print(f"[control] two-sided variant (no limit, no guard): {len(basec)} rows, "
                  f"{int(basec['occ_interpolated'].sum())} retained rows with an interpolated anchor")
            v1, l1 = run_cuts(mc, long, basec, M3_CUTS, "m3")
            v2, l2 = run_cuts(mc, long, basec, gcuts, "gap")
            print("\n".join(l1 + l2))
            det = v1 + v2 > 0
            print(f"[control] violations: {v1} of {2*len(M3_CUTS)} at the m3 cuts, {v2} of {2*len(gcuts)} "
                  f"at the in-gap cuts -> {'DETECTED' if det else 'NOT DETECTED'} ({time.time()-t0:.0f}s)")
            succ = Path(args.builder).read_text()
            assert succ.count(FILL) == 1, "successor fill line not found"
            mg = load_builder(succ.replace(FILL, FILL_TWO_SIDED), work, "guard")
            try:
                build(mg, long); guard = False; msg = "no error"
            except RuntimeError as e:
                guard = "T001 guard" in str(e); msg = str(e)
            print(f"[control] successor guard on the same variant: {'STOPPED' if guard else 'DID NOT STOP'} ({msg})")
            ok &= det and guard
            print(f"[control] {'PASS' if det and guard else 'FAIL'}")
    print("BELGRADE CAUSALITY: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
