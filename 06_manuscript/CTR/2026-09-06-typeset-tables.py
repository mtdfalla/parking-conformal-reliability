#!/usr/bin/env python3
"""Typeset the R-Phase 7 display-item table bodies from the logged CSVs (revision 47).
Every number in T2, T3', T4, T5(C) and T6 is read from 05_results/tables/ at build time — never typed.
Output: 06_manuscript/CTR/_build/tables.tex fragments dict (imported by 2026-09-06-apply-rphase7.py).
Not a result-generating script: reads only, writes only under 06_manuscript/CTR/_build/."""
import csv, statistics as st, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "05_results" / "tables"
def rd(name): return list(csv.DictReader(open(T / name, newline="")))
def f(v, d=3): return f"{float(v):.{d}f}"
def pct(v, d=0): return f"{100*float(v):.{d}f}\\%"
out = {}

# ---------------- T2: seven methods + conformalized NGBoost, both cities, X08-excluded base ----------------
core = rd("2026-09-04-x08-core-headline-excl.csv")
e3   = rd("2026-09-04-x08-e3-summary-excl.csv")
t3p  = rd("2026-09-04-T3prime-two-level-inference.csv")
pop  = rd("2026-09-04-phase4-population.csv")
for _x in e3:   # revision 58 (F-30): the summary CSV stores sd to 4 dp (NGBoost Birmingham 0.1505), so a 3-dp print rounded twice; read the full-precision sd of the same arm from the population file
    _p = [y for y in pop if y["city"]==_x["dataset"] and y["method"]==_x["method"]]
    if _p: assert abs(float(_p[0]["sd_PICP"])-float(_x["sd_PICP"])) < 5e-5; _x["sd_PICP"] = _p[0]["sd_PICP"]
# revision 58b (F-30 class): worst_facility_PICP stored at 4 dp sits on a rounding tie (Belgrade AgACI-style 0.8985); read the full-precision value of the same quantity from 2026-09-03-e3-{city}-per-facility.csv
_e3x = {c: set(next(x for x in rd("2026-09-06-exp037-pooled-vs-worst.csv") if x["city"]==c)["excluded_facilities"].split(";")) - {"none"} for c in ["belgrade","birmingham"]}
_e3f = {c: [y for y in rd(f"2026-09-03-e3-{c}-per-facility.csv") if y["arm"]=="A3_v2_daychunk" and y["dynamic"]=="True" and y["status"]=="ok" and y["facility_id"] not in _e3x[c]] for c in _e3x}
for _x in e3:
    _w = min(float(y["PICP"]) for y in _e3f[_x["dataset"]] if y["horizon"]==_x["horizon"] and y["level"]==_x["level"] and y["method"]==_x["method"])
    assert abs(_w-float(_x["worst_facility_PICP"])) < 5e-5; _x["worst_facility_PICP"] = repr(_w)
def core_row(city, m):   return next(x for x in core if x["city"]==city and x["method"]==m)
def e3_row(city, m):     return next(x for x in e3 if x["dataset"]==city and x["method"]==m)
def t3_row(city, m):     return next(x for x in t3p if x["city"]==city and x["method"]==m)
def pop_row(city, m):    return next(x for x in pop if x["city"]==city and x["method"]==m)
def yn(b): return "yes" if str(b)=="True" else "no"
order = [("split-CP","core"),("CQR","core"),("EnbPI","e3"),("AgACI-style","e3"),("NGBoost","e3"),("NGBoost-conformal","e3"),("ACI","core"),("ACQR","core")]
label = {"NGBoost-conformal":"NGBoost + split-CP (M02)","AgACI-style":"AgACI-style"}
rows=[]
for city, hz, n in [("belgrade","t+15 min",21),("birmingham","t+60 min",28)]:
    rows.append(f"\\multicolumn{{8}}{{l}}{{\\emph{{{city.capitalize()}, {hz}, {n} facilities}}}} \\\\")
    for m, src in order:
        p = pop_row(city, m)
        if src=="core":
            c = core_row(city,m); t=t3_row(city,m)
            picp,sd,mpiw,wk,worst = c["PICP"],c["std"],c["MPIW"],c["Winkler"],t["worst_facility_PICP"]
        else:
            e = e3_row(city,m)
            picp,sd,mpiw,wk,worst = e["mean_PICP"],e["sd_PICP"],e["mean_MPIW"],e["mean_Winkler"],e["worst_facility_PICP"]
        rows.append(f" & {label.get(m,m)} & {f(picp)} & {f(sd)} & {f(mpiw,1)} & {f(wk,1)} & {f(worst)} & {yn(p['EXACT_holm'] if src=='core' else p['EXACT_t'])} / {yn(p['SAFE_t'])} \\\\")
    rows.append("\\midrule")
rows.pop()
out["T2"] = "\n".join(rows)
out["T2_meta"] = {
 "bel": {m: core_row("belgrade",m) for m in ["split-CP","CQR","ACI","ACQR"]},
 "bir": {m: core_row("birmingham",m) for m in ["split-CP","CQR","ACI","ACQR"]},
 "bel_e3": {m: e3_row("belgrade",m) for m in ["EnbPI","AgACI-style","NGBoost","NGBoost-conformal"]},
 "bir_e3": {m: e3_row("birmingham",m) for m in ["EnbPI","AgACI-style","NGBoost","NGBoost-conformal"]},
}

# ---------------- T3': two-level inference ----------------
con = rd("2026-09-04-phase4-contrasts.csv")
rows=[]
for city, hz in [("belgrade","t+15 min"),("birmingham","t+60 min")]:
    rows.append(f"\\multicolumn{{8}}{{l}}{{\\emph{{{city.capitalize()}, {hz}}}}} \\\\")
    for m in ["split-CP","CQR","ACI","ACQR"]:
        p=pop_row(city,m); t=t3_row(city,m)
        cells = f"{int(float(t['cells_below_080']))} / {int(float(t['n_cells']))}" if t["cells_below_080"] else "--"
        wcell = f(t["worst_facility_bucket_cell"]) if t["worst_facility_bucket_cell"] else "--"
        ph = float(p["tost_p_holm"]); phs = "$<$0.001" if ph<0.001 else f"{ph:.3f}"
        rows.append(f" & {m} & {f(p['mean_PICP'])} [{f(p['t_lo90'])}, {f(p['t_hi90'])}] & {phs} & {yn(p['EXACT_holm'])} / {yn(p['SAFE_t'])} & {f(p['sd_PICP'])} & {f(t['worst_facility_PICP'])} (\\#{int(float(t['worst_facility']))}) & {wcell} & {cells} \\\\")
    rows.append("\\midrule")
rows.pop()
out["T3p"] = "\n".join(rows)
# contrasts for prose
def con_row(city, fam, c): return next(x for x in con if x["city"]==city and x["family"]==fam and x["contrast"]==c)
out["contrasts"] = {f"{x['city']}|{x['family']}|{x['contrast']}": x for x in con}

# ---------------- T4: conditional coverage, facility x bucket, with Mondrian row and transfer columns ----------------
tod = rd("2026-09-04-x08-tod-summary-excl.csv")
# revision 58b (F-30 class): pooled time-of-day bucket PICP stored at 4 dp sits on a rounding tie (split-CP evening 0.9475); read the full-precision value of the same quantity from 2026-09-03-tod-facility-bucket.csv
_tfa = [y for y in rd("2026-09-03-tod-facility-bucket.csv") if y["dynamic"]=="True" and y["facility_id"] not in _e3x["belgrade"]]
for _x in tod:
    if _x["scope"].startswith("bucket"):
        _g = [y for y in _tfa if y["method"]==_x["method"] and y["bucket"]==_x["bucket"]]
        _v = sum(float(y["PICP"])*int(y["n_cell"]) for y in _g) / sum(int(y["n_cell"]) for y in _g)
        assert abs(_v-float(_x["PICP"])) < 5e-5; _x["PICP"] = repr(_v)
orth = rd("2026-09-04-x08-orthogonal-summary-excl.csv")
def tod_pool(m,b): return next(x for x in tod if x["method"]==m and x["scope"].startswith("bucket") and x["bucket"]==b)
def tod_worst(m):  return next(x for x in tod if x["method"]==m and "WORST" in x["scope"])
def orth_row(part,m): return next(x for x in orth if x["partition"]==part and x["method"]==m)
rows=[]
for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]:
    w=tod_worst(m); o_t=orth_row("time_of_day",m); o_o=orth_row("occupancy_tercile",m); o_d=orth_row("day_of_week",m); o_r=orth_row("random_5",m)
    b=[f(tod_pool(m,k)["PICP"]) for k in ["night","am_rush","midday","pm_rush","evening"]]
    rows.append(f"{m} & " + " & ".join(b) + f" & {f(w['PICP'])} & {int(float(o_t['cells_below_080']))} & {f(o_t['dispersion_ratio_vs_splitCP'],2)} & {f(o_o['dispersion_ratio_vs_splitCP'],2)} & {f(o_d['dispersion_ratio_vs_splitCP'],2)} & {f(o_r['dispersion_ratio_vs_splitCP'],2)} \\\\")
out["T4"] = "\n".join(rows)
out["T4_meta"] = {"V_tercile": orth_row("occupancy_tercile","split-CP")["cramers_v_vs_tod"], "V_dow": orth_row("day_of_week","split-CP")["cramers_v_vs_tod"], "V_rand": orth_row("random_5","split-CP")["cramers_v_vs_tod"],
                  "worst": {m: tod_worst(m) for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]},
                  "pool": {m:{k:tod_pool(m,k)["PICP"] for k in ["night","am_rush","midday","pm_rush","evening"]} for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]},
                  "n_obs": {k: tod_pool("split-CP",k)["n_obs"] for k in ["night","am_rush","midday","pm_rush","evening"]}}

# ---------------- T5(C): relative-threshold allocation, POINT / INTERVAL / MARGIN ----------------
ra = rd("2026-09-05-rel-alloc-summary.csv")
rows=[]
for win in ["weekend","weekday"]:
    rows.append(f"\\multicolumn{{9}}{{l}}{{\\emph{{{win.capitalize()} window}}}} \\\\")
    for x in [y for y in ra if y["window"]==win]:
        b = lambda k: f"{round(600*float(x[k]), 6):.2f}"   # revision 58 (G 2-5): per-600 means over 20 seeds are multiples of 0.05, printed exactly (one decimal rounded 1.05 to 1.0)
        assert all(abs(20*600*float(x[k]) - round(20*600*float(x[k]))) < 1e-6 for k in ["bad_POINT","bad_INTERVAL","bad_MARGIN"])
        dkm = lambda k: f"{1000*(float(x[k])-float(x['km_POINT'])):+.0f}"
        rows.append(f" & {float(x['theta']):.3g} & {int(float(x['facilities_with_event']))} & {b('bad_POINT')} & {b('bad_INTERVAL')} & {b('bad_MARGIN')} & {dkm('km_INTERVAL')} & {dkm('km_MARGIN')} & {int(float(x['seeds_sign_holds']))} / {int(float(x['seeds_beats_margin']))} \\\\")
    rows.append("\\midrule")
rows.pop()
out["T5C"] = "\n".join(rows)
out["T5C_meta"] = {f"{x['window']}|{x['theta']}": x for x in ra}

# ---------------- T6: evaluation-protocol sensitivity (8 logged choices + C01 from the attribution file) ----------------
t6 = rd("2026-09-04-T6-protocol-sensitivity.csv")
c01 = rd("2026-09-04-c01-attribution.csv")
def pick(issue, city, stat_contains):
    return next(x for x in t6 if x["audit_issue"]==issue and x["city"]==city and stat_contains in x["statistic"])
def c01_stats(m):
    rr=[x for x in c01 if x["method"]==m]; dp=[float(x["d_PICP"]) for x in rr]; rw=[float(x["rel_Winkler"]) for x in rr]
    return len(rr), st.mean(dp), max(abs(v) for v in dp), st.mean(rw)
n_aci, m_aci, mx_aci, rw_aci = c01_stats("ACI"); n_acqr, m_acqr, mx_acqr, rw_acqr = c01_stats("ACQR")
def sci(v):
    v=float(v); 
    return f"{v:.1e}".replace("e-0","e-").replace("e-","$\\times 10^{-")+"}$" if v<1e-3 else f"{v:.3f}"
R=[]
x=pick("C07","belgrade","EnbPI mean PICP");   R.append(("EnbPI outcome release: fixed row chunks $\\to$ calendar-day chunks, matured outcomes only (C07)","early release fed the residual pool before outcomes had matured", f"EnbPI mean PICP, Belgrade, paired run: {f(x['before'])} $\\to$ {f(x['after'])}", "against us (fix improves EnbPI)"))
R.append(("Conformal quantile: \\texttt{np.quantile(\\ldots,`higher')} $\\to$ the $\\lceil(n{+}1)(1{-}\\alpha)\\rceil$ order statistic (C01)","the archived rule over-corrected by one rank at $n_{\\mathrm{cal}}\\approx760$", f"ACI $\\Delta$PICP (alternative $-$ adopted) mean {m_aci:+.4f} (max $|\\Delta|$ {mx_aci:.3f}); ACQR {m_acqr:+.4f} ({mx_acqr:.3f}); split-CP and CQR unchanged ({n_aci} facilities)", "small; negative controls exact"))
xa=pick("1.1-1.3 / 2.1","birmingham","anchors used a later reading"); xt=pick("1.1-1.3 / 2.1","birmingham","targets used a later reading")
assert float(xa["after"])==0 and float(xt["after"])==0   # revision 57 re-key (D-039 item 8): the rebuild removes the exposure
R.append(("Feature build: interpolation of empty half-hour bins $\\to$ last observed bin carried at most one step, observed targets only","an interpolated bin averaged in the next bin's reading, so a stored anchor or target used a later reading", f"Birmingham t+60, scored rows using a later reading: anchors {float(xa['before']):.1f}\\% $\\to$ {float(xa['after']):.0f}\\%, targets {float(xt['before']):.1f}\\% $\\to$ {float(xt['after']):.0f}\\%", "exposure removed"))
x1=pick("X08 / D-018","belgrade","ACI across"); x2=pick("X08 / D-018","belgrade","split-CP across"); R.append(("Data quality: retain all facilities $\\to$ exclude facility-windows with $<10$ distinct readings (X08/D-018)","a stuck sensor reporting two values inflated the adaptive methods' dispersion more than split-CP's", f"Belgrade across-facility sd, ACI {f(x1['before'],4)} $\\to$ {f(x1['after'],4)}; split-CP {f(x2['before'],4)} $\\to$ {f(x2['after'],4)}", "mixed (widens the gap to split-CP, narrows it to EnbPI)")); _xr=pick("X08 / D-018","belgrade","RATIO"); assert float(_xr["after"])>float(_xr["before"]) and "EnbPI/ACI ratio weakens" in _xr["direction_vs_our_claim"]
x=pick("EXP-019 / D-016","belgrade","ACI mean PICP"); xb=pick("EXP-019 / D-016","birmingham","ACI mean PICP"); assert float(x["after"])>float(x["before"]) and float(xb["after"])<float(xb["before"])<0.90   # revision 58d (N4): Belgrade moves toward target, Birmingham away
R.append(("ACI step size: fixed $\\gamma=0.05$ $\\to$ selected on a held-out calibration block (EXP-019)","a fixed step is a tuning choice applied to every facility", f"ACI mean PICP, Belgrade: {f(x['before'])} $\\to$ {f(x['after'])}; Birmingham: {f(xb['before'])} $\\to$ {f(xb['after'])}", "mixed (toward target on Belgrade, away on Birmingham)"))
x=pick("I04","belgrade","ACI vs split-CP"); _i04=sorted(float(y["ratio_after_over_before"]) for y in t6 if y["audit_issue"]=="I04"); assert len(_i04)==4 and sum(r>1 for r in _i04)==3; out["i04_ratio"]=_i04
_i04s=", ".join(f"{r:.1f}" if r<1 else f"{r:.0f}" for r in _i04)
R.append(("Unit of inference: pooled fold-facility rows $\\to$ facility-clustered (I04)","each facility appears in every fold; pooling treats repeats as independent", f"$|$gap$|$ p, clustered over pooled, four contrasts: {_i04s} times", "against us in three of four (honest p larger)"))
x1=pick("I01","belgrade","split-CP: fraction"); x2=pick("I01","belgrade","ACI: fraction"); R.append(("Certification: `facility CI contains 0.90' $\\to$ population equivalence + safety bound (I01)","failing to reject equality is not evidence of it; wider intervals pass more easily", f"facilities certified, Belgrade (CI contains 0.90 $\\to$ CI inside $[0.88, 0.92]$): split-CP {pct(x1['before'])} $\\to$ {pct(x1['after'])}; ACI {pct(x2['before'])} $\\to$ {pct(x2['after'])}", "changes the headline"))
x=pick("I01 (second-order)","belgrade","split-CP: PICP"); _nd=[100*(float(y["after"])-0.88) for y in t6 if y["audit_issue"]=="I01 (second-order)" and y["city"]=="belgrade"]; assert len(_nd)==3
# revision 58b (F-30 class): the PICP a facility needs to pass the safety bound stored at 4 dp sits on a rounding tie (ACQR 0.9095); read the full-precision value of the same quantity from 2026-11-22-core-belgrade-v3-gcal-per-facility.csv
_i01 = [y for y in t6 if y["audit_issue"]=="I01 (second-order)" and y["city"]=="belgrade"]
_cbf = [y for y in rd("2026-11-22-core-belgrade-v3-gcal-per-facility.csv") if y["horizon"]=="y_t+15min" and y["level"]=="0.9" and y["dynamic"]=="True" and y["facility_id"] not in _e3x["belgrade"]]
_gap = [st.median(float(z["PICP"])-float(z["picp_ci_lo"]) for z in _cbf if z["method"]==y["statistic"].split(":")[0]) for y in _i01]
assert all(abs(float(y["before"])+g-float(y["after"])) < 5e-5 for y, g in zip(_i01, _gap)); _nd = [100*g for g in _gap]
R.append(("Safety bound applied per facility $\\to$ at the population level (I01, second order)",f"on Belgrade the facility-level lower bound sits {min(_nd):.1f}--{max(_nd):.1f} points below the estimate", f"PICP a Belgrade facility needs to pass: {f(x['after'],3)} $\\to$ {f(x['before'],2)} (split-CP)", "retired criterion rewarded over-coverage"))
x=pick("D01","belgrade","overflow"); R.append(("Capacity proxy: maximum over the full record $\\to$ over the training window only (D01)","one facility's proxy was the constant its dead sensor reported inside the test window, so the policy was scored against a series pinned above its own capacity", "the earlier allocation vignette's overflow reduction disappears entirely once the proxy is corrected (claim retired; replaced by the prespecified demonstration of Section 6.1)", "kills a published claim"))
rows=[f"{a} & {b} & {c} & {d} \\\\" for a,b,c,d in R]
out["T6"] = "\n".join(rows)
out["T6_n"] = len(R)

# ---------------- prose numbers ----------------
ro = rd("2026-09-03-rolling-origin-foldsummary.csv"); roi = rd("2026-09-03-rolling-origin-inference.csv")
# revision 58b (F-30 class): rolling-origin fold mean and worst facility stored at 4 dp sit on rounding ties (F1 split-CP 0.8945, F1 ACQR 0.8445); read the full-precision value of the same quantity from 2026-09-03-rolling-origin-belgrade.csv
_rob = rd("2026-09-03-rolling-origin-belgrade.csv")
_rok = {y["facility_id"] for y in _rob} - {y["facility_id"] for y in _rob if y["dynamic_fold"]!="True"} - _e3x["belgrade"]
_rop = lambda x: [float(y["PICP"]) for y in _rob if y["fold"]==x["fold"] and y["method"]==x["method"] and y["facility_id"] in _rok and y["gamma_mode"] in ("calibrated","","n/a")]
for _x in ro:
    if _x["gamma_mode"]=="calibrated" and _x["population"]=="dynamic_all_folds_x08excl":
        _p = _rop(_x); assert len(_p)==int(float(_x["n_fac"]))
        for _k, _v in [("mean_PICP", st.mean(_p)), ("min_PICP", min(_p))]:
            assert abs(_v-float(_x[_k])) < 5e-5; _x[_k] = repr(_v)
# revision 58b (sd estimator): the fold sd is stored as the population sd (ddof=0) while Tables 2 and 5 print the sample sd (ddof=1); reproduce the stored value from 2026-09-03-rolling-origin-belgrade.csv on the same facilities, then overwrite with the sample sd
for _x in ro:
    if _x["gamma_mode"]=="calibrated" and _x["population"]=="dynamic_all_folds_x08excl":
        _p = _rop(_x); assert abs(st.pstdev(_p)-float(_x["sd_PICP"])) < 5e-5; _x["sd_PICP"] = repr(st.stdev(_p))
out["ro"] = {f"{x['fold']}|{x['method']}": x for x in ro if x["gamma_mode"]=="calibrated" and x["population"]=="dynamic_all_folds_x08excl"}
out["roi"] = {x["contrast"]: x for x in roi if x["gamma_mode"]=="calibrated" and x["population"]=="dynamic_all_folds_x08excl"}
bl = rd("2026-09-04-x08-base-learner-excl.csv")   # revision 58 (G 7.3): the evaluated base (facility 8 excluded), as every other number
# revision 58b (sd estimator): stdPICP is stored as the population sd (ddof=0) while Tables 2 and 5 print the sample sd (ddof=1) of the same facilities; reproduce the stored value from 2026-09-03-base-learner-robustness-per-facility.csv, then overwrite with the sample sd
_blp = [y for y in rd("2026-09-03-base-learner-robustness-per-facility.csv") if y["dynamic"]=="True" and y["facility_id"] not in _e3x["belgrade"]]
for _x in bl:
    _p = [float(y["PICP"]) for y in _blp if y["base"]==_x["base"] and y["method"]==_x["method"] and y["level"]==_x["level"]]
    assert len(_p)==int(float(_x["n_facilities"])) and abs(st.pstdev(_p)-float(_x["stdPICP"])) < 5e-5; _x["stdPICP"] = repr(st.stdev(_p))
out["bl"] = {f"{x['base']}|{x['method']}": x for x in bl if x["level"]=="0.9"}
ta = rd("2026-09-04-x08-trust-abstain-excl.csv")
# revision 58b (F-30 class): commit rate, committed coverage and committed MPIW stored at 3, 4 and 2 dp sit on rounding ties (width rule 0.9 MPIW 10.55); read the full-precision value of the same quantity from 2026-09-03-trust-abstain-per-facility.csv
_tap = [y for y in rd("2026-09-03-trust-abstain-per-facility.csv") if y["dynamic"]=="True" and y["facility_id"] not in _e3x["belgrade"]]
for _x in ta:
    _g = [y for y in _tap if y["method"]==_x["method"] and y["commit_target"]==_x["commit_target"]]; assert len(_g)==int(float(_x["n_facilities"]))
    for _k, _h in [("commit_rate", 5e-4), ("committed_PICP", 5e-5), ("committed_MPIW", 5e-3)]:
        _v = st.mean(float(y[_k]) for y in _g); assert abs(_v-float(_x[_k])) < _h; _x[_k] = repr(_v)
out["ta"] = {f"{x['method']}|{x['commit_target']}": x for x in ta}
ds = rd("2026-09-02-delay-sensitivity-belgrade.csv")
import collections; agg=collections.defaultdict(list)
for x in ds: agg[(x["method"],x["gamma"],x["horizon"])].append(float(x["PICP"]))
out["delay"] = {f"{k[0]}|{k[1]}|{k[2]}": (len(v), st.mean(v)) for k,v in agg.items()}
wc = rd(str((ROOT/"05_results"/"reference"/"2026-09-04-window-confound.csv").relative_to(T))) if False else list(csv.DictReader(open(ROOT/"05_results"/"reference"/"2026-09-04-window-confound.csv")))
out["wc"] = {x["window"]: x for x in wc}
gam=collections.defaultdict(list)
for city in ["belgrade","birmingham"]:
    for x in rd(f"2026-11-22-core-{city}-v3-gcal-per-facility.csv"):
        if x["method"]=="ACI" and x["gamma"]: gam[f"{city}|{x['horizon']}"].append(float(x["gamma"]))
out["gamma_med"] = {k: st.median(v) for k,v in gam.items()}
# ---- revision 48: EXP-037 (descriptive), the n_cal correlation check, the spatial statistics CSV ----
e37 = [x for x in rd("2026-09-06-exp037-pooled-vs-worst.csv") if x["n_facilities"] not in ("0","")]
out["exp037"] = {f"{x['level']}|{x['city']}|{x['horizon']}|{x['method']}": x for x in e37}
nc = rd("2026-09-06-exp037-ncal-picp-correlation.csv")
out["ncal"] = {f"{x['city']}|{x['method']}|{x['horizon']}": x for x in nc}
sp = rd("2026-09-06-spatial-statistics.csv")
out["spatial"] = {x["statistic"] if x["statistic"]!="spearman_rho_residcorr_vs_distance_naive" else f"{x['statistic']}|{x['script']}": x for x in sp}
# ---- revision 49 (D-030): the spatial leg recomputed on the paper's evaluation base (20 facilities).
# The published rows stay in `spatial` as the record of what the live scripts produce; `spatial_excl` is what
# the manuscript now reads, and `spatial_pub21` is the negative control that reproduces the published values.
spx = rd("2026-09-07-spatial-statistics-exclusion-base.csv")
out["spatial_excl"]  = {x["statistic"]: x for x in spx if x["population"] == "exclusion_base"}
out["spatial_pub21"] = {x["statistic"]: x for x in spx if x["population"] == "published_21"}
# ---- revision 57: keys for register rows 3.4, 3.5, 4.1, paragraph finding 1 and the v3 population verdicts ----
out["pop"] = {f"{x['city']}|{x['method']}": x for x in pop}
out["bboot"] = {x["method"]: x for x in rd("2026-11-22-block-bootstrap-belgrade.csv")}
out["s1s2"] = {f"{x['analysis']}|{x['variant']}|{x['horizon']}|{x['stratum']}|{x['method']}": x for x in rd("2026-11-23-birmingham-s1-s2.csv")}
_cnt = {}
for x in rd("2026-11-23-core-counters.csv"):
    if x["variant"] != "calibrated gamma": continue
    c = _cnt.setdefault(f"{x['city']}|{x['method']}", {"steps": 0, "clipped": 0.0, "inverted": 0})
    c["steps"] += int(float(x["test_steps"])); c["inverted"] += int(float(x["n_inverted"]))
    if x["n_alpha_clipped"]: c["clipped"] += float(x["n_alpha_clipped"])
out["counters"] = _cnt
_tfb = [x for x in rd("2026-09-03-tod-facility-bucket.csv") if x["method"]=="split-CP" and x["dynamic"]=="True" and x["facility_id"]!="8"]
out["worst_cell"] = min(_tfb, key=lambda x: float(x["PICP"]))
assert abs(float(out["worst_cell"]["PICP"]) - float(t3_row("belgrade","split-CP")["worst_facility_bucket_cell"])) < 5e-4
out["T4_meta"]["ratio"] = {f"{x['partition']}|{x['method']}": x["dispersion_ratio_vs_splitCP"] for x in orth}
# ---- revision 57 (agent I): keys for A1, A3, A4, register rows 1.1, 1.2, 4.2, 7.1, 7.2 and the moved-number fixes ----
out["rep"] = {f"{x['city'].lower()}|{x['horizon']}": x for x in rd("2026-09-02-v2-representativeness.csv") if x["city"]=="Belgrade"}
out["rep"].update({f"{x['city'].lower()}|{x['horizon']}": x for x in rd("2026-11-22-v3-representativeness.csv")})
_exc = {c: set(next(x for x in e37 if x["city"]==c)["excluded_facilities"].split(";")) - {"none"} for c in ["belgrade","birmingham"]}
_bm = collections.defaultdict(list)
for city in ["belgrade","birmingham"]:
    for x in rd(f"2026-11-22-core-{city}-v3-gcal-basemodel.csv"):
        if x["dynamic"]=="True" and x["facility_id"] not in _exc[city]: _bm[f"{city}|{x['horizon']}|{x['model']}"].append(float(x["MAE"]))
out["basemodel"] = {k: {"MAE": st.mean(v), "n": len(v)} for k,v in _bm.items()}
out["counters_nfac"] = {}
for x in rd("2026-11-23-core-counters.csv"):
    if x["variant"]=="calibrated gamma": out["counters_nfac"][x["city"]] = max(out["counters_nfac"].get(x["city"],0), int(float(x["n_fac"])))
out["t3"] = {f"{x['city']}|{x['method']}": x for x in t3p}
out["tod_cells"] = {x["method"]: x["cells_below_080"] for x in orth if x["partition"]=="time_of_day"}
out["t6raw"] = t6
assert "CI inside [0.88, 0.92]" in pick("I01","belgrade","split-CP: fraction")["statistic"]
# ---- revision 57 (agent I, A2): EXP-044 facility sample size, read from its promoted path (revision 57b) ----
out["exp044"] = {f"{x['city']}|{x['family']}|{x['item']}|{x['threshold']}|{x['quantity']}|{x['n']}": x for x in rd("2026-11-23-exp044-facility-sample-size.csv")}
(ROOT/"06_manuscript"/"CTR"/"_build").mkdir(exist_ok=True)
json.dump(out, open(ROOT/"06_manuscript"/"CTR"/"_build"/"typeset.json","w"), indent=1, default=str)
print("typeset.json written;", "T6 rows", out["T6_n"])
