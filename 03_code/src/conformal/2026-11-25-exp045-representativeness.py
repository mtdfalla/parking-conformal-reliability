#!/usr/bin/env python3
"""
EXP-045 arm A9 (external-audit findings T044, T090, T028): representativeness of the scored rows.

Three tables, no model fit.

T044, retained against excluded (Birmingham). Candidate rows are the feature-complete rows that pass
the split and embargo rules at horizon H (`split_ok_H & embargo_ok_H` with every model input present).
Retained rows are `use_H`, excluded rows are candidates with `target_observed_H` False, so retained and
excluded partition the candidates (checked). Per horizon and split scope (all splits, test only): counts,
excluded share, and pre-issue covariates of each group: carried-anchor share (`occ_carried`), mean anchor
age in steps, mean hour of issue, mean anchor occupancy, mean anchor occupancy over the facility's
training-window maximum, weekend share.

T090, usable test rows by hour of issue (Birmingham). The rows of each horizon's scored test stream,
counted by the hour of the issue timestamp, 0 to 23 (zero counts kept).

T028, release lag of the delayed stream in clock time (both cities, every horizon). Within each
facility's test stream, the score of step i is released by `core.adaptive_conformal_stream` at stream
index i + h (h in steps). The lag is timestamp[i + h] - timestamp[i] in minutes, for every step whose
release falls inside the stream. The release indices are read from the function itself
(`return_state=True`, `released_at`) on the real stream, not re-derived. Reported: share equal to h,
above h, above 12 h, below h, and the median, 90th percentile and maximum.

Streams are selected exactly as `2026-11-22-run-core-methods.py` selects them: `use_H`, then
`dropna(occupancy, model inputs, target)`, split `test`, sorted by timestamp, facilities with fewer
than 100 / 50 / 50 train / calibration / test rows skipped. Control: every stream's length equals
`n_test` of the shipped gcal per-facility table, and where the shipped per-row table holds the
horizon (Belgrade t+15, every Birmingham horizon) its timestamps equal the stream's exactly. A
mismatch stops the script before anything is written.

Scopes: `all` (every facility with a scored stream) and `paper_base` (dynamic facilities minus the
exclusion set of `2026-09-04-x08-reaggregate.py::exclusion_sets` for that horizon's use flag).

Outputs (05_results/tables): 2026-11-25-exp045-retained-excluded.csv, 2026-11-25-exp045-rows-by-hour.csv,
2026-11-25-exp045-release-lag.csv
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import core

TAB = ROOT / "05_results" / "tables"; PROC = ROOT / "01_data" / "processed"
CFG = {"belgrade": dict(feat="belgrade_features_v2.parquet", H=[("y_t+5min", 5, 1), ("y_t+15min", 15, 3),
                                                                ("y_t+30min", 30, 6)]),
       "birmingham": dict(feat="birmingham_features_v3.parquet", H=[("y_t+30min", 30, 1), ("y_t+60min", 60, 2),
                                                                    ("y_t+90min", 90, 3)])}
DYN = 5.0
OUT_RE = TAB / "2026-11-25-exp045-retained-excluded.csv"
OUT_HR = TAB / "2026-11-25-exp045-rows-by-hour.csv"
OUT_LAG = TAB / "2026-11-25-exp045-release-lag.csv"


def log(m):
    print(f"[repr] {m}", flush=True)


def load_script(fname: str):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_")[:-3], HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def model_inputs(df: pd.DataFrame) -> list:
    return [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]


def streams(df: pd.DataFrame, hz: str, hmin: int) -> dict:
    """{facility_id: sorted test timestamps}, the runner's selection."""
    FEAT = model_inputs(df); out = {}
    for fid in sorted(df.facility_id.unique()):
        g = df[df.facility_id == fid].sort_values("timestamp")
        g = g[g[f"use_{hmin}"]].dropna(subset=["occupancy"] + FEAT + [hz])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
            continue
        out[fid] = te.timestamp.values
    return out


def lag_minutes(ts: np.ndarray, h: int) -> np.ndarray:
    """Release lags from core.adaptive_conformal_stream itself, on a stream of this length."""
    n = len(ts)
    z = np.zeros(n)
    _, _, diag = core.adaptive_conformal_stream(np.ones(20), z, z, z, 0.10, h, gamma=0.0, return_state=True)
    rel = np.array(diag["released_at"], dtype=int).reshape(-1, 2)
    if len(rel) and not (rel[:, 1] - rel[:, 0] == h).all():
        raise SystemExit("[repr] release index is not issue index + h")
    return (ts[rel[:, 1]] - ts[rel[:, 0]]) / np.timedelta64(1, "m")


def main():
    ex = load_script("2026-09-04-x08-reaggregate.py").exclusion_sets()
    ok = True
    lag_rows, hr_rows, re_rows = [], [], []
    for city, cfg in CFG.items():
        df = pd.read_parquet(PROC / cfg["feat"])
        sd = df[df.split == "train"].groupby("facility_id").occupancy.std()
        dyn = {f for f in sd.index if sd[f] >= DYN}
        per = pd.read_csv(TAB / f"2026-11-22-core-{city}-v3-gcal-per-facility.csv")
        rows = pd.read_csv(TAB / f"2026-11-22-core-{city}-v3-gcal-rows-L90.csv",
                           usecols=["facility_id", "horizon", "method", "timestamp"])
        rows = rows[rows.method == "split-CP"]
        for hz, hmin, h in cfg["H"]:
            st = streams(df, hz, hmin)
            # ---- control --------------------------------------------------------------------------
            p = per[(per.horizon == hz) & (per.method == "split-CP") & (per.level == 0.90)]
            nt = dict(zip(p.facility_id, p.n_test))
            bad_n = [f for f in st if nt.get(f) != len(st[f])] + [f for f in nt if f not in st]
            r = rows[rows.horizon == hz]
            bad_t = []
            if len(r):
                for f, ts in st.items():
                    rt = pd.to_datetime(r[r.facility_id == f].timestamp).values
                    if len(rt) != len(ts) or not (rt == ts).all():
                        bad_t.append(f)
            good = not bad_n and not bad_t
            log(f"control {city} {hz}: {len(st)} streams, n_test mismatches {bad_n}, "
                f"timestamp check {'run' if len(r) else 'not available'} mismatches {bad_t}: "
                f"{'PASS' if good else 'FAIL'}")
            ok = ok and good
            base = sorted(f for f in st if f in dyn and f not in ex[(city, f"use_{hmin}")])
            for scope, facs in [("all", sorted(st)), ("paper_base", base)]:
                d = np.concatenate([lag_minutes(st[f], h) for f in facs])
                lag_rows.append(dict(city=city, horizon=hz, h_steps=h, h_minutes=hmin, scope=scope,
                                     n_facilities=len(facs), n_released=len(d),
                                     share_eq_h=float(np.mean(d == hmin)), share_gt_h=float(np.mean(d > hmin)),
                                     share_gt_12h=float(np.mean(d > 720)), share_lt_h=float(np.mean(d < hmin)),
                                     median_min=float(np.median(d)), p90_min=float(np.percentile(d, 90)),
                                     max_min=float(d.max())))
                if city == "birmingham":
                    hrs = pd.Series(np.concatenate([pd.DatetimeIndex(st[f]).hour for f in facs]))
                    vc = hrs.value_counts()
                    for hr in range(24):
                        hr_rows.append(dict(city=city, horizon=hz, scope=scope, n_facilities=len(facs),
                                            hour=hr, n_rows=int(vc.get(hr, 0))))
        if city == "birmingham":
            FEAT = model_inputs(df)
            cap = df[df.split == "train"].groupby("facility_id").occupancy.max()
            fc = df[["occupancy"] + FEAT].notna().all(axis=1)
            for hz, hmin, h in cfg["H"]:
                cand = df[f"split_ok_{hmin}"] & df[f"embargo_ok_{hmin}"] & fc
                ret = cand & df[f"use_{hmin}"]
                exc = cand & ~df[f"target_observed_{hmin}"]
                if (ret & exc).any() or not (ret | exc).eq(cand).all():
                    log(f"CONTROL FAIL: retained and excluded do not partition the candidates at {hz}"); ok = False
                for scope, facs in [("all", sorted(df.facility_id.unique())),
                                    ("paper_base", sorted(f for f in df.facility_id.unique() if f in dyn
                                                          and f not in ex[(city, f"use_{hmin}")]))]:
                    inf = df.facility_id.isin(facs)
                    for split in ["all", "test"]:
                        sp = inf & ((df.split == "test") if split == "test" else True)
                        c_n = int((cand & sp).sum())
                        for grp, m in [("retained", ret & sp), ("excluded", exc & sp)]:
                            g = df[m]
                            re_rows.append(dict(city=city, horizon=hz, scope=scope, split=split, group=grp,
                                                n_facilities=len(facs), n_candidates=c_n, n_rows=len(g),
                                                share_of_candidates=len(g) / c_n if c_n else np.nan,
                                                carried_anchor_share=float(g.occ_carried.mean()),
                                                anchor_age_steps_mean=float(g.anchor_age_steps.mean()),
                                                hour_mean=float(g.timestamp.dt.hour.mean()
                                                                + g.timestamp.dt.minute.mean() / 60),
                                                occupancy_mean=float(g.occupancy.mean()),
                                                occ_over_train_max_mean=float((g.occupancy /
                                                                               g.facility_id.map(cap)).mean()),
                                                weekend_share=float(g.is_weekend.mean())))
    if not ok:
        log("CONTROL FAILED, nothing written"); sys.exit(1)
    outs = [(OUT_RE, pd.DataFrame(re_rows)), (OUT_HR, pd.DataFrame(hr_rows)), (OUT_LAG, pd.DataFrame(lag_rows))]
    with pd.option_context("display.width", 300, "display.max_columns", 40, "display.max_rows", 500):
        for path, t in outs:
            t.to_csv(path, index=False)
            log(f"wrote {path.name} ({len(t)} rows)")
            if path is OUT_HR:
                print(t.pivot_table(index="hour", columns=["scope", "horizon"], values="n_rows").to_string())
            else:
                print(t.to_string())


if __name__ == "__main__":
    main()
