#!/usr/bin/env python3
"""EXP-037 — pooled-vs-worst-facility pilot, DESCRIPTIVE HALF ONLY (revision 48, 2026-09-06).

Prespecification: 04_experiments/2026-09-06-exp037-PRESPECIFICATION.md (read it first).
Population: 2026-09-02-core-{city}-gcal-per-facility.csv, dynamic, X08-excluded via
core.low_information_facilities on the horizon's TEST rows (never hardcoded), n_fac >= 10.
Units: city x horizon x method x nominal level (96 rows); every statistic is computed WITHIN one level.

Outputs (both per-unit flushed, resumable):
  05_results/tables/2026-09-06-exp037-pooled-vs-worst.csv        (96 rows: 72 populated + 24 SKIPPED marker rows,
      because the source holds CQR / ACQR at the 0.90 and 0.95 levels only -- filter n_facilities > 0)
  05_results/tables/2026-09-06-exp037-ncal-picp-correlation.csv  (12 rows; the D-025 / section 5.8 check)
No correlation between pooled and worst coverage is computed here; no p-value on it; no test. Descriptive only.
"""
from __future__ import annotations
import argparse, csv, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
sys.path.insert(0, str(HERE))
import core  # noqa: E402

OUT_A = TAB / "2026-09-06-exp037-pooled-vs-worst.csv"
OUT_B = TAB / "2026-09-06-exp037-ncal-picp-correlation.csv"
CITIES = {"belgrade": [("y_t+5min", "use_5"), ("y_t+15min", "use_15"), ("y_t+30min", "use_30")],
          "birmingham": [("y_t+30min", "use_30"), ("y_t+60min", "use_60"), ("y_t+90min", "use_90")]}
METHODS = ["split-CP", "CQR", "ACI", "ACQR"]
LEVELS = [0.80, 0.85, 0.90, 0.95]
CORR_METHODS = ["split-CP", "ACI"]
MIN_FAC = 10
TOL = 0.02

COLS_A = ["city", "horizon", "level", "method", "n_facilities", "excluded_facilities", "mean_facility_PICP",
          "pooled_PICP_obs_weighted", "sd_PICP", "worst_facility_id", "worst_facility_PICP", "best_facility_PICP",
          "mean_minus_worst", "n_within_002", "mean_within_002", "n_facilities_below_080", "source_file"]
COLS_B = ["city", "horizon", "level", "method", "n_facilities", "n_cal_min", "n_cal_max", "n_cal_distinct",
          "spearman_rho", "spearman_p", "note"]


def log(m):
    print(f"[exp037] {m}", flush=True)


def done_keys(path, keycols):
    if not path.exists() or path.stat().st_size == 0:   # a 0-byte file (interrupted first write) is "absent"
        return set()
    d = pd.read_csv(path)
    return set(tuple(str(v) for v in r) for r in d[keycols].itertuples(index=False))


def append(path, cols, row):
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerow(row)
        f.flush()


def exclusions(city, flag):
    d = pd.read_parquet(ROOT / "01_data" / "processed" / f"{city}_features_v2.parquet")
    te = d[d.split == "test"]
    return core.low_information_facilities(te[te[flag]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=100.0, help="seconds")
    a = ap.parse_args()
    t0 = time.time()
    doneA = done_keys(OUT_A, ["city", "horizon", "level", "method"])
    doneB = done_keys(OUT_B, ["city", "horizon", "level", "method"])
    remaining = 0
    for city, hzs in CITIES.items():
        src = TAB / f"2026-09-02-core-{city}-gcal-per-facility.csv"
        D = pd.read_csv(src)
        for hz, flag in hzs:
            drop = exclusions(city, flag)
            base = D[(D.horizon == hz) & (D.dynamic) & (~D.facility_id.isin(drop))]
            for lv in LEVELS:
                for m in METHODS:
                    key = (city, hz, f"{lv}", m)
                    if key in doneA and (lv != 0.90 or m not in CORR_METHODS or key in doneB):
                        continue
                    if time.time() - t0 > a.budget:
                        remaining += 1
                        continue
                    s = base[(base.level == lv) & (base.method == m)].dropna(subset=["PICP"])
                    n = int(s.facility_id.nunique())
                    if n < MIN_FAC:
                        # A2: a unit that yields nothing gets a MARKER row, or the resume loop never completes.
                        # The source holds CQR / ACQR at 0.90 and 0.95 only, so 24 of the 96 units are empty at source.
                        if key not in doneA:
                            log(f"SKIPPED {key}: n={n} < {MIN_FAC} -- marker row written")
                            append(OUT_A, COLS_A, dict(city=city, horizon=hz, level=lv, method=m, n_facilities=n,
                                   excluded_facilities="SKIPPED", mean_facility_PICP="", pooled_PICP_obs_weighted="",
                                   sd_PICP="", worst_facility_id="", worst_facility_PICP="", best_facility_PICP="",
                                   mean_minus_worst="", n_within_002="", mean_within_002="", n_facilities_below_080="",
                                   source_file=f"SKIPPED-no-rows-at-source: {src.name} holds no {m} rows at level {lv}"))
                        continue
                    if key not in doneA:
                        worst = s.loc[s.PICP.idxmin()]
                        mean = float(s.PICP.mean())
                        row = dict(city=city, horizon=hz, level=lv, method=m, n_facilities=n,
                                   excluded_facilities=";".join(str(x) for x in drop) or "none",
                                   mean_facility_PICP=round(mean, 6),
                                   pooled_PICP_obs_weighted=round(float(np.average(s.PICP, weights=s.n_test)), 6),
                                   sd_PICP=round(float(s.PICP.std()), 6),
                                   worst_facility_id=int(worst.facility_id),
                                   worst_facility_PICP=round(float(worst.PICP), 6),
                                   best_facility_PICP=round(float(s.PICP.max()), 6),
                                   mean_minus_worst=round(mean - float(worst.PICP), 6),
                                   n_within_002=int(((s.PICP - lv).abs() <= TOL).sum()),
                                   mean_within_002=bool(abs(mean - lv) <= TOL),
                                   n_facilities_below_080=int((s.PICP < 0.80).sum()),
                                   source_file=src.name)
                        append(OUT_A, COLS_A, row)
                    if lv == 0.90 and m in CORR_METHODS and key not in doneB:
                        nc = s.n_cal.astype(float)
                        if nc.nunique() <= 1:
                            rho, p, note = "", "", f"undefined: n_cal constant ({int(nc.iloc[0])}) across all {n} facilities"
                        else:
                            r = spearmanr(nc, s.PICP)
                            rho, p, note = round(float(r.correlation), 6), round(float(r.pvalue), 6), ""
                        append(OUT_B, COLS_B, dict(city=city, horizon=hz, level=lv, method=m, n_facilities=n,
                                                   n_cal_min=int(nc.min()), n_cal_max=int(nc.max()),
                                                   n_cal_distinct=int(nc.nunique()), spearman_rho=rho,
                                                   spearman_p=p, note=note))
    nA = len(done_keys(OUT_A, ["city", "horizon", "level", "method"]))
    nB = len(done_keys(OUT_B, ["city", "horizon", "level", "method"]))
    log(f"rows: pooled-vs-worst {nA}/96, ncal-correlation {nB}/12")
    if remaining or nA < 96 or nB < 12:
        log("REMAINING")
    else:
        log("ALL DONE")


if __name__ == "__main__":
    main()
