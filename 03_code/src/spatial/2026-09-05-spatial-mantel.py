#!/usr/bin/env python3
"""EXP-006b: add a Mantel permutation test (handles non-independence of pairwise correlations) and
explicitly define spatial weights + per-facility uncertainty. Belgrade, delay-aware ACI residuals, t+15min."""
# 2026-09-05 (revision 45, EXP-036, defect 7). Derived from the frozen pre-audit
# `spatial_mantel.py` by DELETING the block that appended an `EXP-006b` entry to
# 04_experiments/EXPERIMENTS_LOG.md. Nothing else differs: same statistics, same CSVs, same
# figures. `verify.py` checks that tracker by exact hash, so the append made every replication
# run mutate a manifest-listed document and then fail the package's own verifier -- every run,
# on every machine, with a different hash each day because the entry carried a datetime.now()
# stamp. A result-generating script must not edit a living tracker as a side effect.
# The original is byte-identical in `_retired/` and is registered in
# 00_admin/2026-09-02-preaudit-freeze/2026-09-04-FREEZE-DELTAS.md; do not run it.

import math
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[3]; PROC=ROOT/"01_data"/"processed"; TAB=ROOT/"05_results"/"tables"
FEAT=["lag_5min","lag_10min","lag_15min","lag_30min","lag_45min","lag_60min","roll_mean_30min","roll_std_30min","roll_mean_60min","roll_std_60min","tod_sin","tod_cos","dow","is_weekend","is_holiday"]
HZ="y_t+15min"; SEED=42; DYN=5.0

# 2026-09-06 (revision 48): the printed statistics are ALSO written to a dated CSV, because they were the only
# numbers in the manuscript with no results-table trace (S47 record section 8). Each script rewrites only
# its own rows, so either may be re-run alone without duplicating the other's.
STATS_CSV = TAB/"2026-09-06-spatial-statistics.csv"
def write_stats(script, rows):
    cols=["script","city","horizon","n_facilities","statistic","value","p_value","n_permutations","seed","note"]
    old=[]
    if STATS_CSV.exists() and STATS_CSV.stat().st_size>0:
        old=[r for r in pd.read_csv(STATS_CSV,dtype=str,keep_default_na=False).to_dict("records") if r["script"]!=script]
    for r in rows: r["script"]=script
    out=pd.DataFrame(old+[{c:("" if r.get(c) is None else r.get(c)) for c in cols} for r in rows],columns=cols)
    out.sort_values(["script","statistic"]).to_csv(STATS_CSV,index=False)   # order independent of which script ran last
def hav(lo1,la1,lo2,la2):
    R=6371;p=math.pi/180;dlo=(lo2-lo1)*p;dla=(la2-la1)*p
    a=math.sin(dla/2)**2+math.cos(la1*p)*math.cos(la2*p)*math.sin(dlo/2)**2;return 2*R*math.asin(math.sqrt(a))
def mantel(A,B,perms=9999,seed=SEED):
    # A,B symmetric matrices; correlation of off-diagonal upper-tri; p via permuting labels
    n=A.shape[0]; iu=np.triu_indices(n,1); a=A[iu]; b=B[iu]
    r=np.corrcoef(a,b)[0,1]; rng=np.random.default_rng(seed); cnt=0
    for _ in range(perms):
        pm=rng.permutation(n); Bp=B[np.ix_(pm,pm)]; rb=np.corrcoef(a,Bp[iu])[0,1]
        if abs(rb)>=abs(r): cnt+=1
    return r,(cnt+1)/(perms+1)
df=pd.read_parquet(PROC/"belgrade_features.parquet"); co=pd.read_parquet(PROC/"facility_coords.parquet")
ds=df[df.split=="train"].groupby("facility_id")["occupancy"].std(); dyn=set(ds[ds>=DYN].index)
fids=[f for f in sorted(co.facility_id.unique()) if f in dyn]
resid={}; 
for fid in fids:
    g=df[df.facility_id==fid].sort_values("timestamp"); tr,te=g[g.split=="train"],g[g.split=="test"]
    rf=RandomForestRegressor(n_estimators=100,min_samples_leaf=2,n_jobs=-1,random_state=SEED); rf.fit(tr[FEAT].values,tr[HZ].values-tr["occupancy"].values)
    yhat=te["occupancy"].values+rf.predict(te[FEAT].values); resid[fid]=pd.Series(te[HZ].values-yhat,index=pd.to_datetime(te["timestamp"].values))
RW=pd.DataFrame(resid).dropna(); n=len(fids)
# distance matrix D and residual-correlation matrix C
D=np.zeros((n,n)); C=RW.corr().loc[fids,fids].values
for i in range(n):
    for j in range(n):
        ci=co[co.facility_id==fids[i]].iloc[0]; cj=co[co.facility_id==fids[j]].iloc[0]
        D[i,j]=hav(ci.longitude,ci.latitude,cj.longitude,cj.latitude)
r_m,p_m=mantel(D,C)
# also Spearman of pairwise (naive) for reference
iu=np.triu_indices(n,1); rho,p_naive=spearmanr(D[iu],C[iu])
print(f"facilities={n} | common test points={len(RW)}")
print(f"Mantel (geo-distance vs residual-correlation): r={r_m:.3f}, permutation p={p_m:.3f}")
print(f"(naive Spearman, not independence-corrected: rho={rho:.3f}, p={p_naive:.2e})")
print(f"mean residual corr: {C[iu].mean():.3f}; near<2km {C[(D<2)&(D>0)].mean():.3f}; far>5km {C[D>5].mean():.3f}")
# raw occupancy co-movement on the same facilities and common test timestamps (the "shared daily cycle" number)
OCC=pd.DataFrame({fid:pd.Series(df[(df.facility_id==fid)&(df.split=="test")].sort_values("timestamp")["occupancy"].values,
                                index=pd.to_datetime(df[(df.facility_id==fid)&(df.split=="test")].sort_values("timestamp")["timestamp"].values)) for fid in fids}).loc[RW.index]
Co=OCC.corr().loc[fids,fids].values; occ_mean=float(Co[iu].mean())
print(f"mean raw-occupancy corr (same facilities, same timestamps): {occ_mean:.3f}")
write_stats("2026-09-05-spatial-mantel.py",[
    dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="mantel_r_distance_vs_residcorr",value=f"{r_m:.6f}",p_value=f"{p_m:.6f}",n_permutations=9999,seed=SEED,note="two-sided permutation p"),
    dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="spearman_rho_residcorr_vs_distance_naive",value=f"{rho:.6f}",p_value=f"{p_naive:.6e}",n_permutations="",seed="",note="pairwise, not independence-corrected"),
    dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="mean_pairwise_resid_corr",value=f"{C[iu].mean():.6f}",p_value="",n_permutations="",seed="",note=f"{len(RW)} common test timestamps"),
    dict(city="belgrade",horizon=HZ,n_facilities=n,statistic="mean_pairwise_raw_occupancy_corr",value=f"{occ_mean:.6f}",p_value="",n_permutations="",seed="",note="same facilities and timestamps; EXP-006 follow-up recorded 0.52")])
print("DONE.")
