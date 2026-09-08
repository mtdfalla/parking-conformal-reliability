#!/usr/bin/env python3
"""Render numbered methodology equations as crisp PNGs via matplotlib mathtext (no LaTeX install)."""
import json
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/"05_results"/"figures"/"eq"; OUT.mkdir(parents=True,exist_ok=True)
EQS={
 "eq1_target": r"$\Pr\!\left(Y^{(m)}_{t+h}\in \mathcal{C}^{(m)}_{t,h}\right)\;\geq\;1-\alpha$",
 "eq2_delta":  r"$\Delta_{t+h}=Y_{t+h}-o_t,\qquad \hat{\Delta}_{t+h}=f_\theta(X_t),\qquad \hat{Y}_{t+h}=o_t+\hat{\Delta}_{t+h}$",
 "eq3_score":  r"$s_i=\left|\,Y_i-\hat{Y}_i\,\right|,\qquad i\in \mathcal{I}_{\mathrm{cal}}$",
 "eq4_quant":  r"$\hat{q}_{1-\alpha}=s_{(k)},\qquad k=\left\lceil (n+1)(1-\alpha)\right\rceil,\;\; n=|\mathcal{I}_{\mathrm{cal}}|$",
 "eq5_interval": r"$\mathcal{C}_{t,h}=\left[\,\hat{Y}_{t+h}-\hat{q}_{1-\alpha},\;\; \hat{Y}_{t+h}+\hat{q}_{1-\alpha}\,\right]$",
 "eq6_guarantee": r"$\Pr\!\left(Y_{n+1}\in \mathcal{C}_{n+1}\right)\;\geq\;1-\alpha\quad\text{(exchangeable }s_1,\dots,s_{n+1})$",
 "eq7_aci": r"$\mathrm{err}_t=\mathbf{1}\!\left\{Y_t\notin \mathcal{C}_t(\alpha_t)\right\},\qquad \alpha_{t+1}=\alpha_t+\gamma\left(\alpha-\mathrm{err}_t\right)$",
 "eq8_todaci": r"$\alpha^{(b)}_{t+1}=\alpha^{(b)}_t+\gamma\left(\alpha-\mathrm{err}_t\right)\;\;\text{for }b=b(t),\qquad b(t)\in\{\mathrm{night,\,AM,\,mid,\,PM,\,eve}\}$",
 "eq9_picp": r"$\mathrm{PICP}=\frac{1}{N}\sum_{i=1}^{N}\mathbf{1}\!\left\{Y_i\in[L_i,U_i]\right\}$",
 "eq10_mpiw": r"$\mathrm{MPIW}=\frac{1}{N}\sum_{i=1}^{N}\left(U_i-L_i\right)$",
 "eq11_winkler": r"$W_\alpha(L,U,y)=(U-L)+\frac{2}{\alpha}(L-y)\mathbf{1}\{y<L\}+\frac{2}{\alpha}(y-U)\mathbf{1}\{y>U\}$",
}
sizes={}
for name,tex in EQS.items():
    fig=plt.figure(figsize=(0.1,0.1))
    t=fig.text(0.5,0.5,tex,ha="center",va="center",fontsize=20,color="#111111")
    p=OUT/f"{name}.png"
    fig.savefig(p,dpi=200,bbox_inches="tight",pad_inches=0.06,facecolor="white"); plt.close(fig)
    from PIL import Image
    w,h=Image.open(p).size; sizes[name]=[w,h]
json.dump(sizes,open(OUT/"eq_sizes.json","w"))
print("rendered",len(EQS),"equations"); print(json.dumps(sizes,indent=0))
