#!/usr/bin/env python3
"""ESM figures S1 and S2 on the corrected bases (revision 49, 2026-09-07).

Prespecification: 04_experiments/2026-09-07-esm-figures-PRESPECIFICATION.md.
Reads only manifest-listed tables; recomputes nothing; writes no tracker. The frozen pre-audit makers
(`finalize_corrected.py`, `run_cond_trust_corrected.py`) are untouched and must never be run.

  S1  05_results/figures/2026-09-07-esm-s1-calibration.png/.pdf
      mean AND worst facility coverage vs nominal level, Belgrade t+15, X08-excluded base
  S2  05_results/figures/2026-09-07-esm-s2-spatial-corr-distance.png/.pdf
      pairwise residual correlation vs inter-facility distance, 20-facility exclusion base (D-030);
      revision 60: read from the 2026-11-25 canonical refit (T006, EXP-045 A3)

Revision 61 (T071 rule applied to the ESM): both figures are drawn at their printed width in the ESM (article class,
1 in margins, 6.5 in text width; S1 at 0.98 and S2 at 0.85 of it, scale 1.0) with the previous aspect ratios, every
text element 8 pt, and CQR's colour darkened as in the main figures (contrast 5.3:1 on white).
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
FIG = ROOT / "05_results" / "figures"

FS = 8   # revision 61: minimum text size at final print size
plt.rcParams.update({"font.size": FS, "axes.titlesize": FS, "axes.labelsize": FS, "xtick.labelsize": FS,
                     "ytick.labelsize": FS, "legend.fontsize": FS, "pdf.fonttype": 42, "savefig.dpi": 300, "figure.dpi": 100})
TW = 6.5   # inches: ESM \textwidth (11pt article, margin=1in)
META = {"Software": None, "CreationDate": None, "Creator": None, "Producer": None}
COL = {"split-CP": "#C00000", "CQR": "#1E7A45", "ACI": "#1F4E79", "ACQR": "#7030A0"}
ORDER = ["split-CP", "CQR", "ACI", "ACQR"]
CITY, HZ = "belgrade", "y_t+15min"


def log(m):
    print(f"[esm-fig] {m}", flush=True)


def save(fig, stem):
    fig.savefig(FIG / f"{stem}.png", metadata=META)
    fig.savefig(FIG / f"{stem}.pdf", metadata=META)
    plt.close(fig)
    log(f"wrote {stem}.png / .pdf")


def s1():
    E = pd.read_csv(TAB / "2026-09-06-exp037-pooled-vs-worst.csv")
    d = E[(E.city == CITY) & (E.horizon == HZ) & (E.n_facilities > 0)].copy()
    d["level"] = d["level"].astype(float)
    n_fac = int(d.n_facilities.iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(0.98 * TW, 0.98 * TW * 4.3 / 9.4), sharex=True, sharey=True)
    panels = [("mean_facility_PICP", "mean facility coverage", "(a) mean facility coverage"),
              ("worst_facility_PICP", "worst facility coverage", "(b) worst facility coverage")]
    for ax, (col, ylab, title) in zip(axes, panels):
        lo, hi = 0.78, 0.97
        ax.plot([lo, hi], [lo, hi], "k:", lw=1, label="ideal", zorder=1)
        for m in ORDER:
            s = d[d.method == m].sort_values("level")
            if s.empty:
                continue
            style = dict(color=COL[m], zorder=3)
            if len(s) >= 4:
                ax.plot(s.level, s[col], "-o", ms=4.5, lw=1.3, label=m, **style)
            else:
                ax.plot(s.level, s[col], "s", ms=5.5, label=f"{m} (0.90, 0.95 only)", **style)
        ax.set_xlabel("nominal coverage level")
        ax.set_title(title)
        ax.grid(alpha=0.25, lw=0.5)
        if ax is axes[0]:
            ax.set_ylabel("empirical coverage")
    axes[0].set_xlim(0.775, 0.975)
    axes[0].set_ylim(0.56, 0.98)
    axes[0].legend(loc="lower right", frameon=False)   # revision 61: panel (a) lower right is empty; in (b) the legend covered points
    for _ in range(2):   # revision 61: two passes, as in the main figures
        fig.tight_layout(pad=0.3)
    save(fig, "2026-09-07-esm-s1-calibration")
    for lv in sorted(d.level.unique()):
        r = d[d.level == lv]
        log("  level %.2f: " % lv + "  ".join(
            f"{x.method} mean {x.mean_facility_PICP:.4f} worst {x.worst_facility_PICP:.4f}"
            for x in r.itertuples()))
    log(f"  n_facilities={n_fac}")


def s2():
    S = pd.read_csv(TAB / "2026-11-25-spatial-statistics-exclusion-base.csv")   # revision 60 (T006): canonical pipeline, EXP-045 A3
    E = S[S.population == "exclusion_base"]
    fids = [int(f) for f in str(E.facility_ids.iloc[0]).split(";")]
    val = {r.statistic: (float(r.value), r.p_value) for r in E.itertuples()}
    D = pd.read_csv(TAB / "2026-11-25-spatial-corr-distance.csv")   # revision 60 (T006): pairwise residual correlations of the same refit
    D = D[D.fi.isin(fids) & D.fj.isin(fids)]
    assert len(D) == len(fids) * (len(fids) - 1) // 2, (len(D), len(fids))
    fig, ax = plt.subplots(figsize=(0.85 * TW, 0.85 * TW * 4.6 / 7.4))
    ax.axhline(0.0, color="#888888", lw=0.8, ls="-", zorder=1)
    ax.scatter(D.dist_km, D.resid_corr, alpha=0.45, s=20, color="#1F4E79", lw=0, zorder=2, label="facility pair")
    bins = np.linspace(0, D.dist_km.max(), 9)
    B = D.assign(b=pd.cut(D.dist_km, bins)).groupby("b", observed=True).agg(
        d=("dist_km", "mean"), c=("resid_corr", "mean")).dropna()
    ax.plot(B.d, B.c, "-o", color="#C00000", ms=4.5, lw=1.3, zorder=3, label="binned mean (8 equal-width bins)")
    mr, mp = val["mantel_r_distance_vs_residcorr"]
    sr, sp = val["spearman_rho_residcorr_vs_distance_naive"]
    ax.set_xlabel("inter-facility distance (km)")
    ax.set_ylabel("residual correlation")
    _m = lambda v: f"{v:.3f}".replace("-", "\u2212")   # revision 61 (FIX): a true minus, as on the axis ticks (g7 N7)
    ax.set_title(f"Belgrade, $t{{+}}15$ min, {len(fids)} facilities, {len(D)} pairs\n"
                 f"Mantel $r$ = {_m(mr)} ($p$ = {float(mp):.3f}, 9,999 permutations)\n"
                 f"naive Spearman $\\rho$ = {_m(sr)} ($p$ = {float(sp):.3f}), not independence-corrected",
                 fontsize=FS)
    ax.legend(frameon=False, loc="upper right")
    ax.grid(alpha=0.25, lw=0.5)
    for _ in range(2):   # revision 61: two passes, as in the main figures
        fig.tight_layout(pad=0.3)
    save(fig, "2026-09-07-esm-s2-spatial-corr-distance")
    log(f"  facilities={fids}")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    s1()
    s2()
    log("ALL DONE")
