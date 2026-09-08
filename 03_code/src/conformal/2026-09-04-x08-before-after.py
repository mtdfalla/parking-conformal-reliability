#!/usr/bin/env python3
"""EXP-027 — publish the before/after table of EVERY number the D-018 exclusion changes.

Reads the control and filtered re-aggregations produced by `2026-09-04-x08-reaggregate.py` and emits
one long-format CSV: experiment, statistic key, before, after, delta, and whether the row changed.
The control column is the LOGGED value (proved identical to it by the negative control), so this table
is also the audit trail from the published numbers to the corrected ones.
"""
from pathlib import Path
import pandas as pd

TAB = Path(__file__).resolve().parents[3] / "05_results" / "tables"
OUT = TAB / "2026-09-04-x08-before-after.csv"
TOL = 5e-5

SETS = [
    ("EXP-017/019 core headline", "core-headline", ["city", "horizon", "method"]),
    ("EXP-025 E3 baselines", "e3-summary", ["dataset", "horizon", "level", "method"]),
    ("EXP-020 base learners", "base-learner", ["base", "level", "method"]),
    ("EXP-021 time-of-day", "tod-summary", ["method", "scope", "bucket"]),
    ("EXP-022 orthogonal partition", "orthogonal-summary", ["partition", "method"]),
    ("EXP-024 trust/abstain", "trust-abstain", ["method", "commit_target"]),
]


def main() -> None:
    rows = []
    for label, stem, keys in SETS:
        a = pd.read_csv(TAB / f"2026-09-04-x08-{stem}-control.csv")
        b = pd.read_csv(TAB / f"2026-09-04-x08-{stem}-excl.csv")
        for k in keys:
            for d in (a, b):
                d[k] = d[k].astype(str)
        m = a.merge(b, on=keys, how="outer", suffixes=("_before", "_after"))
        num = [c for c in a.columns if c not in keys
               and pd.api.types.is_numeric_dtype(a[c]) and f"{c}_after" in m.columns]
        for _, r in m.iterrows():
            unit = " | ".join(str(r[k]) for k in keys)
            for c in num:
                x, y = r[f"{c}_before"], r[f"{c}_after"]
                if pd.isna(x) and pd.isna(y):
                    continue
                d = (y - x) if (pd.notna(x) and pd.notna(y)) else float("nan")
                rows.append(dict(
                    experiment=label, unit=unit, statistic=c,
                    before=x, after=y, delta=d,
                    changed=bool(pd.isna(d) or abs(d) > TOL)))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    ch = out[out.changed]
    print(f"wrote {OUT.name}: {len(out)} statistics, {len(ch)} changed, "
          f"{len(out) - len(ch)} unchanged")
    print()
    print("changed statistics per experiment:")
    print(ch.groupby('experiment').size().to_string())


if __name__ == "__main__":
    main()
