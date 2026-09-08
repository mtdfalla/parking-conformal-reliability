#!/usr/bin/env python3
"""Conceptual framework figure (Fig 1) for the manuscript."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
ROOT=Path(__file__).resolve().parents[3]; FIG=ROOT/"05_results"/"figures"
BLUE="#1F4E79"; LBLUE="#D9E2F3"; GREEN="#2E9E5B"; LGREEN="#E2EFDA"; AMBER="#F2C744"; GREY="#7F7F7F"; RED="#C00000"
fig,ax=plt.subplots(figsize=(12,6.2)); ax.set_xlim(0,100); ax.set_ylim(0,62); ax.axis("off")
def box(x,y,w,h,text,fc,ec=BLUE,fs=10,bold=False,tc="#1a1a1a"):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.3,rounding_size=1.2",
        linewidth=1.4,edgecolor=ec,facecolor=fc))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,fontweight="bold" if bold else "normal",color=tc,wrap=True)
def arrow(x1,y1,x2,y2,color=BLUE,style="-|>",ls="-",lw=1.6):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,mutation_scale=16,color=color,lw=lw,linestyle=ls))
# Row of pipeline (y~40)
box(1,42,17,12,"Data\nBelgrade (2-min, 17 d)\nBirmingham (30-min, 76 d)\n+ capacity / coordinates",LBLUE,fs=9,bold=True)
box(21,42,17,12,"Feature engineering\nlags, rolling stats,\ntime-of-day, weekend,\nholidays (gap-aware)",LBLUE,fs=9,bold=True)
box(41,42,18,12,"Change-anchored\nbase model\nŷ = occ(t) + Δ̂\n(model-agnostic)",LGREEN,ec=GREEN,fs=9,bold=True)
box(62,42,15,12,"Temporal split\ntrain / calibration\n/ test\n(no shuffling)",LBLUE,fs=9,bold=True)
arrow(18,48,21,48); arrow(38,48,41,48); arrow(59,48,62,48)
# Conformal layer (center, y~22) — three methods
box(30,22,40,12,"",("#FBFCFE"),ec=BLUE,fs=9)
ax.text(50,32.5,"Conformal prediction layer",ha="center",va="center",fontsize=10.5,fontweight="bold",color=BLUE)
box(31.5,23.5,11.5,6.5,"Split-CP\n(static)",("#F2F2F2"),ec=GREY,fs=8.5)
box(44.2,23.5,11.5,6.5,"ACI\n(adaptive)",LBLUE,ec=BLUE,fs=8.5,bold=True)
box(56.9,23.5,11.5,6.5,"ToD-ACI\n(conditional)",LGREEN,ec=GREEN,fs=8.5,bold=True)
arrow(50,42,50,34.3)  # pipeline -> conformal layer
# Outputs (y~4)
box(8,4,24,12,"Prediction intervals\nvalidity: PICP\nefficiency: MPIW, Winkler\n(per-facility)",LBLUE,fs=9,bold=True)
box(38,4,24,12,"Decision: trust / abstain\ncommit when confident,\nwiden search when not",AMBER and "#FFF2CC",ec=AMBER,fs=9,bold=True)
box(68,4,26,12,"Downstream:\nparking-allocation\noptimisation\n(risk-aware assignment)",LGREEN,ec=GREEN,fs=9,bold=True)
arrow(42,22,20,16.2,color=BLUE)   # layer -> intervals
arrow(32,10,38,10)               # intervals -> decision
arrow(62,10,68,10,color=GREEN)  # decision -> allocation
# feedback loop ACI online update
arrow(46,16,49,23.4,color=RED,ls="--",lw=1.3)
ax.text(40,19.4,"online update\n(realised coverage)",ha="center",va="center",fontsize=7.5,color=RED,style="italic")
ax.text(50,59.5,"A conformal-prediction framework for trustworthy parking-occupancy forecasting",
        ha="center",va="center",fontsize=12.5,fontweight="bold",color="#1a1a1a")
fig.tight_layout(); out=FIG/"2026-06-21-framework.png"; fig.savefig(out,dpi=150,bbox_inches="tight"); print("WROTE",out)
