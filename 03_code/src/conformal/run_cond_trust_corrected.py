#!/usr/bin/env python3
"""EXP-007b + EXP-009b corrected: ToD-ACI and trust/abstain with DELAY-AWARE ACI (Belgrade, t+15min=3 steps).
Trust/abstain threshold chosen on CALIBRATION set; MAE reported in cars and % of mean occupancy."""
from pathlib import Path
from datetime import datetime
import math, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
ROOT=Path(__file__).resolve().parents[3]; PROC=ROOT/"01_data"/"processed"; FIG=ROOT/"05_results"/"figures"; TAB=ROOT/"05_results"/"tables"; EXP=ROOT/"04_experiments"/"EXPERIMENTS_LOG.md"
FEAT=["lag_5min","lag_10min","lag_15min","lag_30min","lag_45min","lag_60min","roll_mean_30min","roll_std_30min","roll_mean_60min","roll_std_60min","tod_sin","tod_cos","dow","is_weekend","is_holiday"]
HZ="y_t+15min"; HSTEPS=3; ALPHA=0.10; SEED=42; DYN=5.0; GAMMA=0.05
BUCK=[("night",0,5),("am_rush",6,9),("midday",10,15),("pm_rush",16,19),("evening",20,23)]
def bk(h):
    for nm,a,b in BUCK:
        if a<=h<=b: return nm
    return "night"
def cqn(n,a): return min(math.ceil((n+1)*(1-a)),n)
def aci_delayed(resid,yhat,y,a,h,gamma=GAMMA,window=None,states=None,key=None):
    sc=list(resid); al=a; window=window or len(resid); n=len(y); lo=np.empty(n); hi=np.empty(n); rel={}
    for i in range(n):
        for (r,err) in rel.pop(i,[]): al=al+gamma*(a-err); sc.append(r)
        a_c=min(max(al,1e-3),1-1e-3); pool=np.asarray(sc[-window:]); m=len(pool)
        lv=min(1.0,cqn(m,a_c)/m); q=float(np.max(pool)) if lv>=1 else float(np.quantile(pool,lv,method="higher"))
        lo[i]=max(yhat[i]-q,0.0); hi[i]=yhat[i]+q
        cov=(y[i]>=yhat[i]-q)and(y[i]<=hi[i]); rel.setdefault(i+h,[]).append((abs(y[i]-yhat[i]),0 if cov else 1))
    return lo,hi
def tod_aci_delayed(resid,yhat,y,buckets,a,h,gamma=GAMMA):
    # per-bucket ACI state; each forecast's feedback delayed by h and routed to its bucket
    n=len(y); lo=np.empty(n); hi=np.empty(n)
    st={nm:{"a":a,"sc":list(resid)} for nm,_,_ in BUCK}; rel={}
    for i in range(n):
        for (b,r,err) in rel.pop(i,[]): s=st[b]; s["a"]=s["a"]+gamma*(a-err); s["sc"].append(r)
        b=buckets[i]; s=st[b]; a_c=min(max(s["a"],1e-3),1-1e-3); pool=np.asarray(s["sc"]); m=len(pool)
        lv=min(1.0,cqn(m,a_c)/m); q=float(np.max(pool)) if lv>=1 else float(np.quantile(pool,lv,method="higher"))
        lo[i]=max(yhat[i]-q,0.0); hi[i]=yhat[i]+q
        cov=(y[i]>=yhat[i]-q)and(y[i]<=hi[i]); rel.setdefault(i+h,[]).append((b,abs(y[i]-yhat[i]),0 if cov else 1))
    return lo,hi
def main():
    df=pd.read_parquet(PROC/"belgrade_features.parquet")
    ds=df[df.split=="train"].groupby("facility_id")["occupancy"].std(); dyn=sorted(ds[ds>=DYN].index)
    rec=[]; ta=[]   # conditional records ; trust/abstain
    for fid in dyn:
        g=df[df.facility_id==fid].sort_values("timestamp"); tr,ca,te=g[g.split=="train"],g[g.split=="calibration"],g[g.split=="test"]
        rf=RandomForestRegressor(n_estimators=100,min_samples_leaf=2,n_jobs=-1,random_state=SEED); rf.fit(tr[FEAT].values,tr[HZ].values-tr["occupancy"].values)
        yhat_ca=ca["occupancy"].values+rf.predict(ca[FEAT].values); resid=np.abs(ca[HZ].values-yhat_ca)
        yhat_te=te["occupancy"].values+rf.predict(te[FEAT].values); yte=te[HZ].values
        bte=np.array([bk(h) for h in pd.to_datetime(te["timestamp"].values).hour])
        # global split, ACI, ToD-ACI
        nq=np.sort(resid)[cqn(len(resid),ALPHA)-1]; slo=np.maximum(yhat_te-nq,0); shi=yhat_te+nq
        alo,ahi=aci_delayed(resid,yhat_te,yte,ALPHA,HSTEPS)
        tlo,thi=tod_aci_delayed(resid,yhat_te,yte,bte,ALPHA,HSTEPS)
        for i in range(len(yte)):
            rec.append(dict(bucket=bte[i],split=int(slo[i]<=yte[i]<=shi[i]),ACI=int(alo[i]<=yte[i]<=ahi[i]),ToD_ACI=int(tlo[i]<=yte[i]<=thi[i])))
        # trust/abstain: width on ACI; threshold from CALIBRATION ACI widths to hit commit rates
        # compute ACI half-widths on calibration (delay-aware) to pick thresholds
        alo_c,ahi_c=aci_delayed(resid,yhat_ca,ca[HZ].values,ALPHA,HSTEPS); hw_c=(ahi_c-alo_c)/2
        hw=(ahi-alo)/2; err=np.abs(yte-yhat_te); meanocc=max(te["occupancy"].mean(),1.0)
        for q in np.round(np.arange(0.1,1.0001,0.1),2):
            thr=np.quantile(hw_c,q)               # calibration-chosen width threshold
            commit=hw<=thr
            if commit.sum()==0: continue
            ta.append(dict(fid=fid,commit_target=q,commit_rate=float(commit.mean()),
                           MAE_cars=float(err[commit].mean()),MAE_pct=float(err[commit].mean()/meanocc*100),
                           cov=float(((yte>=alo)&(yte<=ahi))[commit].mean())))
    R=pd.DataFrame(rec); order=[nm for nm,_,_ in BUCK]
    cov=R.groupby("bucket").agg(split=("split","mean"),ACI=("ACI","mean"),ToD_ACI=("ToD_ACI","mean"),n=("split","size")).reindex(order).round(3)
    cov.to_csv(TAB/"2026-06-25-corr-conditional.csv")
    print("CONDITIONAL (delay-aware):\n"+cov.to_string())
    T=pd.DataFrame(ta).groupby("commit_target").agg(commit_rate=("commit_rate","mean"),MAE_cars=("MAE_cars","mean"),MAE_pct=("MAE_pct","mean"),cov=("cov","mean")).round(3)
    T.to_csv(TAB/"2026-06-25-corr-trustabstain.csv")
    print("\nTRUST/ABSTAIN (calibration-chosen threshold):\n"+T.to_string())
    base=pd.DataFrame(ta).groupby("fid").MAE_pct.last()  # ~full-commit baseline not exact; use commit_target=1.0
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8.4,4.6))
    ax.plot(T["commit_rate"]*100,T["MAE_cars"],"-o",color="#1F4E79",label="MAE on committed (cars)")
    ax.set_xlabel("commit rate (%)"); ax.set_ylabel("MAE on committed (cars)")
    ax.set_title("Trust/abstain by ACI width (calibration-chosen thresholds), Belgrade t+15min")
    ax2=ax.twinx(); ax2.plot(T["commit_rate"]*100,T["cov"],"-s",color="#2E9E5B",alpha=.7,label="coverage on committed"); ax2.axhline(0.90,color="green",ls=":"); ax2.set_ylabel("coverage on committed"); ax2.set_ylim(0.8,1.0)
    l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels(); ax.legend(l1+l2,la1+la2,fontsize=8,loc="upper left")
    fig.tight_layout(); fig.savefig(FIG/"2026-06-25-corr-trustabstain.png",dpi=130); plt.close(fig)
    # conditional figure
    x=np.arange(len(order)); w=0.26
    fig,ax=plt.subplots(figsize=(9.5,4.4))
    ax.bar(x-w,cov.split,w,label="split-CP",color="#C00000",alpha=.8); ax.bar(x,cov.ACI,w,label="ACI",color="#1F4E79",alpha=.8); ax.bar(x+w,cov.ToD_ACI,w,label="ToD-ACI",color="#2E9E5B",alpha=.9)
    ax.axhline(0.90,color="green",ls=":"); ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylim(0.6,1.04); ax.set_ylabel("conditional PICP")
    ax.set_title("Conditional coverage by time of day (delay-aware ACI), Belgrade t+15min, 90%"); ax.legend(fontsize=8,ncol=3,loc="upper center")
    fig.tight_layout(); fig.savefig(FIG/"2026-06-25-corr-conditional.png",dpi=130); plt.close(fig)
    with open(EXP,"a") as f:
        f.write(f"\n### EXP-007b/009b — {datetime.now():%Y-%m-%d} — Conditional + trust/abstain (DELAY-AWARE ACI)\n")
        f.write("- **Conditional (worst bucket PICP):** split-CP %.3f, ACI %.3f, ToD-ACI %.3f.\n"%(cov.split.min(),cov.ACI.min(),cov.ToD_ACI.min()))
        f.write("- **Trust/abstain (calibration-chosen width thresholds):** at ~70%% commit, MAE %.2f cars (%.1f%% of mean occ), coverage %.3f.\n"%(T.loc[0.7,"MAE_cars"],T.loc[0.7,"MAE_pct"],T.loc[0.7,"cov"]))
        f.write("- **Artifacts:** `2026-06-25-corr-conditional.csv/.png`, `2026-06-25-corr-trustabstain.csv/.png`\n")
    print("logged EXP-007b/009b")
if __name__=="__main__": main()
