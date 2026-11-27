#!/usr/bin/env python3
"""Spatial uncertainty analysis (RQ4, Belgrade) — novelty differentiator.
Does prediction uncertainty have spatial structure? (nearby facilities hard together => justify spatial/graph CP)

2026-11-25 successor of `2026-09-05-spatial-analysis.py` (external-audit finding T006, EXP-045 arm A3).
The spatial leg now runs on the canonical pipeline of `2026-11-22-run-core-methods.py`, and nothing else
changes (same statistics, same seed, same permutation counts, same columns):
  * features from `belgrade_features_v2.parquet` with the `use_15` mask and the runner's dropna, in place
    of the v1 table with no availability mask;
  * the per-facility ACI half-width is the conformal radius q of `core.adaptive_conformal_stream` (delayed
    release, h = 3 steps, level 0.90, unclipped q as in the old `aci_hw`) at each facility's shipped
    calibrated gamma, read from `2026-11-22-core-belgrade-v3-gcal-per-facility.csv`, in place of the old
    immediate-feedback recursion at the fixed gamma 0.05;
  * positive control: each facility's ACI covered count equals the shipped table's ACI PICP x n_test
    exactly, or the run stops. `--check-only shipped` runs the control alone and writes nothing.
    `--check-only fixed005` runs it with the retired gamma 0.05 and must FAIL (negative control);
  * outputs carry 2026-11-25 names (statistics CSV, the two per-facility and pairwise tables, figures).
"""
# 2026-09-05 (revision 45, EXP-036, defect 7). Derived from the frozen pre-audit
# `spatial_analysis.py` by DELETING the block that appended an `EXP-006` entry to
# 04_experiments/EXPERIMENTS_LOG.md. Nothing else differs: same statistics, same CSVs, same
# figures. `verify.py` checks that tracker by exact hash, so the append made every replication
# run mutate a manifest-listed document and then fail the package's own verifier -- every run,
# on every machine, with a different hash each day because the entry carried a datetime.now()
# stamp. A result-generating script must not edit a living tracker as a side effect.
# The original is byte-identical in `_retired/` and is registered in
# 00_admin/2026-09-02-preaudit-freeze/2026-09-04-FREEZE-DELTAS.md; do not run it.

from __future__ import annotations
import argparse, math, sys
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from scipy.stats import spearmanr

HERE=Path(__file__).resolve(); ROOT=HERE.parents[3]
PROC=ROOT/"01_data"/"processed"; FIG=ROOT/"05_results"/"figures"; TAB=ROOT/"05_results"/"tables"
for d in (FIG,TAB): d.mkdir(parents=True,exist_ok=True)
FEATURES=["lag_5min","lag_10min","lag_15min","lag_30min","lag_45min","lag_60min",
          "roll_mean_30min","roll_std_30min","roll_mean_60min","roll_std_60min",
          "tod_sin","tod_cos","dow","is_weekend","is_holiday"]
HZ="y_t+15min"; SEED=42; N_TREES=100; DYN_STD=5.0
HMIN=15; HSTEPS=3; LEVEL=0.90   # canonical Belgrade primary horizon (2026-11-22 runner CFG)
sys.path.insert(0,str(ROOT/"03_code"/"src"/"conformal")); import core
GCAL=TAB/"2026-11-22-core-belgrade-v3-gcal-per-facility.csv"
def log(m): print(f"[spatial] {m}",flush=True)

# 2026-09-06 (revision 48): the printed statistics are ALSO written to a dated CSV, because they were the only
# numbers in the manuscript with no results-table trace (S47 record section 8). Each script rewrites only
# its own rows, so either may be re-run alone without duplicating the other's.
STATS_CSV = TAB/"2026-11-25-spatial-statistics.csv"
def write_stats(script, rows):
    cols=["script","city","horizon","n_facilities","statistic","value","p_value","n_permutations","seed","note"]
    old=[]
    if STATS_CSV.exists() and STATS_CSV.stat().st_size>0:
        old=[r for r in pd.read_csv(STATS_CSV,dtype=str,keep_default_na=False).to_dict("records") if r["script"]!=script]
    for r in rows: r["script"]=script
    out=pd.DataFrame(old+[{c:("" if r.get(c) is None else r.get(c)) for c in cols} for r in rows],columns=cols)
    out.sort_values(["script","statistic"]).to_csv(STATS_CSV,index=False)   # order independent of which script ran last
def haversine(lo1,la1,lo2,la2):
    R=6371.0; p=math.pi/180; dlo=(lo2-lo1)*p; dla=(la2-la1)*p
    a=math.sin(dla/2)**2+math.cos(la1*p)*math.cos(la2*p)*math.sin(dlo/2)**2
    return 2*R*math.asin(math.sqrt(a))
def aci_hw(resid_cal,yhat,y,alpha=0.10,gamma=0.05):
    sc=list(resid_cal); a=alpha; W=len(resid_cal); hw=[]
    for i in range(len(y)):
        a_c=min(max(a,1e-3),1-1e-3); pool=np.asarray(sc[-W:]); n=len(pool)
        lv=min(1.0,math.ceil((n+1)*(1-a_c))/n)
        q=float(np.max(pool)) if lv>=1 else float(np.quantile(pool,lv,method="higher"))
        hw.append(q); c=(y[i]>=yhat[i]-q)and(y[i]<=yhat[i]+q); a=a+gamma*(alpha-(0 if c else 1)); sc.append(abs(y[i]-yhat[i]))
    return np.array(hw)
def morans_I(x,W):
    n=len(x); xb=x-x.mean(); S0=W.sum()
    return (n/S0)*((W*np.outer(xb,xb)).sum()/(xb**2).sum())
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--check-only",choices=["shipped","fixed005"],default=None,
                    help="run the ACI PICP control alone and write nothing; fixed005 is the negative control")
    args=ap.parse_args()
    ref=pd.read_csv(GCAL,float_precision="round_trip")
    ref=ref[(ref.horizon==HZ)&np.isclose(ref.level,LEVEL)&(ref.method=="ACI")].set_index("facility_id")
    df=pd.read_parquet(PROC/"belgrade_features_v2.parquet"); co=pd.read_parquet(PROC/"facility_coords.parquet")
    ds=df[df.split=="train"].groupby("facility_id")["occupancy"].std(); dyn=set(ds[ds>=DYN_STD].index)
    fids=[f for f in sorted(co.facility_id.unique()) if f in dyn]
    log(f"{len(fids)} coord-matched dynamic facilities")
    resid_wide={}; per=[]; n_fail=0
    for fid in fids:
        g=df[df.facility_id==fid].sort_values("timestamp")
        g=g[g[f"use_{HMIN}"]].dropna(subset=["occupancy"]+FEATURES+[HZ])   # the runner's row set
        tr,ca,te=g[g.split=="train"],g[g.split=="calibration"],g[g.split=="test"]
        rf=RandomForestRegressor(n_estimators=N_TREES,min_samples_leaf=2,n_jobs=-1,random_state=SEED)
        rf.fit(tr[FEATURES].values, tr[HZ].values-tr["occupancy"].values)
        yhat_ca=ca["occupancy"].values+rf.predict(ca[FEATURES].values)
        yhat_te=te["occupancy"].values+rf.predict(te[FEATURES].values)
        yte=te[HZ].values; resid=yte-yhat_te
        gam=0.05 if args.check_only=="fixed005" else float(ref.loc[fid,"gamma"])
        a_lo,a_hi,a_dg=core.adaptive_conformal_stream(np.abs(ca[HZ].values-yhat_ca),yhat_te,yhat_te,yte,
                                                      1-LEVEL,HSTEPS,gamma=gam,return_state=True)
        hw=a_dg["q"]                      # the conformal radius, unclipped, as the old aci_hw returned it
        p_ci,_,_=core.interval_metrics(yte,a_lo,a_hi,1-LEVEL)
        n_cov=int(round(p_ci*len(yte))); n_ref=int(round(float(ref.loc[fid,"PICP"])*int(ref.loc[fid,"n_test"])))
        ok=(len(yte)==int(ref.loc[fid,"n_test"])) and (n_cov==n_ref)
        n_fail+=0 if ok else 1
        log(f"  control fac {fid}: gamma={gam:g} n_test={len(yte)}/{int(ref.loc[fid,'n_test'])} covered={n_cov}/{n_ref} {'OK' if ok else 'MISMATCH'}")
        if args.check_only: continue
        resid_wide[fid]=pd.Series(resid,index=pd.to_datetime(te["timestamp"].values))
        c=co[co.facility_id==fid].iloc[0]
        per.append(dict(facility_id=fid,lon=c.longitude,lat=c.latitude,
                        mean_abs_resid=float(np.mean(np.abs(resid))),
                        mean_aci_halfwidth=float(np.mean(hw)),mean_occ=float(te["occupancy"].mean())))
    if n_fail:
        sys.exit(f"[spatial] CONTROL FAIL: {n_fail} of {len(fids)} facilities do not reproduce the shipped ACI PICP")
    log(f"CONTROL PASS: ACI covered counts reproduce the shipped table at all {len(fids)} facilities")
    if args.check_only: return
    P=pd.DataFrame(per); P.to_csv(TAB/"2026-11-25-spatial-facility-uncertainty.csv",index=False)
    RW=pd.DataFrame(resid_wide).dropna(); log(f"common test timestamps: {len(RW)}"); corr=RW.corr()
    pairs=[]
    for i,fi in enumerate(fids):
        for fj in fids[i+1:]:
            ci=P[P.facility_id==fi].iloc[0]; cj=P[P.facility_id==fj].iloc[0]
            pairs.append(dict(fi=fi,fj=fj,dist_km=haversine(ci.lon,ci.lat,cj.lon,cj.lat),resid_corr=float(corr.loc[fi,fj])))
    D=pd.DataFrame(pairs); D.to_csv(TAB/"2026-11-25-spatial-corr-distance.csv",index=False)
    rho,p_sp=spearmanr(D.dist_km,D.resid_corr)
    near=D[D.dist_km<2].resid_corr.mean(); far=D[D.dist_km>5].resid_corr.mean()
    log(f"resid-corr vs distance: Spearman rho={rho:.3f} (p={p_sp:.2e}); near<2km {near:.3f} vs far>5km {far:.3f}")
    n=len(fids); Wm=np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            if i!=j:
                ci=P.iloc[i]; cj=P.iloc[j]; d=haversine(ci.lon,ci.lat,cj.lon,cj.lat); Wm[i,j]=1.0/d if d>0 else 0
    x=P["mean_aci_halfwidth"].values; I=morans_I(x,Wm)
    rng=np.random.default_rng(SEED); perm=np.array([morans_I(rng.permutation(x),Wm) for _ in range(999)])
    p_mi=float((np.sum(np.abs(perm)>=abs(I))+1)/(len(perm)+1))
    log(f"Moran's I={I:.3f}, perm p={p_mi:.3f}")
    write_stats("2026-11-25-spatial-analysis.py",[
        dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="morans_I_mean_aci_halfwidth",value=f"{I:.6f}",p_value=f"{p_mi:.6f}",n_permutations=999,seed=SEED,note="inverse-haversine weights; two-sided permutation p"),
        dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="spearman_rho_residcorr_vs_distance_naive",value=f"{rho:.6f}",p_value=f"{p_sp:.6e}",n_permutations="",seed="",note="pairwise, not independence-corrected"),
        dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="mean_resid_corr_near_lt2km",value=f"{near:.6f}",p_value="",n_permutations="",seed="",note=""),
        dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="mean_resid_corr_far_gt5km",value=f"{far:.6f}",p_value="",n_permutations="",seed="",note="")])
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,6))
    s=ax.scatter(P.lon,P.lat,c=P.mean_aci_halfwidth,s=130,cmap="YlOrRd",edgecolor="k")
    for _,r in P.iterrows(): ax.annotate(int(r.facility_id),(r.lon,r.lat),fontsize=7,ha="center",va="center")
    plt.colorbar(s,label="mean ACI half-width (uncertainty)")
    ax.set_title(f"Belgrade — spatial uncertainty (t+15min)\nMoran's I={I:.2f}, p={p_mi:.3f}")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); fig.tight_layout()
    fig.savefig(FIG/"2026-11-25-spatial-uncertainty-map.png",dpi=130); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5)); ax.scatter(D.dist_km,D.resid_corr,alpha=0.45,s=18,color="#1F4E79")
    bins=np.linspace(0,D.dist_km.max(),9); D["b"]=pd.cut(D.dist_km,bins)
    bm=D.groupby("b",observed=True).agg(d=("dist_km","mean"),c=("resid_corr","mean")).dropna()
    ax.plot(bm.d,bm.c,"-o",color="#C00000",label="binned mean")
    ax.set_xlabel("inter-facility distance (km)"); ax.set_ylabel("residual correlation")
    ax.set_title(f"Residual co-movement vs distance (Spearman {rho:.2f}, p={p_sp:.1e})"); ax.legend(); fig.tight_layout()
    fig.savefig(FIG/"2026-11-25-spatial-corr-vs-distance.png",dpi=130); plt.close(fig)
    allr=pd.concat([pd.DataFrame({"hour":sr.index.hour,"ar":np.abs(sr.values)}) for sr in resid_wide.values()])
    hp=allr.groupby("hour")["ar"].mean()
    fig,ax=plt.subplots(figsize=(8,4)); ax.bar(hp.index,hp.values,color="#1F4E79")
    ax.set_xlabel("hour"); ax.set_ylabel("mean |residual|"); ax.set_title("Belgrade — uncertainty by hour (t+15min)")
    fig.tight_layout(); fig.savefig(FIG/"2026-11-25-uncertainty-by-hour.png",dpi=130); plt.close(fig)
    log("DONE.")
if __name__=="__main__": main()
