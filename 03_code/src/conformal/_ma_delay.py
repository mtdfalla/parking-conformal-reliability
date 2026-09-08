import math, numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
PROC=Path("../../../01_data/processed").resolve()
FEAT=["lag_5min","lag_10min","lag_15min","lag_30min","lag_45min","lag_60min","roll_mean_30min","roll_std_30min","roll_mean_60min","roll_std_60min","tod_sin","tod_cos","dow","is_weekend","is_holiday"]
HZ="y_t+15min"; H=3; SEED=42
def cqn(n,a): return min(math.ceil((n+1)*(1-a)),n)
def split_cp(r,yh,a): q=np.sort(r)[cqn(len(r),a)-1]; return np.maximum(yh-q,0),yh+q
def aci(r,yh,y,a,h=H,g=0.05,w=None):
    sc=list(r);al=a;w=w or len(r);n=len(y);lo=np.empty(n);hi=np.empty(n);rel={}
    for i in range(n):
        for (rr,e) in rel.pop(i,[]): al=al+g*(a-e); sc.append(rr)
        a_c=min(max(al,1e-3),1-1e-3);pool=np.asarray(sc[-w:]);m=len(pool);lv=min(1.0,cqn(m,a_c)/m)
        q=float(np.max(pool)) if lv>=1 else float(np.quantile(pool,lv,method="higher"))
        lo[i]=max(yh[i]-q,0);hi[i]=yh[i]+q;cov=(y[i]>=yh[i]-q)and(y[i]<=hi[i]);rel.setdefault(i+h,[]).append((abs(y[i]-yh[i]),0 if cov else 1))
    return lo,hi
def wink(y,lo,hi,a): w=hi-lo;s=w.copy();b=y<lo;u=y>hi;s[b]+=(2/a)*(lo[b]-y[b]);s[u]+=(2/a)*(y[u]-hi[u]);return float(np.mean(s))
df=pd.read_parquet(PROC/"belgrade_features.parquet"); ds=df[df.split=='train'].groupby('facility_id')['occupancy'].std(); dyn=sorted(ds[ds>=5].index)
def learner(L):
    return {"RF":RandomForestRegressor(n_estimators=100,min_samples_leaf=2,n_jobs=-1,random_state=SEED),
            "GBM":HistGradientBoostingRegressor(max_iter=150,random_state=SEED),"Ridge":Ridge(alpha=1.0)}[L]
rows=[]
for L in ["RF","GBM","Ridge"]:
  for lvl in [0.90]:
    a=1-lvl; sp={"P":[],"M":[],"W":[]}; ac={"P":[],"M":[],"W":[]}
    for fid in dyn:
        g=df[df.facility_id==fid].sort_values('timestamp');tr,ca,te=g[g.split=='train'],g[g.split=='calibration'],g[g.split=='test']
        m=learner(L);m.fit(tr[FEAT].values,tr[HZ].values-tr['occupancy'].values)
        yhc=ca['occupancy'].values+m.predict(ca[FEAT].values);res=np.abs(ca[HZ].values-yhc)
        yht=te['occupancy'].values+m.predict(te[FEAT].values);yt=te[HZ].values
        slo,shi=split_cp(res,yht,a);alo,ahi=aci(res,yht,yt,a)
        sp["P"].append(np.mean((yt>=slo)&(yt<=shi)));sp["M"].append(np.mean(shi-slo));sp["W"].append(wink(yt,slo,shi,a))
        ac["P"].append(np.mean((yt>=alo)&(yt<=ahi)));ac["M"].append(np.mean(ahi-alo));ac["W"].append(wink(yt,alo,ahi,a))
    rows.append((L,lvl,"split-CP",np.mean(sp["P"]),np.std(sp["P"]),np.mean(sp["M"]),np.mean(sp["W"])))
    rows.append((L,lvl,"ACI",np.mean(ac["P"]),np.std(ac["P"]),np.mean(ac["M"]),np.mean(ac["W"])))
for r in rows: print(f"{r[0]:5} {r[1]} {r[2]:8} PICP {r[3]:.4f} std {r[4]:.4f} MPIW {r[5]:.2f} Wink {r[6]:.2f}")
