#!/usr/bin/env python3
"""
Pipeline-level causality test of a Birmingham feature builder (register rows 1.1 to 1.3, review finding 11).

  python3 2026-11-22-test-pipeline-causality.py --builder PATH_TO_BUILDER [--expect-fail] [--part single|pipeline|both]

It strengthens `2026-11-22-test-feature-causality.py` in the two ways the independent review asked for.

PART "single": one raw reading at a time. For a fixed sample of facility-day sessions (seed 42) EVERY grid
bin c is a cut, and the FIRST raw reading with timestamp >= c + 30 min is perturbed alone (+50, and
separately deleted). Every non-target column of every row at bins <= c must be unchanged, and the set of
rows at bins <= c must be unchanged under the value shift. A builder that lets one later reading leak
into an earlier row fails here even when a whole-future perturbation happens to cancel.

PART "pipeline": the builder's real `main()`, run end to end on a copy of the raw table. For each of six
global cut times T (three daytime bins empty for every facility, three span quantiles), every reading with timestamp >= floor(T) + 30 min gets a random
value (seed 42, values only: timestamps, record counts and the span are unchanged, so the split boundaries
and MIN_RECORDS, which use the whole span by design, cannot move). The rows at timestamps <= floor(T) must
be the same rows, with every non-target column identical, including the split, use and flag columns.

Time convention: row t is issued at the close of bin t and may use any reading with timestamp < t + 30 min.
Target columns (y_t+*, target_observed_*, target_interpolated_*) and the use_* columns that depend on target
observation are excluded from the "single" deletion comparison only; under value-only perturbation they
must be unchanged as well, except the y_t+* values themselves.

`--expect-fail` is the positive control (C29): pointed at the v2 builder BOTH parts must report violations,
and the script exits 0 only if they do.
"""
from __future__ import annotations
import argparse, importlib.util, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd

SEED = 42; N_SESSIONS = 200; N_GLOBAL_CUTS = 6; STEP = pd.Timedelta(minutes=30)
TARGET_PREFIX = ("y_t+",)
TARGET_DEP_PREFIX = ("y_t+", "target_observed_", "target_interpolated_", "use_")

def load(path):
    spec = importlib.util.spec_from_file_location(f"builder_{abs(hash(str(path)))}", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def cols_except(df, prefixes):
    return [c for c in df.columns if not c.startswith(prefixes)]

def same(a: pd.DataFrame, b: pd.DataFrame, cols) -> bool:
    if len(a) != len(b): return False
    for c in cols:
        if c not in b.columns: return False
        x, y = a[c].values, b[c].values
        if x.dtype.kind in "fc":
            if not np.array_equal(x.astype(float), y.astype(float), equal_nan=True): return False
        elif not (pd.Series(x).astype(str).values == pd.Series(y).astype(str).values).all(): return False
    return True

def part_single(b, long):
    keys = sorted(long.groupby(["facility_id", "day"]).groups.keys())
    rng = np.random.default_rng(SEED)
    pick = [keys[i] for i in sorted(rng.choice(len(keys), size=min(N_SESSIONS, len(keys)), replace=False))]
    gb = long.groupby(["facility_id", "day"])
    checks = viol = 0; first = None
    for k in pick:
        raw = gb.get_group(k)[["timestamp", "occupancy"]].sort_values("timestamp").reset_index(drop=True)
        base = b.build_session(raw.copy(), *k)
        if len(base) < 3: continue
        for c in base["timestamp"]:
            later = np.flatnonzero((raw["timestamp"] >= c + STEP).values)
            if len(later) == 0: continue
            j = later[0]
            for kind in ("shift", "delete"):
                pert = raw.copy()
                if kind == "shift": pert.loc[j, "occupancy"] = pert.loc[j, "occupancy"] + 50.0
                else: pert = pert.drop(index=j)
                out = b.build_session(pert, *k)
                a_ = base[base["timestamp"] <= c].reset_index(drop=True)
                b_ = out[out["timestamp"] <= c].reset_index(drop=True)
                # deleting a reading may legitimately change target_observed of earlier rows; shifting may not
                cols = cols_except(base, TARGET_DEP_PREFIX if kind == "delete" else TARGET_PREFIX)
                checks += 1
                if not same(a_, b_, cols):
                    viol += 1
                    if first is None: first = (k[0], str(k[1]), str(c), kind)
    return checks, viol, first

def run_main(b, raw_df, workdir: Path) -> pd.DataFrame:
    workdir.mkdir(parents=True, exist_ok=True)
    inp = workdir / "birmingham_long.parquet"; raw_df.to_parquet(inp, index=False)
    b.IN = inp; b.PROC = workdir
    if hasattr(b, "OUT"): b.OUT = workdir / "out.parquet"
    argv = sys.argv; sys.argv = ["builder", "--out-dir", str(workdir)]
    import contextlib, io
    try:
        with contextlib.redirect_stdout(io.StringIO()): b.main()
    finally:
        sys.argv = argv
    outs = sorted(p for p in workdir.glob("*.parquet") if p.name != inp.name)
    if len(outs) != 1: raise RuntimeError(f"expected one output parquet, found {[p.name for p in outs]}")
    df = pd.read_parquet(outs[0]); outs[0].unlink()
    return df

def part_pipeline(b, raw_full, tmp: Path):
    raw_full = raw_full.sort_values(["facility_id", "timestamp"]).reset_index(drop=True)
    base = run_main(b, raw_full, tmp / "base")
    ts = pd.to_datetime(raw_full["timestamp"])
    # Cut choice matters. The feed polls every facility at the same jittered instants, so a grid bin is
    # empty for ALL facilities or for none: a cut at the bin of an actual reading never meets an empty
    # bin, and the v2 builder passed six such cuts (revision 56, the positive control caught it). Half the
    # cuts are therefore daytime bins that are empty for every facility with both neighbours observed,
    # which is exactly where an interpolating builder reads the next bin; the rest are span quantiles.
    b30 = ts.dt.floor("30min")
    occ = pd.Series(1, index=pd.DatetimeIndex(b30.unique())).sort_index()
    full = pd.date_range(occ.index.min(), occ.index.max(), freq="30min")
    have = occ.reindex(full, fill_value=0).astype(bool)
    empty = [t for i, t in enumerate(full[1:-1], start=1)
             if not have.iloc[i] and have.iloc[i-1] and have.iloc[i+1] and 9 <= t.hour <= 16]
    n_e = N_GLOBAL_CUTS // 2
    cuts = [empty[i] for i in np.linspace(0, len(empty) - 1, n_e).astype(int)] if empty else []
    cuts += [ts.quantile(q).floor("30min") for q in np.linspace(0.15, 0.85, N_GLOBAL_CUTS - len(cuts))]
    rng = np.random.default_rng(SEED)
    checks = viol = 0; first = None
    key = ["facility_id", "timestamp"]
    for i, T in enumerate(cuts):
        pert = raw_full.copy(); pert["occupancy"] = pert["occupancy"].astype(float)
        later = pd.to_datetime(pert["timestamp"]) >= T + STEP
        cap = pert.loc[later, "capacity"].astype(float).values if "capacity" in pert else 500.0
        pert.loc[later, "occupancy"] = rng.uniform(0, 1, later.sum()) * cap
        out = run_main(b, pert, tmp / f"cut{i}")
        a_ = base[base["timestamp"] <= T].sort_values(key).reset_index(drop=True)
        b_ = out[out["timestamp"] <= T].sort_values(key).reset_index(drop=True)
        cols = cols_except(base, TARGET_PREFIX)
        checks += 1
        if not same(a_, b_, cols):
            viol += 1
            if first is None:
                bad = [c for c in cols if len(a_) == len(b_) and not same(a_, b_, [c])]
                first = (str(T), f"rows {len(a_)} vs {len(b_)}", bad[:6])
    return checks, viol, first, len(base)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--builder", required=True)
    ap.add_argument("--expect-fail", action="store_true")
    ap.add_argument("--part", choices=["single", "pipeline", "both"], default="both")
    args = ap.parse_args()
    b = load(args.builder)
    raw = pd.read_parquet(b.IN)
    print(f"[pipeline-causality] builder: {Path(args.builder).name}")
    results = {}
    if args.part in ("single", "both"):
        long = raw.copy()
        long["occupancy"] = long["occupancy"].clip(lower=0).astype(float)
        long["timestamp"] = pd.to_datetime(long["timestamp"]); long["day"] = long["timestamp"].dt.date
        c, v, f = part_single(b, long)
        print(f"[pipeline-causality] single-reading: {c} checks, {v} violation(s)" + (f"; first {f}" if f else ""))
        results["single"] = (c, v)
    if args.part in ("pipeline", "both"):
        with tempfile.TemporaryDirectory() as td:
            c, v, f, n = part_pipeline(b, raw.copy(), Path(td))
        print(f"[pipeline-causality] main() end to end: {n} rows built, {c} global cuts, {v} violation(s)"
              + (f"; first {f}" if f else ""))
        results["pipeline"] = (c, v)
    if args.expect_fail:
        ok = all(v > 0 for c, v in results.values())
        print("[pipeline-causality] POSITIVE CONTROL " + ("PASS: every part detects the builder that looks ahead"
                                                          if ok else "FAIL: a part is blind"))
    else:
        ok = all(v == 0 and c > 0 for c, v in results.values())
        print("[pipeline-causality] " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
