#!/usr/bin/env python3
"""
EXP-029 analysis — the allocation vignette, seed distributions, the prespecified decision rule,
and the two diagnostics that explain the result.

Reads  05_results/tables/2026-09-04-vignette-seeds.csv   (written by 2026-09-04-allocation-vignette.py)
Writes 05_results/tables/2026-09-04-vignette-summary.csv          per window x policy, over 20 seeds
       05_results/tables/2026-09-04-vignette-contrasts.csv        the prespecified contrasts, with CIs
       05_results/tables/2026-09-04-vignette-x08-attribution.csv  where the ARCHIVED effect came from
       05_results/tables/2026-09-04-vignette-overflow-capability.csv   input-only: can the outcome occur?
       05_results/figures/2026-09-04-vignette-overflow-capability.png

The last two are INPUT-ONLY diagnostics: neither reads any policy's performance. They exist because the
prespecified contrast turned out to be degenerate and the question "why" is answered on the inputs.
No evaluation criterion is changed here. The capability table reports what the DATA can support under
alternative fullness thresholds; it is decision support for the author, NOT a result, and no policy
comparison is computed at any threshold other than the prespecified one.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
TAB = ROOT / "05_results" / "tables"; FIG = ROOT / "05_results" / "figures"
B_BOOT = 10_000; SEED = 42
WINDOWS = {"weekday": (20, 21), "weekend": (18, 19)}
HOURS = (12, 19)


def logged_path(name: str) -> Path:
    """Locate an ARCHIVED logged artifact that no live step regenerates (see EXP-035, C14).

    In the REPOSITORY these sit in `05_results/tables/`; in the SHIPPED PACKAGE that directory is the
    replicator's own empty output directory and our outputs live in `05_results/reference/`, so a
    from-scratch run raised FileNotFoundError. Prefer tables/, fall back to reference/. Never invert it,
    and never copy the archived file INTO tables/ -- pre-seeding a replicator's output directory with our
    numbers would let a run "reproduce" a file we handed them.
    """
    p = TAB / name
    return p if p.exists() else (ROOT / "05_results" / "reference" / name)


def boot_ci(x, B=B_BOOT, seed=SEED):
    x = np.asarray(x, float)
    if len(x) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    m = rng.choice(x, size=(B, len(x)), replace=True).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    d = pd.read_csv(TAB / "2026-09-04-vignette-seeds.csv")

    # ---- per window x policy, across seeds -----------------------------------------------------
    rows = []
    for (w, p), g in d.groupby(["window", "policy"]):
        rec = dict(window=w, policy=p, n_seeds=len(g),
                   n_base=int(g.n_base.iloc[0]), n_slots=int(g.n_slots.iloc[0]),
                   excluded=g.excluded.iloc[0], anchor=g.anchor.iloc[0],
                   margin_m=round(float(g.margin_m.iloc[0]), 4))
        for c in ["assigned_rate", "overflow_rate", "unserved_or_overflow_rate",
                  "mean_straight_line_km", "p90_straight_line_km"]:
            v = g[c].values
            lo, hi = boot_ci(v)
            rec[f"{c}_mean"] = round(float(np.mean(v)), 6)
            rec[f"{c}_sd"] = round(float(np.std(v, ddof=1)), 6)
            rec[f"{c}_min"] = round(float(np.min(v)), 6)
            rec[f"{c}_max"] = round(float(np.max(v)), 6)
            rec[f"{c}_ci_lo"] = round(lo, 6); rec[f"{c}_ci_hi"] = round(hi, 6)
        rows.append(rec)
    summ = pd.DataFrame(rows).sort_values(["window", "policy"])
    summ.to_csv(TAB / "2026-09-04-vignette-summary.csv", index=False)

    # ---- the prespecified contrasts, paired within seed -----------------------------------------
    piv = d.pivot_table(index=["window", "seed"], columns="policy",
                        values=["overflow_rate", "mean_straight_line_km", "assigned_rate"])
    crows = []
    for w in sorted(d.window.unique()):
        s = piv.loc[w]
        pairs = [("overflow_reduction_pp", "overflow_rate", "POINT", "INTERVAL", 100.0),
                 ("additional_straight_line_m", "mean_straight_line_km", "INTERVAL", "POINT", 1000.0),
                 ("margin_vs_interval_overflow_pp", "overflow_rate", "MARGIN", "INTERVAL", 100.0),
                 ("margin_vs_interval_addl_straight_line_m", "mean_straight_line_km", "MARGIN", "INTERVAL", 1000.0)]
        for name, col, a, b, scale in pairs:
            delta = (s[(col, a)] - s[(col, b)]).values * scale
            lo, hi = boot_ci(delta)
            crows.append(dict(window=w, contrast=name, unit=("pp" if scale == 100 else "m"),
                              n_seeds=len(delta), mean=round(float(np.mean(delta)), 4),
                              sd=round(float(np.std(delta, ddof=1)), 4),
                              median=round(float(np.median(delta)), 4),
                              iqr=round(float(np.percentile(delta, 75) - np.percentile(delta, 25)), 4),
                              min=round(float(np.min(delta)), 4), max=round(float(np.max(delta)), 4),
                              ci_lo=round(lo, 4), ci_hi=round(hi, 4),
                              n_seeds_positive=int((delta > 0).sum()),
                              ci_excludes_zero=int(not (lo <= 0 <= hi))))
    con = pd.DataFrame(crows)
    con.to_csv(TAB / "2026-09-04-vignette-contrasts.csv", index=False)

    # ---- diagnostic 1: where the ARCHIVED effect came from ---------------------------------------
    r = pd.read_csv(logged_path("2026-08-04-allocation-vignette-requests.csv"))
    arows = []
    for pol, g in r.groupby("policy"):
        tot = int(g.overflow.sum())
        for fac, gg in g.groupby("assigned"):
            arows.append(dict(source="EXP-015 archived", policy=pol, facility_id=int(fac),
                              n_assigned=len(gg), n_overflow=int(gg.overflow.sum()),
                              overflow_rate_at_facility=round(float(gg.overflow.mean()), 4),
                              share_of_policy_overflows=(round(int(gg.overflow.sum()) / tot, 4) if tot else 0.0)))
    att = pd.DataFrame(arows).sort_values(["policy", "n_overflow"], ascending=[True, False])
    att.to_csv(TAB / "2026-09-04-vignette-x08-attribution.csv", index=False)

    # ---- diagnostic 2: input-only, can the outcome event occur at all? ---------------------------
    df = pd.read_parquet(ROOT / "01_data" / "processed" / "belgrade_features_v2.parquet")
    df["ts"] = pd.to_datetime(df.timestamp); df = df[df.use_15]
    cap = pd.read_csv(TAB / "2026-09-04-vignette-capacity-proxy.csv").set_index("facility_id")
    te = df[df.split == "test"]
    krows = []
    for wname, days in WINDOWS.items():
        w = te[te.ts.dt.day.isin(days) & (te.ts.dt.hour >= HOURS[0]) & (te.ts.dt.hour < HOURS[1])]
        w = w[w.facility_id.isin(cap.index)]
        for label, sub in (("healthy base (fac 8 excluded)", w[w.facility_id != 8]),
                           ("facility 8 only", w[w.facility_id == 8])):
            if not len(sub):
                continue
            ratio = sub["y_t+15min"].values / cap.loc[sub.facility_id, "cap_train"].values
            for th in [0.90, 0.95, 0.97, 0.98, 0.99, 0.995, 1.00]:
                sel = ratio >= th
                krows.append(dict(window=wname, population=label, threshold_frac_of_cap=th,
                                  n_facility_slots=len(ratio), n_at_or_above=int(sel.sum()),
                                  pct_at_or_above=round(float(sel.mean()) * 100, 3),
                                  facilities=";".join(map(str, sorted(set(
                                      sub.facility_id.values[sel].astype(int).tolist()))))))
    kap = pd.DataFrame(krows)
    kap.to_csv(TAB / "2026-09-04-vignette-overflow-capability.csv", index=False)

    # ---- figure: what the data can and cannot support --------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9), sharey=True)
    for ax, wname in zip(axes, ["weekday", "weekend"]):
        for label, col, mk in (("healthy base (fac 8 excluded)", "#1F4E79", "o"),
                               ("facility 8 only (dead sensor)", "#C00000", "s")):
            s = kap[(kap.window == wname) & (kap.population == label.split(" (dead")[0].replace(
                "healthy base (fac 8 excluded)", "healthy base (fac 8 excluded)"))]
            s = kap[(kap.window == wname) & (kap.population.str.startswith(label.split(" (")[0]))]
            if len(s):
                ax.plot(s.threshold_frac_of_cap * 100, s.pct_at_or_above, marker=mk, color=col, label=label)
        ax.axvline(100, ls=":", c="grey", lw=1)
        ax.set_title(f"{wname} afternoons ({int(kap[kap.window==wname].n_facility_slots.max())} facility-slots)")
        ax.set_xlabel("'full' threshold (% of training capacity proxy)")
    axes[0].set_ylabel("% of facility-slots at or above threshold")
    axes[0].legend(fontsize=7.5, frameon=False)
    fig.suptitle("Can the vignette's outcome event occur? Belgrade test window, t+15 (input-only diagnostic)",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "2026-09-04-vignette-overflow-capability.png", dpi=200)

    print(summ.to_string(index=False)); print()
    print(con.to_string(index=False)); print()
    print(att[att.n_overflow > 0].to_string(index=False))
    print("\nwrote 4 CSVs + 1 figure")


if __name__ == "__main__":
    main()
