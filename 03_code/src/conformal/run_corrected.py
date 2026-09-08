#!/usr/bin/env python3
"""
Corrected re-run: delay-aware ACI (no lookahead) + CQR baseline + split-CP, with lower-bound clipping at 0,
base-model-by-horizon metrics, multi-level calibration, and per-facility block-bootstrap coverage CIs.
RESUMABLE per facility. Usage: python run_corrected.py --dataset belgrade|birmingham
"""
from __future__ import annotations
import argparse, math, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

HERE=Path(__file__).resolve(); ROOT=HERE.parents[3]
PROC=ROOT/"01_data"/"processed"; TAB=ROOT/"05_results"/"tables"
SEED=42; N_TREES=100; DYN=5.0; GAMMA=0.05
LEVELS_CP=[0.80,0.85,0.90,0.95]; LEVELS_CQR=[0.90,0.95]
CFG={"belgrade":{"feat":"belgrade_features.parquet","H":[("y_t+5min",1),("y_t+15min",3),("y_t+30min",6)]},
     "birmingham":{"feat":"birmingham_features.parquet","H":[("y_t+30min",1),("y_t+60min",2),("y_t+90min",3)]}}
def log(m): print(f"[corr] {m}",flush=True)
def cq_idx(n,a): return min(math.ceil((n+1)*(1-a)),n)
def split_cp(resid,yhat,a):
    q=np.sort(resid)[cq_idx(len(resid),a)-1]; return np.maximum(yhat-q,0.0), yhat+q
def aci_delayed(resid_cal,yhat,y,a,h,gamma=GAMMA,window=None):
    sc=list(resid_cal); al=a; window=window or len(resid_cal); n=len(y)
    lo=np.empty(n); hi=np.empty(n); rel={}
    for i in range(n):
        for (r,err) in rel.pop(i,[]):       # delayed feedback becomes available now
            al=al+gamma*(a-err); sc.append(r)
        a_c=min(max(al,1e-3),1-1e-3); pool=np.asarray(sc[-window:]); m=len(pool)
        lv=min(1.0,cq_idx(m,a_c)/m); q=float(np.max(pool)) if lv>=1 else float(np.quantile(pool,lv,method="higher"))
        lo[i]=max(yhat[i]-q,0.0); hi[i]=yhat[i]+q
        cov=(y[i]>=yhat[i]-q) and (y[i]<=hi[i]); err=0 if cov else 1
        rel.setdefault(i+h,[]).append((abs(y[i]-yhat[i]),err))   # released after h steps
    return lo,hi
def cqr(occ_tr,d_tr,X_tr,occ_ca,y_ca,X_ca,occ_te,y_te,X_te,a):
    glo=HistGradientBoostingRegressor(loss="quantile",quantile=a/2,max_iter=100,random_state=SEED)
    ghi=HistGradientBoostingRegressor(loss="quantile",quantile=1-a/2,max_iter=100,random_state=SEED)
    glo.fit(X_tr,d_tr); ghi.fit(X_tr,d_tr)
    qlo_ca=occ_ca+glo.predict(X_ca); qhi_ca=occ_ca+ghi.predict(X_ca)
    E=np.maximum(qlo_ca-y_ca, y_ca-qhi_ca); qh=np.sort(E)[cq_idx(len(E),a)-1]
    qlo=occ_te+glo.predict(X_te); qhi=occ_te+ghi.predict(X_te)
    return np.maximum(qlo-qh,0.0), qhi+qh
def winkler(y,lo,hi,a):
    w=hi-lo; s=w.copy(); b=y<lo; u=y>hi; s[b]+=(2/a)*(lo[b]-y[b]); s[u]+=(2/a)*(y[u]-hi[u]); return float(np.mean(s))
def mets(y,lo,hi,a): return float(np.mean((y>=lo)&(y<=hi))),float(np.mean(hi-lo)),winkler(y,lo,hi,a)
def boot_ci(cov,B=500,block=20,seed=SEED):
    rng=np.random.default_rng(seed); n=len(cov); nb=max(1,n//block); picp=[]
    for _ in range(B):
        starts=rng.integers(0,n-block+1,size=nb); idx=np.concatenate([np.arange(s,s+block) for s in starts])
        picp.append(cov[idx].mean())
    return float(np.percentile(picp,5)),float(np.percentile(picp,95))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dataset",required=True,choices=list(CFG)); a=ap.parse_args()
    cfg=CFG[a.dataset]; df=pd.read_parquet(PROC/cfg["feat"])
    FEAT=[c for c in df.columns if c.startswith(("lag_","roll_"))]+["tod_sin","tod_cos","dow","is_weekend","is_holiday"]
    ds=df[df.split=="train"].groupby("facility_id")["occupancy"].std(); dyn=sorted(ds[ds>=DYN].index)
    PER=TAB/f"2026-06-25-corr-{a.dataset}-per-facility.csv"
    MAE=TAB/f"2026-06-25-corr-{a.dataset}-basemodel.csv"
    done=set(pd.read_csv(PER).facility_id.unique()) if PER.exists() else set()
    todo=[f for f in dyn if f not in done]; log(f"{a.dataset}: {len(done)} done, {len(todo)} to do")
    import time; t0=time.time(); rows=[]; mrows=[]
    for fid in todo:
        if time.time()-t0>20: log("budget hit; save+exit"); break
        g=df[df.facility_id==fid].sort_values("timestamp"); g=g.dropna(subset=["occupancy"]+FEAT+[h for h,_ in cfg["H"]]); tr,ca,te=g[g.split=="train"],g[g.split=="calibration"],g[g.split=="test"]
        for hz,hsteps in cfg["H"]:
            occ_tr=tr["occupancy"].values; occ_ca=ca["occupancy"].values; occ_te=te["occupancy"].values
            d_tr=tr[hz].values-occ_tr
            rf=RandomForestRegressor(n_estimators=N_TREES,min_samples_leaf=2,n_jobs=-1,random_state=SEED); rf.fit(tr[FEAT].values,d_tr)
            yhat_ca=occ_ca+rf.predict(ca[FEAT].values); resid=np.abs(ca[hz].values-yhat_ca)
            yhat_te=occ_te+rf.predict(te[FEAT].values); yte=te[hz].values
            # base-model MAE/RMSE: RF-delta, persistence, RF-absolute
            rfa=RandomForestRegressor(n_estimators=N_TREES,min_samples_leaf=2,n_jobs=-1,random_state=SEED); rfa.fit(tr[FEAT].values,tr[hz].values)
            yabs=rfa.predict(te[FEAT].values)
            for nm,pred in [("RF-delta",yhat_te),("persistence",occ_te),("RF-absolute",yabs)]:
                e=yte-pred; mrows.append(dict(facility_id=fid,horizon=hz,model=nm,MAE=float(np.mean(np.abs(e))),RMSE=float(np.sqrt(np.mean(e**2)))))
            # split-CP & ACI across calibration levels
            for lvl in LEVELS_CP:
                al=1-lvl
                slo,shi=split_cp(resid,yhat_te,al); alo,ahi=aci_delayed(resid,yhat_te,yte,al,hsteps)
                for meth,(lo,hi) in {"split-CP":(slo,shi),"ACI":(alo,ahi)}.items():
                    p,m,w=mets(yte,lo,hi,al); rec=dict(facility_id=fid,horizon=hz,level=lvl,method=meth,PICP=p,MPIW=m,Winkler=w)
                    if abs(lvl-0.90)<1e-9:
                        clo,chi=boot_ci(((yte>=lo)&(yte<=hi)).astype(float)); rec["picp_lo"]=clo; rec["picp_hi"]=chi
                    rows.append(rec)
            # CQR at 90/95
            for lvl in LEVELS_CQR:
                al=1-lvl; lo,hi=cqr(occ_tr,d_tr,tr[FEAT].values,occ_ca,ca[hz].values,ca[FEAT].values,occ_te,yte,te[FEAT].values,al)
                p,m,w=mets(yte,lo,hi,al); rec=dict(facility_id=fid,horizon=hz,level=lvl,method="CQR",PICP=p,MPIW=m,Winkler=w)
                if abs(lvl-0.90)<1e-9:
                    clo,chi=boot_ci(((yte>=lo)&(yte<=hi)).astype(float)); rec["picp_lo"]=clo; rec["picp_hi"]=chi
                rows.append(rec)
        log(f"fac {fid} done")
    if rows:
        rd=pd.DataFrame(rows); md=pd.DataFrame(mrows)
        if PER.exists(): rd=pd.concat([pd.read_csv(PER),rd],ignore_index=True)
        if MAE.exists(): md=pd.concat([pd.read_csv(MAE),md],ignore_index=True)
        rd.to_csv(PER,index=False); md.to_csv(MAE,index=False)
    per=pd.read_csv(PER); remaining=[f for f in dyn if f not in set(per.facility_id.unique())]
    log(f"REMAINING {a.dataset}: {len(remaining)}" if remaining else f"ALL DONE {a.dataset}: {per.facility_id.nunique()} facilities")
if __name__=="__main__": main()
