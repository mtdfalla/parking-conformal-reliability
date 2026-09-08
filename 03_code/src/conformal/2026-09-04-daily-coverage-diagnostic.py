#!/usr/bin/env python3
"""X09 diagnostic — uneven daily coverage in the Belgrade export, and what it confounds.

FOUND 2026-09-04 (revision 39) while running task 5b. Fold F1's day-of-week partition showed
Cramer's V = 0.48 against time-of-day, where a regular grid should give ~0. The cause is not the
pipeline: the RAW export itself covers some calendar days only partially -- 15 March carries about an
eighth of a full day. Within any short window this makes WEEKDAY structurally confounded with
TIME-OF-DAY, because a partially covered day contributes only some hours.

Same class as X08 and S02/X01: a source property that no structural integrity check asks about.
Verified against `01_data/raw/belgrade_RAW.csv` as well as the v2 table, so it is not pipeline-induced.

Outputs: 05_results/tables/2026-09-04-daily-coverage-belgrade.csv
         05_results/tables/2026-09-04-window-confound.csv
"""
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
BUCKETS = [("night", 0, 5), ("am_rush", 6, 9), ("midday", 10, 15),
           ("pm_rush", 16, 19), ("evening", 20, 23)]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WINDOWS = [("F1 fold test", "2017-03-13", "2017-03-16"),
           ("F2 fold test", "2017-03-16", "2017-03-19"),
           ("F3 fold test", "2017-03-19", "2017-03-22"),
           ("main test split", "2017-03-18", "2017-03-22")]


def bucket_of(h):
    for nm, a, b in BUCKETS:
        if a <= h <= b:
            return nm
    return "night"


def cramers_v(x, y) -> float:
    ct = pd.crosstab(pd.Series(x), pd.Series(y)).values.astype(float)
    n = ct.sum()
    if n == 0 or min(ct.shape) < 2:
        return np.nan
    exp = np.outer(ct.sum(1), ct.sum(0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(exp > 0, (ct - exp) ** 2 / exp, 0.0))
    return float(np.sqrt((chi2 / n) / (min(ct.shape) - 1)))


def main() -> None:
    d = pd.read_parquet(PROC/"belgrade_features_v2.parquet")
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    nfac = d.facility_id.nunique()
    full = 288 * nfac                      # 5-min cadence x facilities

    d["day"] = d.timestamp.dt.date
    g = d.groupby("day").agg(rows=("occupancy", "size"), used_15=("use_15", "sum"))
    g["pct_of_full_day"] = (100 * g.rows / full).round(1)
    g["distinct_hours"] = d.groupby("day").timestamp.apply(lambda s: s.dt.hour.nunique())
    g["weekday"] = [DAYS[pd.Timestamp(i).dayofweek] for i in g.index]
    g = g[["weekday", "rows", "used_15", "pct_of_full_day", "distinct_hours"]]
    g.to_csv(TAB/"2026-09-04-daily-coverage-belgrade.csv")
    print("Belgrade daily coverage (a full day = 288 slots x "
          f"{nfac} facilities = {full} rows):")
    print(g.to_string())

    rows = []
    u = d[d.use_15]
    for name, a, b in WINDOWS:
        w = u[(u.timestamp >= pd.Timestamp(a)) & (u.timestamp < pd.Timestamp(b))]
        ts = w.timestamp
        wd, bk = ts.dt.dayofweek.map(lambda i: DAYS[i]).values, ts.dt.hour.map(bucket_of).values
        per_day = w.groupby(w.timestamp.dt.date).size()
        rows.append(dict(window=name, start=a, end=b, n_rows=len(w),
                         n_dates=int(ts.dt.date.nunique()),
                         equivalent_full_days=round(len(w) / full, 2),
                         min_day_pct=round(100 * per_day.min() / full, 1),
                         max_day_pct=round(100 * per_day.max() / full, 1),
                         cramers_v_weekday_vs_tod=round(cramers_v(wd, bk), 3)))
    r = pd.DataFrame(rows)
    r.to_csv(TAB/"2026-09-04-window-confound.csv", index=False)
    print("\nWhat this does to each evaluation window "
          "(V = association between weekday and time-of-day; 0 = orthogonal):")
    print(r.to_string(index=False))
    print("\nA window whose days are unequally covered cannot support a day-of-week analysis:")
    print("weekday and time-of-day are not separable in it, and time-of-day is the axis ToD-ACI")
    print("conditions on, so any day-of-week 'transfer' measured there is partly the ToD axis again.")


if __name__ == "__main__":
    main()
