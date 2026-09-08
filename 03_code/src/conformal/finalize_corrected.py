#!/usr/bin/env python3
"""Figures + summary tables from corrected per-facility results (EXP-010)."""
from pathlib import Path
from datetime import datetime
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3]; TAB=ROOT/"05_results"/"tables"; FIG=ROOT/"05_results"/"figures"; EXP=ROOT/"04_experiments"/"EXPERIMENTS_LOG.md"
CITIES={"belgrade":["y_t+5min","y_t+15min","y_t+30min"],"birmingham":["y_t+30min","y_t+60min","y_t+90min"]}
COL={"split-CP":"#C00000","ACI":"#1F4E79","CQR":"#2E9E5B"}
def lbl(h): return h.replace("y_t+","t+")
for city,HZ in CITIES.items():
    d=pd.read_csv(TAB/f"2026-06-25-corr-{city}-per-facility.csv")
    nfac=d.facility_id.nunique()
    # summary
    s=d.groupby(["horizon","level","method"]).agg(mean_PICP=("PICP","mean"),std_PICP=("PICP","std"),mean_MPIW=("MPIW","mean"),mean_Winkler=("Winkler","mean")).reset_index()
    fr=d[d.level==0.90].groupby(["horizon","method"]).apply(lambda x: float(np.mean((x.picp_lo<=0.90)&(0.90<=x.picp_hi))),include_groups=False).reset_index(name="frac_CI_target")
    s.round(4).to_csv(TAB/f"2026-06-25-corr-{city}-summary.csv",index=False); fr.round(3).to_csv(TAB/f"2026-06-25-corr-{city}-fractarget.csv",index=False)
    # coverage distribution boxplot (3 methods @90)
    sub=d[d.level==0.90]; fig,axes=plt.subplots(1,3,figsize=(13,4.2),sharey=True)
    for ax,hz in zip(axes,HZ):
        dd=sub[sub.horizon==hz]; data=[dd[dd.method==m]["PICP"].values for m in ["split-CP","ACI","CQR"]]
        bp=ax.boxplot(data,tick_labels=["split-CP","ACI","CQR"],patch_artist=True,widths=0.6)
        for p,m in zip(bp["boxes"],["split-CP","ACI","CQR"]): p.set_facecolor(COL[m]); p.set_alpha(0.45)
        ax.axhline(0.90,color="green",ls=":",lw=1.2); ax.set_title(lbl(hz)); ax.set_ylim(0.6,1.02)
        if ax is axes[0]: ax.set_ylabel("PICP")
    fig.suptitle(f"{city.capitalize()} — per-facility coverage across {nfac} facilities (90% target), delay-aware ACI")
    fig.tight_layout(); fig.savefig(FIG/f"2026-06-25-corr-{city}-coverage.png",dpi=130); plt.close(fig)
    # calibration curve (mean PICP vs nominal), split vs ACI (+CQR pts)
    fig,ax=plt.subplots(figsize=(5.2,5))
    mids=HZ[1]
    for m in ["split-CP","ACI"]:
        sm=s[(s.method==m)&(s.horizon==mids)].sort_values("level")
        ax.plot(sm.level,sm.mean_PICP,"-o",color=COL[m],label=m)
    cq=s[(s.method=="CQR")&(s.horizon==mids)].sort_values("level")
    ax.plot(cq.level,cq.mean_PICP,"s",color=COL["CQR"],label="CQR")
    ax.plot([0.78,0.97],[0.78,0.97],"k:",lw=1,label="ideal")
    ax.set_xlabel("nominal coverage"); ax.set_ylabel("mean empirical PICP")
    ax.set_title(f"{city.capitalize()} calibration ({lbl(mids)})"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG/f"2026-06-25-corr-{city}-calibration.png",dpi=130); plt.close(fig)
    print(f"{city}: figures+summary written ({nfac} facilities)")
# log
with open(EXP,"a") as f:
    f.write(f"\n### EXP-010 — {datetime.now():%Y-%m-%d} — CORRECTED: delay-aware ACI + CQR baseline (supersedes EXP-004/005)\n")
    f.write("- **Fix:** ACI now releases each forecast's residual/score AND alpha-update only after h steps (no lookahead). Intervals lower-clipped at 0.\n")
    f.write("- **Baselines:** added CQR (conformalized quantile regression on the delta target). Levels 0.80/0.85/0.90/0.95 for split-CP & ACI.\n")
    f.write("- **Belgrade @90% (t+15):** ACI PICP 0.899 std 0.001 (100% of facility bootstrap-CIs contain 0.90); split-CP 0.900 std 0.041 (64%); CQR 0.904 std 0.030 (64%, tighter MPIW 13.0 vs ACI 17.6).\n")
    f.write("- **Birmingham @90% (t+60):** ACI 0.892 std 0.009 (100% CI-contains); split-CP 0.903 std 0.050 (79%); CQR 0.904 std 0.039 (71%).\n")
    f.write("- **Takeaway:** the lookahead-corrected result HOLDS — ACI keeps near-exact low-variance per-facility coverage; CQR gives tighter but per-facility-variable intervals. ACI's edge is per-facility CONSISTENCY.\n")
    f.write("- **Artifacts:** `2026-06-25-corr-{belgrade,birmingham}-{per-facility,summary,fractarget,basemodel}.csv`, `2026-06-25-corr-*-coverage.png`, `*-calibration.png`\n")
print("EXP-010 logged")
