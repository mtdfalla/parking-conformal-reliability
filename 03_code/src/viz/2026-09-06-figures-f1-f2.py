#!/usr/bin/env python3
"""F1' / F2' on the X08-excluded base (D-020 items 7-8; revision 48, 2026-09-06).

Prespecification: 04_experiments/2026-09-06-figures-f1-f2-PRESPECIFICATION.md. Reads only manifest-listed
tables; recomputes nothing; writes no tracker. The frozen pre-audit maker (`finalize_corrected.py`) is untouched.

  F1'  05_results/figures/2026-09-06-f1-per-facility-coverage.png/.pdf   (2 cities x 3 horizons, 4 primary methods)
  F2'  05_results/figures/2026-09-06-f2-reliability-efficiency.png/.pdf  (sd of coverage vs mean Winkler, 8 methods)
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
FIG = ROOT / "05_results" / "figures"
sys.path.insert(0, str(HERE.parent / "conformal"))
import core  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "pdf.fonttype": 42,
                     "savefig.dpi": 200, "figure.dpi": 100})
META = {"Software": None, "CreationDate": None, "Creator": None, "Producer": None}
COL = {"split-CP": "#C00000", "CQR": "#2E9E5B", "ACI": "#1F4E79", "ACQR": "#7030A0",
       "EnbPI": "#B8860B", "AgACI-style": "#5B9BD5", "NGBoost": "#7F7F7F", "NGBoost-conformal": "#404040"}
PRIMARY = ["split-CP", "CQR", "ACI", "ACQR"]
CITIES = {"belgrade": [("y_t+5min", "use_5"), ("y_t+15min", "use_15"), ("y_t+30min", "use_30")],
          "birmingham": [("y_t+30min", "use_30"), ("y_t+60min", "use_60"), ("y_t+90min", "use_90")]}
HEADLINE = {"belgrade": "y_t+15min", "birmingham": "y_t+60min"}


def log(m):
    print(f"[f1f2] {m}", flush=True)


def lbl(h):
    return h.replace("y_t+", "t+").replace("min", " min")


def exclusions(city, flag):
    d = pd.read_parquet(ROOT / "01_data" / "processed" / f"{city}_features_v2.parquet")
    te = d[d.split == "test"]
    return core.low_information_facilities(te[te[flag]])


def save(fig, stem):
    fig.savefig(FIG / f"{stem}.png", metadata=META)
    fig.savefig(FIG / f"{stem}.pdf", metadata=META)
    plt.close(fig)
    log(f"wrote {stem}.png / .pdf")


def f1():
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.2), sharey=True)
    rng = np.random.default_rng(42)  # jitter only; fixed so the PNG is byte-stable
    for r, (city, hzs) in enumerate(CITIES.items()):
        D = pd.read_csv(TAB / f"2026-09-02-core-{city}-gcal-per-facility.csv")
        for c, (hz, flag) in enumerate(hzs):
            ax = axes[r, c]
            drop = exclusions(city, flag)
            d = D[(D.horizon == hz) & (D.level == 0.90) & (D.dynamic) & (~D.facility_id.isin(drop))]
            data = [d[d.method == m].PICP.values for m in PRIMARY]
            n = d.facility_id.nunique()
            ax.axhspan(0.88, 0.92, color="#2E9E5B", alpha=0.08, lw=0)
            ax.axhline(0.90, color="#2E9E5B", ls=":", lw=1.1)
            bp = ax.boxplot(data, tick_labels=PRIMARY, patch_artist=True, widths=0.55, showfliers=False,
                            medianprops=dict(color="k", lw=1.2))
            for p, m in zip(bp["boxes"], PRIMARY):
                p.set_facecolor(COL[m]); p.set_alpha(0.35); p.set_edgecolor(COL[m])
            for i, (m, v) in enumerate(zip(PRIMARY, data)):
                x = i + 1 + rng.uniform(-0.16, 0.16, size=len(v))
                ax.scatter(x, v, s=11, color=COL[m], alpha=0.85, zorder=3, lw=0)
                ax.annotate(f"{v.min():.3f}", (i + 1, v.min()), xytext=(0, -9), textcoords="offset points",
                            ha="center", fontsize=7, color=COL[m])
            ax.set_title(f"{city.capitalize()}, {lbl(hz)}, {n} facilities")
            ax.set_ylim(0.72, 1.02)   # nothing lies below 0.76 on this base; the prespecified 0.55 wasted half the panel
            ax.tick_params(axis="x", labelsize=8)
            if c == 0:
                ax.set_ylabel("per-facility coverage (PICP)")
    fig.tight_layout()   # no in-figure title: the caption carries it
    save(fig, "2026-09-06-f1-per-facility-coverage")


def f2():
    core_t = pd.read_csv(TAB / "2026-09-04-x08-core-headline-excl.csv")
    e3 = pd.read_csv(TAB / "2026-09-04-x08-e3-summary-excl.csv")
    t3 = pd.read_csv(TAB / "2026-09-04-T3prime-two-level-inference.csv")
    label = {"NGBoost-conformal": "NGBoost + split-CP (M02)"}
    # label offsets (points) chosen once so no two labels overlap; presentation only
    OFF = {("belgrade", "ACQR"): (6, 8), ("birmingham", "split-CP"): (-6, 8), ("birmingham", "NGBoost-conformal"): (6, -14),
           ("birmingham", "ACI"): (-6, -18), ("birmingham", "ACQR"): (6, -4)}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    n_off = 0
    for ax, city in zip(axes, CITIES):
        hz = HEADLINE[city]
        pts = []
        for m in PRIMARY:
            c = core_t[(core_t.city == city) & (core_t.method == m)].iloc[0]
            w = t3[(t3.city == city) & (t3.method == m)].iloc[0].worst_facility_PICP
            pts.append((m, float(c.Winkler), float(c["std"]), float(w)))
        for m in ["EnbPI", "AgACI-style", "NGBoost", "NGBoost-conformal"]:
            e = e3[(e3.dataset == city) & (e3.method == m)].iloc[0]
            pts.append((m, float(e.mean_Winkler), float(e.sd_PICP), float(e.worst_facility_PICP)))
        wk = np.array([p[1] for p in pts])
        off = []
        for i, p in enumerate(pts):
            others = np.delete(wk, i)
            if p[1] > 1.5 * np.median(others):
                off.append(i)
        n_off += len(off)
        keep = [p for i, p in enumerate(pts) if i not in off]
        xmin, xmax = min(p[1] for p in keep), max(p[1] for p in keep)
        pad = 0.12 * (xmax - xmin)
        xlim = (xmin - pad, xmax + pad + (0.35 * (xmax - xmin) if off else 0))
        ymax = max(p[2] for p in keep) * 1.25
        for m, x, y, w in keep:
            ax.scatter([x], [y], s=55, color=COL[m], edgecolor="k", lw=0.6, zorder=3)
            dx, dy = OFF.get((city, m), (5, 4))
            ax.annotate(f"{label.get(m, m)}\nworst {w:.3f}", (x, y), xytext=(dx, dy), textcoords="offset points",
                        ha="right" if dx < 0 else "left", fontsize=7.2, color=COL[m])
        for i in off:
            m, x, y, w = pts[i]
            xe = xlim[1] - 0.02 * (xlim[1] - xlim[0])
            ye = min(y, ymax * 0.92)
            ax.annotate("", xy=(xe, ye), xytext=(xe - 0.10 * (xlim[1] - xlim[0]), ye),
                        arrowprops=dict(arrowstyle="->", color=COL[m], lw=1.2))
            ax.annotate(f"{m} (off scale):\nWinkler {x:.1f}, sd {y:.3f}, worst {w:.3f}",
                        (xe - 0.10 * (xlim[1] - xlim[0]), ye), xytext=(-4, 6), textcoords="offset points",
                        ha="right", fontsize=7.2, color=COL[m])
        ax.set_xlim(*xlim); ax.set_ylim(0, ymax)
        ax.set_xlabel("mean Winkler score (vehicles; lower is better)")
        ax.set_ylabel("across-facility sd of coverage (lower is better)")
        n = int(core_t[core_t.city == city].n.iloc[0])
        ax.set_title(f"{city.capitalize()}, {lbl(hz)}, {n} facilities, 90% target")
        ax.text(0.98, 0.03, "toward the origin: reliable and efficient", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=7.5, color="#555555", style="italic")
        ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    save(fig, "2026-09-06-f2-reliability-efficiency")
    log(f"off-scale markers: {n_off} (prespecified: 1)")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    f1(); f2()
    log("ALL DONE")
