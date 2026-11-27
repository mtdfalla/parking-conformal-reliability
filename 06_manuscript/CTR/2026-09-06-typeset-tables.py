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
# revision 60 (disp, T005 / D-053 item 1): the rolling-pool arm RS-CP / RS-CQR (step size 0, same delay and window as ACI).
# Population rows from 2026-11-25-exp045-rolling-inference.csv (P-with-rolling: TOST Holm over the six methods,
# safety pointwise); width and the worst facility recomputed from the per-facility table and asserted against it.
rin = rd("2026-11-25-exp045-rolling-inference.csv")
def rpop(city, m): return next(x for x in rin if x["city"]==city and x["family"]=="P-with-rolling" and x["item"]==m)
_HZ = {"belgrade": "y_t+15min", "birmingham": "y_t+60min"}
_rsf = {c: [y for y in rd(f"2026-11-25-core-{c}-v3-rolling0-per-facility.csv") if y["horizon"]==_HZ[c] and y["level"]=="0.9" and y["dynamic"]=="True" and y["facility_id"] not in _e3x[c]] for c in _HZ}
rs = {}
for c in _HZ:
    for m in ["RS-CP","RS-CQR"]:
        _g = [y for y in _rsf[c] if y["method"]==m]; _p = rpop(c, m); _pc = [float(y["PICP"]) for y in _g]
        assert len(_g)==int(float(_p["n_fac"])) and abs(st.mean(_pc)-float(_p["mean_PICP"]))<1e-12 and abs(st.stdev(_pc)-float(_p["sd_PICP"]))<1e-12 and min(_pc)==float(_p["worst_PICP"]) and abs(st.mean(float(y["Winkler"]) for y in _g)-float(_p["mean_Winkler"]))<1e-9
        _w = [y for y in _g if float(y["PICP"])==min(_pc)]; assert len(_w)==1
        rs[f"{c}|{m}"] = dict(_p, MPIW=repr(st.mean(float(y["MPIW"]) for y in _g)), worst_facility=_w[0]["facility_id"])
    for m in ["split-CP","CQR","ACI","ACQR"]:   # widening the TOST family to six leaves every primary verdict and statistic unchanged
        _p, _q = rpop(c, m), pop_row(c, m)
        assert abs(float(_p["mean_PICP"])-float(_q["mean_PICP"]))<1e-12 and abs(float(_p["t_lower95"])-float(_q["t_lower95"]))<1e-12 and _p["EXACT_holm"]==_q["EXACT_holm"] and _p["SAFE_t_pointwise"]==_q["SAFE_t"]
order = [("split-CP","core"),("CQR","core"),("EnbPI","e3"),("AgACI-style","e3"),("NGBoost","e3"),("NGBoost-conformal","e3"),("RS-CP","rs"),("RS-CQR","rs"),("ACI","core"),("ACQR","core")]
label = {"NGBoost-conformal":"NGBoost + split-CP","AgACI-style":"AgACI-style"}
# revision 60 (disp): the two cities side by side, one row per method (ten rows), so the two added arms cost no page space.
# The block keeps 19 source lines (the content master's line count is fixed: copyedit E2, port G1), so each row is
# split over two lines (Belgrade cells, then Birmingham cells) except the first.
def t2cells(city, m, src):
    if src=="core":
        p = pop_row(city, m); c = core_row(city,m); t=t3_row(city,m)
        picp,sd,mpiw,wk,worst = c["PICP"],c["std"],c["MPIW"],c["Winkler"],t["worst_facility_PICP"]; v = f"{yn(p['EXACT_holm'])} / {yn(p['SAFE_t'])}"
    elif src=="rs":
        p = rs[f"{city}|{m}"]
        picp,sd,mpiw,wk,worst = p["mean_PICP"],p["sd_PICP"],p["MPIW"],p["mean_Winkler"],p["worst_PICP"]; v = f"{yn(p['EXACT_holm'])} / {yn(p['SAFE_t_pointwise'])}"
    else:
        p = pop_row(city, m); e = e3_row(city,m)
        picp,sd,mpiw,wk,worst = e["mean_PICP"],e["sd_PICP"],e["mean_MPIW"],e["mean_Winkler"],e["worst_facility_PICP"]; v = f"{yn(p['EXACT_t'])}$^\\dagger$ / {yn(p['SAFE_t'])}"   # g2 NEW-6: unadjusted exact marked
    return f"{f(picp)} & {f(sd)} & {f(mpiw,1)} & {f(wk,1)} & {f(worst)} & {v}"
rows=[]
for i, (m, src) in enumerate(order):
    a, b = f"{label.get(m,m)} & {t2cells('belgrade', m, src)}", f"& {t2cells('birmingham', m, src)} \\\\"
    if i==0: rows.append(a + " " + b)
    else: rows += [a, b]
assert len(rows)==19
out["T2"] = "\n".join(rows)
out["T2_n"] = len(order)   # s61 FIX2 (contribution count): the interval methods of Table 2
out["T2_meta"] = {
 "bel": {m: core_row("belgrade",m) for m in ["split-CP","CQR","ACI","ACQR"]},
 "bir": {m: core_row("birmingham",m) for m in ["split-CP","CQR","ACI","ACQR"]},
 "bel_e3": {m: e3_row("belgrade",m) for m in ["EnbPI","AgACI-style","NGBoost","NGBoost-conformal"]},
 "bir_e3": {m: e3_row("birmingham",m) for m in ["EnbPI","AgACI-style","NGBoost","NGBoost-conformal"]},
}

# ---------------- T3': two-level inference ----------------
con = rd("2026-09-04-phase4-contrasts.csv")
# revision 60 (disp, T069 / g2 NEW-4): the facility-by-period cells of all four primary methods from 2026-11-25-exp045-tod-cells.csv
# (issue-time periods, as Table 4); split-CP and ACI reproduce the shipped T3prime values.
tcl = rd("2026-11-25-exp045-tod-cells.csv")
def tcell(city, m): return next(x for x in tcl if x["city"]==city and x["method"]==m and x["bucket"]=="SUMMARY")
for m in ["split-CP","ACI"]:
    _t = t3_row("belgrade", m); _c = tcell("belgrade", m)
    assert abs(float(_t["worst_facility_bucket_cell"])-float(_c["PICP"]))<5e-4 and int(float(_t["cells_below_080"]))==int(float(_c["cells_below_080"])) and int(float(_t["n_cells"]))==int(float(_c["n_cells"]))
for m in ["split-CP","CQR","ACI","ACQR"]:   # C51: the summary row equals the minimum and the count over the full cell rows
    _g = [x for x in tcl if x["city"]=="belgrade" and x["method"]==m and x["bucket"]!="SUMMARY"]; _c = tcell("belgrade", m)
    assert len(_g)==int(float(_c["n_cells"])) and min(float(x["PICP"]) for x in _g)==float(_c["PICP"]) and sum(float(x["PICP"])<0.80 for x in _g)==int(float(_c["cells_below_080"]))
# Birmingham: every t+60 forecast is ISSUED in one period (midday), so its cells are its facilities (the table prints dashes and says why)
assert all(int(float(tcell("birmingham", m)["n_cells"]))==int(float(tcell("birmingham", m)["n_facilities"])) for m in ["split-CP","CQR","ACI","ACQR"])
assert {x["bucket"] for x in tcl if x["city"]=="birmingham" and x["bucket"]!="SUMMARY"}=={"midday"}
rows=[]
for city, hz in [("belgrade","t+15 min"),("birmingham","t+60 min")]:
    rows.append(f"\\multicolumn{{9}}{{l}}{{\\emph{{{city.capitalize()}, {hz}}}}} \\\\")   # g7 N1: the subheading spans all nine columns
    for m in ["split-CP","CQR","RS-CP","RS-CQR","ACI","ACQR"]:
        if m.startswith("RS-"):
            p = rs[f"{city}|{m}"]; wf, wid, safe = p["worst_PICP"], p["worst_facility"], p["SAFE_t_pointwise"]; cells = wcell = "--"
        else:
            p=pop_row(city,m); t=t3_row(city,m); wf, wid, safe = t["worst_facility_PICP"], t["worst_facility"], p["SAFE_t"]
            if city=="belgrade":
                c = tcell(city, m); cells = f"{int(float(c['cells_below_080']))} / {int(float(c['n_cells']))}"; wcell = f(c["PICP"])
            else: cells = wcell = "--"
        ph = float(p["tost_p_holm"]); phs = "$<$0.001" if ph<0.001 else f"{ph:.3f}"
        r = f" & {m} & {f(p['mean_PICP'])} [{f(p['t_lo90'])}, {f(p['t_hi90'])}] & {phs} & {yn(p['EXACT_holm'])} / {yn(safe)} & {f(p['sd_PICP'])} & {f(wf)} (\\#{int(float(wid))}) & {wcell} & {cells} \\\\"
        if m.startswith("RS-"): rows[-1] += r   # appended to the CQR line: the line count of the content master is fixed (copyedit E2, port G1)
        else: rows.append(r)
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
# revision 60 (disp, T039 / D-056b): the random-partition column is the 200-draw band of 2026-11-25-exp045-partition-random200-summary.csv
# (median [5th, 95th percentile] of each method's split-CP-relative dispersion over 200 balanced draws), replacing the single draw.
r200 = rd("2026-11-25-exp045-partition-random200-summary.csv")
def r2(m, s): return next(x for x in r200 if x["method"]==m and x["statistic"]==s)
for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]:
    _r = r2(m, "dispersion_ratio_vs_splitCP")
    assert int(float(_r["n_draws"]))==200 and abs(float(_r["single_draw_shipped"])-float(orth_row("random_5",m)["dispersion_ratio_vs_splitCP"]))<5e-3 and abs(float(_r["tod_value"])-float(orth_row("time_of_day",m)["dispersion_ratio_vs_splitCP"]))<5e-3   # the summary stores the ratio at 2 dp
assert all(float(r2(m, "sd_PICP")["tod_pct_below"])==100 for m in ["split-CP","Mondrian-split-CP","ACI"]) and float(r2("ToD-ACI","dispersion_ratio_vs_splitCP")["tod_pct_below"])==100
for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]:
    w=tod_worst(m); o_t=orth_row("time_of_day",m); o_o=orth_row("occupancy_tercile",m); o_d=orth_row("day_of_week",m); _r=r2(m,"dispersion_ratio_vs_splitCP")
    b=[f(tod_pool(m,k)["PICP"]) for k in ["night","am_rush","midday","pm_rush","evening"]]
    rows.append(f"{m} & " + " & ".join(b) + f" & {f(w['PICP'])} & {int(float(o_t['cells_below_080']))} & {f(o_t['dispersion_ratio_vs_splitCP'],2)} & {f(o_o['dispersion_ratio_vs_splitCP'],2)} & {f(o_d['dispersion_ratio_vs_splitCP'],2)} & {f(_r['draws_median'],2)} [{f(_r['draws_p05'],2)}, {f(_r['draws_p95'],2)}] \\\\")
out["T4"] = "\n".join(rows)
out["T4_meta"] = {"V_tercile": orth_row("occupancy_tercile","split-CP")["cramers_v_vs_tod"], "V_dow": orth_row("day_of_week","split-CP")["cramers_v_vs_tod"], "V_rand": orth_row("random_5","split-CP")["cramers_v_vs_tod"],
                  "worst": {m: tod_worst(m) for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]},
                  "pool": {m:{k:tod_pool(m,k)["PICP"] for k in ["night","am_rush","midday","pm_rush","evening"]} for m in ["split-CP","Mondrian-split-CP","ACI","ToD-ACI"]},
                  "n_obs": {k: tod_pool("split-CP",k)["n_obs"] for k in ["night","am_rush","midday","pm_rush","evening"]}}

# ---------------- T5(C): relative-threshold allocation, POINT / INTERVAL / MARGIN ----------------
ra = rd("2026-09-05-rel-alloc-summary.csv")
# revision 60 (disp, T009 / T050 / g4 N4): the same-predictor ladder of 2026-11-25-exp045-allocation-ladder-wide.csv beside POINT and MARGIN:
# on the RF point forecast, the implementable split-CP upper bound (calibration only); on the HGB quantile model, its raw upper
# quantile, split-CQR and ACQR (= INTERVAL). Its POINT, INTERVAL and MARGIN columns reproduce the shipped summary exactly.
lad = rd("2026-11-25-exp045-allocation-ladder-wide.csv")
def lad_row(win, th): return next(y for y in lad if y["window"]==win and y["theta"]==th)
_POL = ["POINT","MARGIN","RF_SPLITCP","CQR_RAW","SPLIT_CQR","INTERVAL"]
for x in ra:
    y = lad_row(x["window"], x["theta"])
    assert all(abs(float(x[k])-float(y[k]))<1e-12 for k in ["bad_POINT","bad_INTERVAL","bad_MARGIN","km_POINT","km_INTERVAL","km_MARGIN"]) and all(int(float(x[k]))==int(float(y[k])) for k in ["facilities_with_event","seeds_sign_holds","seeds_beats_margin"])
    assert all(float(y[f"abst_{p}"])==0 for p in _POL) and int(float(y["n_seeds"]))==20   # "Abstention is zero in every cell"
rows=[]
for win in ["weekend","weekday"]:
    rows.append(f"\\multicolumn{{10}}{{l}}{{\\emph{{{win.capitalize()} window}}}} \\\\")
    for x in [y for y in ra if y["window"]==win]:
        y = lad_row(win, x["theta"])
        b = lambda k: f"{round(600*float(y['bad_'+k]), 6):.2f}"   # revision 58 (G 2-5): per-600 means over 20 seeds are multiples of 0.05, printed exactly (one decimal rounded 1.05 to 1.0)
        assert all(abs(20*600*float(y['bad_'+k]) - round(20*600*float(y['bad_'+k]))) < 1e-6 for k in _POL)
        cell = lambda k: f"{b(k)} ({1000*(float(y['km_'+k])-float(y['km_POINT'])):+.0f})"
        rows.append(f" & {float(x['theta']):.{2 if round(float(x['theta']), 2) == float(x['theta']) else 3}f} & {int(float(x['facilities_with_event']))} & {b('POINT')} & " + " & ".join(cell(k) for k in _POL[1:]) + f" & {int(float(x['seeds_sign_holds']))} / {int(float(x['seeds_beats_margin']))} \\\\")
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
x=pick("C07","belgrade","EnbPI mean PICP");   R.append(("EnbPI outcome release: fixed row chunks $\\to$ calendar-day chunks, matured outcomes only (C07)","early release fed the residual pool before outcomes had matured", f"EnbPI mean PICP, Belgrade, paired run: {f(x['before'])} $\\to$ {f(x['after'])}", "against the claim (EnbPI improves)"))
R.append(("Conformal quantile: \\texttt{np.quantile(\\ldots,`higher')} $\\to$ the $\\lceil(n{+}1)(1{-}\\alpha)\\rceil$ order statistic (C01)","the archived rule over-corrected by one rank at $n_{\\mathrm{cal}}\\approx760$", f"ACI $\\Delta$PICP (alternative $-$ adopted) mean {m_aci:+.4f} (max $|\\Delta|$ {mx_aci:.3f}), ACQR {m_acqr:+.4f} ({mx_acqr:.3f}), split-CP and CQR unchanged ({n_aci} facilities)", "small, negative controls exact"))
xa=pick("1.1-1.3 / 2.1","birmingham","anchors used a later reading"); xt=pick("1.1-1.3 / 2.1","birmingham","targets used a later reading")
assert float(xa["after"])==0 and float(xt["after"])==0   # revision 57 re-key (D-039 item 8): the rebuild removes the exposure
R.append(("Feature build: interpolation of empty half-hour bins $\\to$ last observed bin carried at most one step, observed targets only","an interpolated bin averaged in the next bin's reading, so a stored anchor or target used a later reading", f"Birmingham t+60 min, scored rows using a later reading: anchors {float(xa['before']):.1f}\\% $\\to$ {float(xa['after']):.0f}\\%, targets {float(xt['before']):.1f}\\% $\\to$ {float(xt['after']):.0f}\\%", "exposure removed"))
x1=pick("X08 / D-018","belgrade","ACI across"); x2=pick("X08 / D-018","belgrade","split-CP across"); R.append(("Data quality: retain all facilities $\\to$ exclude facility-windows with $<10$ distinct readings (X08/D-018)","a stuck sensor reporting two values inflated the adaptive methods' dispersion more than split-CP's", f"Belgrade across-facility sd, ACI {f(x1['before'],4)} $\\to$ {f(x1['after'],4)}, split-CP {f(x2['before'],4)} $\\to$ {f(x2['after'],4)}", "mixed (widens the gap to split-CP, narrows it to EnbPI)")); _xr=pick("X08 / D-018","belgrade","RATIO"); assert float(_xr["after"])>float(_xr["before"]) and "EnbPI/ACI ratio weakens" in _xr["direction_vs_our_claim"]
x=pick("EXP-019 / D-016","belgrade","ACI mean PICP"); xb=pick("EXP-019 / D-016","birmingham","ACI mean PICP"); assert float(x["after"])>float(x["before"]) and float(xb["after"])<float(xb["before"])<0.90   # revision 58d (N4): Belgrade moves toward target, Birmingham away
R.append(("ACI step size: fixed $\\gamma=0.05$ $\\to$ selected on a held-out calibration block (EXP-019)","a fixed step is a tuning choice applied to every facility", f"ACI mean PICP, Belgrade: {f(x['before'])} $\\to$ {f(x['after'])}, Birmingham: {f(xb['before'])} $\\to$ {f(xb['after'])}", "mixed (toward target on Belgrade, away on Birmingham)"))
x=pick("I04","belgrade","ACI vs split-CP"); _i04=sorted(float(y["ratio_after_over_before"]) for y in t6 if y["audit_issue"]=="I04"); assert len(_i04)==4 and sum(r>1 for r in _i04)==3; out["i04_ratio"]=_i04
_i04s=", ".join(f"{r:.1f}" if r<1 else f"{r:.0f}" for r in _i04)
R.append(("Unit of inference: pooled fold-facility rows $\\to$ facility-clustered (I04)","each facility appears in every fold, and pooling treats repeats as independent", f"$|$gap$|$ p, clustered over pooled, four contrasts: {_i04s} times", "against the claim in three of four (clustered p larger)"))
x1=pick("I01","belgrade","split-CP: fraction"); x2=pick("I01","belgrade","ACI: fraction"); R.append(("Certification: `facility CI contains 0.90' $\\to$ population equivalence + safety bound (I01)","failing to reject equality is not evidence of it, and wider intervals pass more easily", f"facilities certified, Belgrade (CI contains 0.90 $\\to$ CI inside $[0.88, 0.92]$): split-CP {pct(x1['before'])} $\\to$ {pct(x1['after'])}, ACI {pct(x2['before'])} $\\to$ {pct(x2['after'])}", "changes the certification outcome"))
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
out["T6_dir"] = [d for a,b,c,d in R]   # s61 FIX2 (retest new-4): last-column direction labels, read by the V-G count

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
ta = rd("2026-11-25-x08-trust-abstain-excl.csv")   # revision 60 (disp, T024): the boundary-maturity replay (EXP-045 A4)
# revision 58b (F-30 class): commit rate, committed coverage and committed MPIW stored at 3, 4 and 2 dp sit on rounding ties (width rule 0.9 MPIW 10.55); read the full-precision value of the same quantity from 2026-09-03-trust-abstain-per-facility.csv
_tap = [y for y in rd("2026-11-25-trust-abstain-per-facility.csv") if y["dynamic"]=="True" and y["facility_id"] not in _e3x["belgrade"]]
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
sp = rd("2026-11-25-spatial-statistics.csv")   # revision 60 (disp, T006): canonical pipeline (EXP-045 A3)
out["spatial"] = {x["statistic"] if x["statistic"]!="spearman_rho_residcorr_vs_distance_naive" else f"{x['statistic']}|{x['script']}": x for x in sp}
# ---- revision 49 (D-030): the spatial leg recomputed on the paper's evaluation base (20 facilities).
# The published rows stay in `spatial` as the record of what the live scripts produce; `spatial_excl` is what
# the manuscript now reads, and `spatial_pub21` is the negative control that reproduces the published values.
spx = rd("2026-11-25-spatial-statistics-exclusion-base.csv")   # revision 60 (disp, T006)
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
# ---- revision 60 (disp): keys for the rolling arm, Holm-adjusted safety, the two-city block bootstrap, the cells, the random bands, the ladder ----
import re as _re
from scipy import stats as _ss
out["disp_rs"] = rs   # RS-CP / RS-CQR at the headline settings, keyed city|method: the P-with-rolling row + MPIW + worst_facility
out["disp_rollinf"] = {f"{x['city']}|{x['family']}|{x['item']}": x for x in rin}   # every row of 2026-11-25-exp045-rolling-inference.csv
# T003 / g8 N1: the safety leg Holm-adjusted over the four primary methods (prespecified family P), from the same t statistics
_sh = {}
for c in ["belgrade","birmingham"]:
    _P = [pop_row(c, m) for m in ["split-CP","CQR","ACI","ACQR"]]
    for x in _P:
        _n = int(x["n_fac"]); assert abs(float(x["mean_PICP"])-_ss.t.ppf(0.95, _n-1)*float(x["se"])-float(x["t_lower95"])) < 1e-12
    _pr = [float(_ss.t.sf((float(x["mean_PICP"])-0.88)/float(x["se"]), int(x["n_fac"])-1)) for x in _P]
    assert all((p <= 0.05)==(x["SAFE_t"]=="True") for p, x in zip(_pr, _P))   # the pointwise verdict is the raw one-sided test
    _o = sorted(range(4), key=lambda i: _pr[i]); _ad = [0.0]*4; _run = 0.0
    for k, i in enumerate(_o): _run = max(_run, min(1.0, (4-k)*_pr[i])); _ad[i] = _run
    for x, pr, pa in zip(_P, _pr, _ad): _sh[f"{c}|{x['method']}"] = {"p_raw": pr, "p_holm": pa, "SAFE_holm": pa <= 0.05, "SAFE_t": x["SAFE_t"]=="True"}
assert all(_sh[f"belgrade|{m}"]["SAFE_holm"] for m in ["split-CP","CQR","ACI","ACQR"]) and not any(_sh[f"birmingham|{m}"]["SAFE_holm"] for m in ["split-CP","CQR","ACI","ACQR"])
assert [m for m in ["split-CP","CQR","ACI","ACQR"] if _sh[f"birmingham|{m}"]["SAFE_t"]] == ["CQR","ACQR"]
out["disp_safe_holm"] = _sh
# T002 / g2 NEW-1, NEW-2: the synchronous time-block bootstrap, both cities, six methods (EXP-045 A7)
_bb = rd("2026-11-25-block-bootstrap-both-cities.csv")
assert len(_bb)==12 and not any(x["safe_boot"]=="True" or x["exact_boot"]=="True" for x in _bb)
assert all(abs(float(x["boot_lo"])-float(out["bboot"][x["method"]]["boot_lo"]))<1e-12 for x in _bb if x["city"]=="belgrade" and x["method"] in out["bboot"])
out["disp_bboot2"] = {f"{x['city']}|{x['method']}": x for x in _bb}
out["disp_tcells"] = {f"{x['city']}|{x['method']}": x for x in tcl if x["bucket"]=="SUMMARY"}   # T069
out["disp_r200"] = {f"{x['method']}|{x['statistic']}": x for x in r200}   # T039 bands and percentiles
out["disp_ladder"] = {f"{x['window']}|{x['theta']}": x for x in lad}   # T009 / T050 ladder, every column of the wide table
# T029: the time-of-day periods (issue-time hours) read from the code that buckets them, not typed
_bk = _re.findall(r'\("(\w+)", (\d+), (\d+)\)', (ROOT/"03_code"/"src"/"conformal"/"2026-09-03-tod-conditional.py").read_text())
assert [b[0] for b in _bk] == ["night","am_rush","midday","pm_rush","evening"] == [k for k in out["T4_meta"]["n_obs"]]
out["disp_buckets"] = {b[0]: [int(b[1]), int(b[2])] for b in _bk}
# ---- revision 60 (data): Section III exposure, roster and representativeness facts; IV-D release lag; IV-H Holm on the safety legs ----
import re as _re
import pandas as _pd
from scipy import stats as _sst
_PR = ROOT / "01_data" / "processed"
_bv = _pd.read_parquet(_PR / "belgrade_features_v2.parquet")
_brep = json.load(open(_PR / "belgrade_features_v2_report.json"))
assert len(_bv) == int(_brep["rows"]) == int(float(out["rep"]["belgrade|t+30min"]["rows_v2_total"]))
_btr = _bv[_bv["split"] == "train"].groupby("facility_id")["occupancy"].std()
_bdyn = sorted(int(k) for k, v in _btr.items() if v >= 5.0)             # the dynamic rule: train sd at least five vehicles
_bnon = sorted(int(k) for k, v in _btr.items() if not v >= 5.0)
_bev = [k for k in _bdyn if str(k) not in _exc["belgrade"]]
_blow = sorted(int(k) for k in _exc["belgrade"] if int(k) in _bdyn)    # dynamic but screened out (facility 8)
_g = _bv.groupby("facility_id")["occupancy"]
_cv = (_g.std() / _g.mean()); _cap = _g.max()
_te30 = _bv[(_bv["split"] == "test") & _bv["use_30"] & _bv["facility_id"].isin(_bev)]
_gc30 = [x for x in rd("2026-11-22-core-belgrade-v3-gcal-per-facility.csv") if x["horizon"] == "y_t+30min" and float(x["level"]) == 0.90
         and x["method"] == "split-CP" and x["dynamic"] == "True" and x["facility_id"] not in _exc["belgrade"]]
assert len(_gc30) == len(_bev) and len(_te30) == sum(int(x["n_test"]) for x in _gc30)   # the evaluated t+30 base
assert int(_bv["occ_interpolated"].sum()) == 0                                           # no retained anchor is filled (the builder guard asserts every input)
_k30 = int(_te30["target_interpolated_30"].sum())
_blg = _pd.read_parquet(_PR / "belgrade_long.parquet")   # s61 FIX3 (T001): the later reading behind each interpolated target is observed by the time
for _f, _s in _bv[(_bv["split"] == "test") & _bv["use_30"] & _bv["facility_id"].isin(_bev)].groupby("facility_id"):   # its score is released (stream row i + 6)
    _s = _s.sort_values("timestamp").reset_index(drop=True)
    _ob = _blg[_blg["facility_id"] == _f].set_index("timestamp").sort_index()["occupancy"].resample("5min").mean().dropna().index
    for _j in _s.index[_s["target_interpolated_30"]]:
        assert _j + 6 >= len(_s) or _s.at[_j + 6, "timestamp"] >= _ob[_ob > _s.at[_j, "target_ts_30"]].min()
_bl = _pd.read_parquet(_PR / "birmingham_long.parquet")
_minrec = int(_re.search(r"^MIN_RECORDS = (\d+)", (ROOT / "03_code" / "src" / "features" / "2026-11-22-build_features_birmingham_v3.py").read_text(encoding="utf_8"), _re.M).group(1))
_brec = _bl.groupby("facility_id").size()
_bsparse = sorted(int(k) for k, v in _brec.items() if v < _minrec)
_bkept = sorted(int(k) for k in _pd.read_parquet(_PR / "birmingham_features_v3.parquet")["facility_id"].unique())
assert len(_bsparse) == 2 and not set(_bsparse) & set(_bkept) and len(_bkept) + len(_bsparse) == _brec.size
out["data_bel"] = {"rows": len(_bv), "dyn": _bdyn, "nondyn": _bnon, "eval": _bev, "lowinfo": _blow, "n_eval30": len(_te30), "k_interp30": _k30,
                   "pct_interp30": 100 * _k30 / len(_te30), "cv_min": float(_cv[_bev].min()), "cv_max": float(_cv[_bev].max()),
                   "cv_max_modeled": float(_cv[_bdyn].max()), "cap_min": float(_cap[_bev].min()), "cap_max": float(_cap[_bev].max()),
                   "n_small": int((_cap[_bev] < 100).sum()), "n_mid": int(((_cap[_bev] >= 100) & (_cap[_bev] < 400)).sum()), "n_large": int((_cap[_bev] >= 400).sum())}
assert out["data_bel"]["cv_max_modeled"] > out["data_bel"]["cv_max"]    # g5 NEW-1: the modeled maximum is the screened facility's
_rex = {(x["horizon"], x["group"]): x for x in rd("2026-11-25-exp045-retained-excluded.csv") if x["scope"] == "paper_base" and x["split"] == "test"}
_rws = _pd.read_csv(T / "2026-11-25-core-birmingham-v3-rolling0-rows-L90.csv", usecols=["timestamp"], parse_dates=["timestamp"])["timestamp"]
_tod = sorted(set(_rws.dt.strftime("%H:%M")))
_hrs = [x for x in rd("2026-11-25-exp045-rows-by-hour.csv") if x["city"] == "birmingham" and x["scope"] == "paper_base" and int(x["n_rows"]) > 0]
assert min(int(x["hour"]) for x in _hrs) == int(_tod[0][:2]) and max(int(x["hour"]) for x in _hrs) == int(_tod[-1][:2])
out["data_bir"] = {"minrec": _minrec, "sparse": _bsparse, "tod_first": _tod[0], "tod_last": _tod[-1],
                   "excl_share": {h: float(_rex[(h, "excluded")]["share_of_candidates"]) for h in ["y_t+30min", "y_t+60min", "y_t+90min"]},
                   "carried": {f"{h}|{g}": float(_rex[(h, g)]["carried_anchor_share"]) for h in ["y_t+30min", "y_t+60min", "y_t+90min"] for g in ["retained", "excluded"]}}
_c = out["data_bir"]["carried"]   # revision 59 correction (3): imbalance at t+60 only, reversed at t+90, none at t+30
assert _c["y_t+60min|excluded"] > _c["y_t+60min|retained"] and _c["y_t+90min|excluded"] < _c["y_t+90min|retained"] and _c["y_t+30min|excluded"] < _c["y_t+30min|retained"]
out["data_lag"] = {f"{x['city']}|{x['horizon']}": {k: float(x[k]) for k in ["share_eq_h", "share_gt_h", "share_gt_12h", "share_lt_h"]}
                   for x in rd("2026-11-25-exp045-release-lag.csv") if x["scope"] == "paper_base"}
assert all(v["share_lt_h"] == 0 for v in out["data_lag"].values())   # feedback is never released early
_sh = {}
for _city in ["belgrade", "birmingham"]:
    _rows = [x for x in pop if x["city"] == _city and x["family"] == "P-primary"]
    assert [x["method"] for x in _rows] == ["split-CP", "CQR", "ACI", "ACQR"]
    _p = [float(_sst.t.sf((float(x["mean_PICP"]) - 0.88) / float(x["se"]), int(x["n_fac"]) - 1)) for x in _rows]
    _o = sorted(range(len(_p)), key=lambda i: _p[i]); _adj = [0.0] * len(_p); _run = 0.0
    for r, i in enumerate(_o):
        _run = max(_run, min(1.0, (len(_p) - r) * _p[i])); _adj[i] = _run
    for x, pr, pa in zip(_rows, _p, _adj):
        assert (pr < 0.05) == (x["SAFE_t"] == "True")    # the one-sided t bound at 0.88 and the raw p agree
        _sh[f"{_city}|{x['method']}"] = {"p_raw": pr, "p_holm": pa, "SAFE_t": x["SAFE_t"], "SAFE_holm": pa < 0.05}
out["data_safety_holm"] = _sh
assert all(_sh[f"belgrade|{m}"]["SAFE_holm"] for m in ["split-CP", "CQR", "ACI", "ACQR"])
assert [m for m in ["split-CP", "CQR", "ACI", "ACQR"] if _sh[f"birmingham|{m}"]["SAFE_t"] == "True" and not _sh[f"birmingham|{m}"]["SAFE_holm"]] == ["CQR", "ACQR"]
# ---- revision 60 (front): numbers for the abstract, contribution paragraph and conclusion (T005 / D-056a, T009, T012) ----
_fri = rd("2026-11-25-exp045-rolling-inference.csv")
def _frc(c, it): return next(x for x in _fri if x["city"]==c and x["section"]=="contrast" and x["family"]=="R-dispersion" and x["item"]==it)
def _frp(c, m):  return next(x for x in _fri if x["city"]==c and x["section"]=="population" and x["item"]==m)
_FRC = ("ACI vs RS-CP", "ACQR vs RS-CQR"); _FRT = (("split-CP","RS-CP","ACI"), ("CQR","RS-CQR","ACQR"))
_frs = {f"{x['city']}|{x['item']}": float(x["value"]) for x in _fri if x["section"]=="decomposition" and x["family"]=="sd share"}
for _c in ("belgrade","birmingham"):           # the shipped share equals (sd static - sd rolling) / (sd static - sd adaptive)
    for _s, _r, _a in _FRT:
        _v = [float(_frp(_c, m)["sd_PICP"]) for m in (_s, _r, _a)]
        assert abs(_frs[f"{_c}|{_s} > {_r} > {_a}"] - (_v[0]-_v[1])/(_v[0]-_v[2])) < 1e-9
_frl = rd("2026-11-25-exp045-allocation-ladder.csv")
def _frv(pol, comp, met): return float(next(x for x in _frl if x["window"]=="weekend" and x["day"]=="all" and abs(float(x["theta"])-0.9)<1e-9 and x["policy"]==pol and x["comparator"]==comp and x["metric"]==met)["value"])
_fr5 = rd("2026-11-25-orthogonal-5b-summary.csv")
out["front"] = {
 "holm_bel": [float(_frc("belgrade", i)["wilcoxon_p_holm"]) for i in _FRC],
 "holm_bir": [float(_frc("birmingham", i)["wilcoxon_p_holm"]) for i in _FRC],
 "share": sorted(_frs.values()),
 "raw_share": _frv("CQR-RAW", "POINT", "share_of_point_to_interval_reduction"),
 "tod_folds": [int(float(next(x for x in _fr5 if x["arm"]=="A_folds" and x["fold"]==k and x["partition"]=="time_of_day" and x["method"]=="ToD-ACI")["cells_below_080"])) for k in ("F1","F2","F3")],
}
_FR = out["front"]
assert all(_frc("belgrade", i)["significant_holm_005"]=="True" and float(_frc("belgrade", i)["mean_diff"]) < 0 for i in _FRC)   # "adapting the level adds a Holm-significant gain on Belgrade"
assert not any(_frc("birmingham", i)["significant_holm_005"]=="True" for i in _FRC)                                            # "none detected on Birmingham"
assert len(set(f"{p:.3f}" for p in _FR["holm_bel"])) == 1          # one printed p serves both Belgrade contrasts
assert len(_FR["share"]) == 4 and min(_FR["share"]) > 0.5          # "most of the narrowing comes from recalibrating on matured scores"
assert 0.5 < _FR["raw_share"] < 1                                    # "most of the cut already comes from the raw quantile-regression bound"
assert abs(_frv("INTERVAL", "POINT", "rel_reduction") - float(next(v for v in out["T5C_meta"].values() if v["window"]=="weekend" and abs(float(v["theta"])-0.9)<1e-9)["rel_reduction_vs_point"])) < 1e-9   # the ladder is the Table VI panel
assert int(float(out["tod_cells"]["ToD-ACI"])) == 0 and float(out["T4_meta"]["worst"]["ToD-ACI"]["PICP"]) > 0.80   # "every cell above 0.80 in the primary test window"
assert max(_FR["tod_folds"]) > 0                                     # the primary-window claim does not hold in every fold, so the text scopes it
assert abs(float(out['T2_meta']['bir_e3']['NGBoost-conformal']['mean_PICP']) - 0.9) < 0.005   # "restored its mean coverage" (Birmingham only: Belgrade M02 fails both verdicts)
# ---- revision 60 (res): Section V keys. T005 rolling arm, T002 block bootstrap, T003 Holm safety, T069 cells, T012 fold cells, T039 random partitions, T006 spatial, T017 all-facility, NEW-8 worst-facility interval, T038 variance benchmark, T086 normalised Winkler ----
import math as _rm
from scipy import stats as _rs
out["res_roll"] = {f"{x['city']}|{x['family']}|{x['item']}": x for x in rd("2026-11-25-exp045-rolling-inference.csv")}
out["res_bb"] = {f"{x['city']}|{x['method']}": x for x in rd("2026-11-25-block-bootstrap-both-cities.csv")}
_rsh = {}
for _c in ["belgrade","birmingham"]:
    _pp = {m: pop_row(_c, m) for m in ["split-CP","CQR","ACI","ACQR"]}
    _raw = {m: float(_rs.t.sf((float(x["mean_PICP"])-0.88)/float(x["se"]), int(x["n_fac"])-1)) for m, x in _pp.items()}
    for m, x in _pp.items():   # the pointwise safety leg reproduces the stored verdict
        assert (_raw[m] <= 0.05) == (x["SAFE_t"]=="True"), (_c, m, _raw[m])
    _ord = sorted(_raw, key=_raw.get); _run = 0.0
    for i, m in enumerate(_ord):
        _run = max(_run, min(1.0, (len(_ord)-i)*_raw[m])); _rsh[f"{_c}|{m}"] = {"p_raw": _raw[m], "p_holm": _run}
out["res_safe_holm"] = _rsh
# s61 FIX2 (retest, T003 carry): pointwise safety Holm-adjusted over the six methods of the rolling-arm family (the TOST family of Table 3 for RS-CP and RS-CQR)
_rsh6 = {}
for _c in ["belgrade","birmingham"]:
    _q = {x["item"]: x for x in out["res_roll"].values() if x["city"]==_c and x["family"]=="P-with-rolling"}; assert len(_q) == 6
    _raw6 = {}
    for m, x in _q.items():
        _n = int(float(x["n_fac"])); _se = (float(x["mean_PICP"])-float(x["t_lower95"]))/float(_rs.t.ppf(0.95, _n-1))
        _raw6[m] = float(_rs.t.sf((float(x["mean_PICP"])-0.88)/_se, _n-1)); assert (_raw6[m] <= 0.05) == (x["SAFE_t_pointwise"]=="True"), (_c, m)
    _o6 = sorted(_raw6, key=_raw6.get); _run = 0.0
    for i, m in enumerate(_o6):
        _run = max(_run, min(1.0, (len(_o6)-i)*_raw6[m])); _rsh6[f"{_c}|{m}"] = {"p_raw": _raw6[m], "p_holm": _run}
assert abs(_rsh6["birmingham|RS-CQR"]["p_holm"] - float(out["res_roll"]["birmingham|P-with-rolling|RS-CQR"]["tost_p_holm"])) < 1e-9   # the lower one-sided leg is the binding TOST leg
out["res_safe_holm6"] = _rsh6
out["res_cells"] = {f"{x['city']}|{x['method']}": x for x in rd("2026-11-25-exp045-tod-cells.csv") if x["bucket"]=="SUMMARY"}
out["res_fold_cells"] = {f"{x['fold']}|{x['method']}": x for x in rd("2026-11-25-orthogonal-5b-summary.csv") if x["arm"]=="A_folds" and x["partition"]=="time_of_day"}
out["res_part"] = {f"{x['method']}|{x['statistic']}": x for x in rd("2026-11-25-exp045-partition-random200-summary.csv")}
out["res_spx"] = {x["statistic"]: x for x in rd("2026-11-25-spatial-statistics-exclusion-base.csv") if x["population"]=="exclusion_base"}
_evb = {str(int(float(y["facility_id"]))) for y in rd("2026-11-22-core-belgrade-v3-gcal-per-facility.csv") if y["dynamic"]=="True" and y["facility_id"] not in _e3x["belgrade"]}
out["res_spx_missing"] = sorted(_evb - set(out["res_spx"]["morans_I_mean_aci_halfwidth"]["facility_ids"].split(";")), key=int)   # fix round (res-40): the evaluated facility without coordinates
assert len(out["res_spx_missing"]) == len(_evb) - int(out["res_spx"]["morans_I_mean_aci_halfwidth"]["n_facilities"]) == 1
# T017: the all-facility Belgrade roster (facility 8 retained), re-aggregated from the per-facility table and checked against the control CSV
_ctl = {f"{x['city']}|{x['method']}": x for x in rd("2026-09-04-x08-core-headline-control.csv")}
_pf8 = [y for y in rd("2026-11-22-core-belgrade-v3-gcal-per-facility.csv") if y["horizon"]=="y_t+15min" and y["level"]=="0.9" and y["dynamic"]=="True"]
_af = {}
for m in ["split-CP","CQR","ACI","ACQR"]:
    _v = [float(y["PICP"]) for y in _pf8 if y["method"]==m]; _n = len(_v); _mu = st.mean(_v); _sd = st.stdev(_v); _se = _sd/_rm.sqrt(_n)
    assert _n == int(_ctl[f"belgrade|{m}"]["n"]) and abs(_mu-float(_ctl[f"belgrade|{m}"]["PICP"])) < 1e-9 and abs(_sd-float(_ctl[f"belgrade|{m}"]["std"])) < 1e-9
    _af[m] = {"n": _n, "mean": _mu, "sd": _sd, "t_lower95": _mu-_rs.t.ppf(0.95, _n-1)*_se,
              "tost_p": max(_rs.t.sf((_mu-0.88)/_se, _n-1), _rs.t.sf((0.92-_mu)/_se, _n-1))}
_ord = sorted(_af, key=lambda m: _af[m]["tost_p"]); _run = 0.0
for i, m in enumerate(_ord):
    _run = max(_run, min(1.0, (len(_ord)-i)*_af[m]["tost_p"])); _af[m]["tost_p_holm"] = _run
out["res_allfac"] = _af
# NEW-8: the Birmingham split-CP worst facility, its forecast count and exact (Clopper-Pearson) 95% interval
_bw = t3_row("birmingham","split-CP"); _bpf = [y for y in rd("2026-11-22-core-birmingham-v3-gcal-per-facility.csv") if y["horizon"]=="y_t+60min" and y["level"]=="0.9" and y["method"]=="split-CP" and y["dynamic"]=="True" and str(int(float(y["facility_id"])))==str(int(float(_bw["worst_facility"])))]
assert len(_bpf)==1 and abs(float(_bpf[0]["PICP"])-float(_bw["worst_facility_PICP"])) < 5e-5
_nt = int(_bpf[0]["n_test"]); _k = round(float(_bpf[0]["PICP"])*_nt); assert abs(_k/_nt-float(_bpf[0]["PICP"])) < 1e-12
out["res_bir_worst"] = {"k": _k, "n": _nt, "lo": float(_rs.beta.ppf(0.025, _k, _nt-_k+1)), "hi": float(_rs.beta.ppf(0.975, _k+1, _nt-_k))}
# T038: the spread of split-CP facility coverage that exchangeable scores would produce at Belgrade's calibration and test sizes
_bsp = [y for y in _pf8 if y["method"]=="split-CP" and y["facility_id"] not in _e3x["belgrade"]]
assert len({y["n_cal"] for y in _bsp})==1 and len({y["n_test"] for y in _bsp})==1
_nc = int(_bsp[0]["n_cal"]); _nte = int(_bsp[0]["n_test"]); _ka = _rm.ceil((_nc+1)*0.9); _a, _b = _ka, _nc+1-_ka
_vb = _a*_b/((_a+_b)**2*(_a+_b+1)); _pm = _a/(_a+_b); _vt = (_pm*(1-_pm) - _vb)/_nte
out["res_var"] = {"n_cal": _nc, "n_test": _nte, "sd_beta": _rm.sqrt(_vb), "sd_test": _rm.sqrt(_vt), "sd_total": _rm.sqrt(_vb+_vt)}
out["res_nwk"] = {f"{x['city']}|{x['method']}": x for x in rd("2026-11-25-exp045-normalised-winkler.csv")}
# ---- revision 60 (alloc): Section VI-A ladder, capacity, seeds, section 0, selection, VI-C and VII checks (EXP-045) ----
_alw = rd("2026-11-25-exp045-allocation-ladder-wide.csv")
_ars = rd("2026-09-05-rel-alloc-summary.csv")
for _x in _alw:   # the three shipped policies are reproduced exactly by the ladder run
    _y = next(z for z in _ars if z["window"]==_x["window"] and float(z["theta"])==float(_x["theta"]))
    assert all(abs(float(_x[k])-float(_y[k])) < 1e-12 for k in ["bad_POINT","bad_INTERVAL","bad_MARGIN","km_POINT","km_INTERVAL","km_MARGIN","seeds_sign_holds","seeds_beats_margin"]), _x["theta"]
out["alloc_lad"] = {f"{x['window']}|{float(x['theta']):g}": x for x in _alw}
_all = rd("2026-11-25-exp045-allocation-ladder.csv")
_av = lambda w,d,t,p,c,m: float(next(x for x in _all if x["window"]==w and x["day"]==d and float(x["theta"])==t and x["policy"]==p and x["comparator"]==c and x["metric"]==m)["value"])
_wd = sorted({x["day"] for x in _all if x["window"]=="weekend" and x["day"]!="all"})
out["alloc_sel"] = {"miss_assigned_INTERVAL": _av("weekend","all",0.9,"INTERVAL","","upper_miss_assigned_mean"),
                    "miss_all_INTERVAL": _av("weekend","all",0.9,"INTERVAL","","upper_miss_all_slots"),
                    "miss_all_CQR_RAW": _av("weekend","all",0.9,"CQR-RAW","","upper_miss_all_slots"),
                    "withdraw_INTERVAL": _av("weekend","all",0.9,"INTERVAL","","withdraw_rate"),
                    "withdraw_MARGIN": _av("weekend","all",0.9,"MARGIN","","withdraw_rate"),
                    "days_seeds": [_av("weekend",d,0.9,"INTERVAL","POINT","seeds_policy_better") for d in _wd]}
_ase = [x for x in rd("2026-11-25-exp045-allocation-seeds.csv") if x["window"]=="weekend" and x["day"]=="all" and float(x["theta"])==0.9]
_pd = [600*(float(p["bad_assignments_per_request"])-float(i["bad_assignments_per_request"])) for p in _ase if p["policy"]=="POINT" for i in _ase if i["policy"]=="INTERVAL" and i["seed"]==p["seed"]]
assert len(_pd)==20 and abs(st.stdev(_pd)/len(_pd)**0.5 - float(next(v for k, v in out["alloc_lad"].items() if k.startswith("weekend|") and float(v["theta"]) == 0.9)["d_point_minus_interval_per600_se"])) < 1e-9
_acp = rd("2026-11-25-exp045-allocation-capacity.csv")
_sp = max(float(x["spread"]) for x in _acp)
_cr = [x for x in _acp if float(x["spread"])==_sp and x["policy"]=="INTERVAL" and x["comparator"]=="POINT"]
out["alloc_cap"] = {"spread": _sp, "draws": len({x["draw"] for x in _cr}),
                    "min_rel": min(float(x["value"]) for x in _cr if x["metric"]=="rel_reduction"),
                    "min_seeds": min(float(x["value"]) for x in _cr if x["metric"]=="seeds_policy_better")}
_s0 = rd("2026-11-25-exp045-rel-alloc-section0.csv")
out["alloc_s0"] = {f"{x['window']}|{float(x['theta']):g}": x for x in _s0}
_bb2 = rd("2026-11-25-block-bootstrap-both-cities.csv")
out["alloc_bb2"] = {"n_rows": len(_bb2), "none_safe_or_exact": all(x["safe_boot"]=="False" and x["exact_boot"]=="False" for x in _bb2), "cities": sorted({x["city"] for x in _bb2})}
_ri = rd("2026-11-25-exp045-rolling-inference.csv")
out["alloc_roll"] = {"sd_share_min": min(float(x["value"]) for x in _ri if x["section"]=="decomposition" and x["family"]=="sd share"),
                     "bel_sig": [x["significant_holm_005"] for x in _ri if x["city"]=="belgrade" and x["family"]=="R-dispersion"],
                     "bir_sig": [x["significant_holm_005"] for x in _ri if x["city"]=="birmingham" and x["family"]=="R-dispersion"]}
out["alloc_folds_tod"] = [int(x["cells_below_080"]) for x in rd("2026-11-25-orthogonal-5b-summary.csv") if x["arm"]=="A_folds" and x["partition"]=="time_of_day" and x["method"]=="ToD-ACI"]
# ---- revision 60 (esm): keys for the ESM corrections and the new ESM tables S10 to S12 (T002, T003, T007, T010, T011, T012,
# T017, T021, T022, T024, T025, T026, T028, T029, T030, T031, T041, T044, T047, T049, T053, T067, T070, T086, T090, g2 NEW-8,
# g3 NEW-1, NEW-2, NEW-5, g5 NEW-5). Every printed number is read here from 05_results/tables/, a processed-data report or
# the code that sets it, never typed into the ESM generator ----
import ast as _ast, math as _math, re as _re, datetime as _dt
from scipy import stats as _stats
_SRC = ROOT / "03_code" / "src"
def _lit(node):
    try: return _ast.literal_eval(node)
    except ValueError:   # a plain arithmetic constant such as 10/18
        assert isinstance(node, _ast.BinOp) and isinstance(node.op, _ast.Div); return _lit(node.left) / _lit(node.right)
def _consts(path, names):
    """Module-level literal assignments of a code file (the settings the ESM states), read without importing it."""
    _v = {}
    for _n in _ast.parse((_SRC / path).read_text(encoding="utf-8")).body:
        if isinstance(_n, _ast.Assign):
            _tg = _n.targets[0]
            if isinstance(_tg, _ast.Name) and _tg.id in names: _v[_tg.id] = _lit(_n.value)
            elif isinstance(_tg, _ast.Tuple) and isinstance(_n.value, _ast.Tuple):
                for _a, _b in zip(_tg.elts, _n.value.elts):
                    if isinstance(_a, _ast.Name) and _a.id in names: _v[_a.id] = _lit(_b)
    assert set(_v) == set(names), (path, set(names) - set(_v)); return _v
_core = (_SRC / "conformal" / "core.py").read_text(encoding="utf-8")
_cfg = {"gamma_grid": list(_consts("conformal/core.py", ["GAMMA_GRID"])["GAMMA_GRID"])}
_cfg["gamma_fallback"] = _cfg["gamma_grid"][len(_cfg["gamma_grid"]) // 2]
assert "return grid[len(grid) // 2]" in _core and "if cut < 30 or (n - cut) < max(50, 10 * horizon):" in _core and "split_frac=0.5" in _core
assert "gap = horizon - 1" in _core and "pool_a = cal_scores[:cut - gap]" in _core and "ties broken by lower Winkler score" in _core
assert "min_group: int = 50" in _core and "the fallback pool is the own scores plus the OTHER groups' scores, each once" in _core
assert "return min(int(math.ceil((n + 1) * (1.0 - alpha))), n)" in _core and "mid = 0.5 * (qlo[cross] + qhi[cross])" in _core
assert "Both ends are set to their midpoint" in _core
_bv = _consts("features/2026-09-02-build_features_v2.py", ["LAGS", "ROLL_WINDOWS", "STEP_MIN"])
_bb = _consts("features/2026-11-22-build_features_birmingham_v3.py", ["LAGS", "ROLL", "MIN_RECORDS", "TRAIN_FRAC", "CALIB_FRAC", "STEP"])
_cfg["lags_bel"] = [L * _bv["STEP_MIN"] for L in _bv["LAGS"]]; _cfg["lags_bir"] = [L * _bb["STEP"] for L in _bb["LAGS"]]
_cfg["roll_bel"] = [W * _bv["STEP_MIN"] for W in _bv["ROLL_WINDOWS"]]; _cfg["roll_bir"] = [W * _bb["STEP"] for W in _bb["ROLL"]]
_cfg["min_records"] = _bb["MIN_RECORDS"]; _cfg["step_bel"] = _bv["STEP_MIN"]; _cfg["step_bir"] = _bb["STEP"]; _cfg["h15_steps"] = 15 // _bv["STEP_MIN"]
_rc = _consts("conformal/2026-11-22-run-core-methods.py", ["SEED", "DYN"]); _cfg["seed_core"] = _rc["SEED"]; _cfg["dyn_sd"] = _rc["DYN"]
_pt = _consts("conformal/2026-11-25-orthogonal-partition-check.py", ["N_DRAWS", "SEED_PART"]); _cfg["n_part"] = _pt["N_DRAWS"]; _cfg["seed_part"] = _pt["SEED_PART"]
_rj = json.load(open(ROOT / "01_data" / "processed" / "birmingham_features_v3_report.json"))
_t0, _t1 = _dt.datetime.fromisoformat(_rj["time_min"]), _dt.datetime.fromisoformat(_rj["time_max"])
_cut = lambda fr: _t0 + (_t1 - _t0) * fr
_hm = lambda t: f"{t.strftime('%b')} {t.day}, {t.strftime('%H:%M')}"
_cfg["bir_cuts"] = [_hm(_cut(_bb["TRAIN_FRAC"])), _hm(_cut(_bb["TRAIN_FRAC"] + _bb["CALIB_FRAC"]))]
_cfg["bir_span"] = [_hm(_t0), _hm(_t1)]; _cfg["bir_excluded"] = _rj["excluded"]
_tod = _consts("conformal/2026-09-03-tod-conditional.py", ["BUCKETS"])["BUCKETS"]
_cfg["buckets"] = [[b[0].replace("_", " ").replace("am rush", "AM rush").replace("pm rush", "PM rush"), b[1], b[2]] for b in _tod]
_va = _consts("conformal/2026-11-25-allocation-vignette.py", ["SEED_FIT", "HMIN", "HOT", "SIG", "BBOX_MARGIN", "ANCHOR_K", "WINDOWS", "HOURS", "R_REQ"])
_cfg["alloc"] = _va; _cfg["alloc_cap"] = _consts("conformal/2026-11-25-relative-threshold-allocation.py", ["CAP_SPREADS", "CAP_DRAWS", "CAP_SEED"])
out["esm_cfg"] = _cfg
# Belgrade facility screens (T041): the dynamic flag of the core run and the low-information set of the paper base
_pfb = rd("2026-11-22-core-belgrade-v3-gcal-per-facility.csv")
out["esm_screen"] = {"bel_all": len({x["facility_id"] for x in _pfb}), "bel_static": sorted({int(x["facility_id"]) for x in _pfb if x["dynamic"] != "True"}),
                     "bel_lowinfo": sorted(int(v) for v in _e3x["belgrade"]), "bir_excluded": _rj["excluded"], "bir_kept": _rj["facilities"]}
# S3: rank-cap saturation over the same base as the clip counts (T007), quantile crossings and inverted bands at the headline (T031, T008)
_sat = {}
for x in rd("2026-11-23-core-counters.csv"):
    if x["variant"] == "calibrated gamma" and x["n_q_saturated"]:
        s = _sat.setdefault(f"{x['city']}|{x['method']}", {"steps": 0, "sat": 0.0}); s["steps"] += int(float(x["test_steps"])); s["sat"] += float(x["n_q_saturated"])
for k, s in _sat.items(): assert s["steps"] == out["counters"][k]["steps"]
out["esm_sat"] = _sat
_hd = {"belgrade": ("y_t+15min", _e3x["belgrade"]), "birmingham": ("y_t+60min", _e3x["birmingham"])}
_hl = {}
for c, (hz, ex) in _hd.items():
    for x in rd(f"2026-11-22-core-{c}-v3-gcal-per-facility.csv"):
        if x["horizon"] == hz and x["level"] == "0.9" and x["dynamic"] == "True" and x["facility_id"] not in ex:
            h = _hl.setdefault(f"{c}|{x['method']}", {"n_fac": 0, "n_test": 0, "n_cal": 0, "cross_cal": 0, "cross_test": 0, "sat": 0, "inv": 0, "rows": []})
            h["n_fac"] += 1; h["n_test"] += int(x["n_test"]); h["n_cal"] += int(x["n_cal"]); h["inv"] += int(x["n_inverted"]); h["rows"].append(x)
            for k, col in [("cross_cal", "n_crossings_cal"), ("cross_test", "n_crossings_test"), ("sat", "n_q_saturated")]:
                if x[col]: h[k] += int(float(x[col]))
assert _hl["belgrade|CQR"]["cross_cal"] == _hl["belgrade|ACQR"]["cross_cal"] and _hl["birmingham|CQR"]["cross_test"] == _hl["birmingham|ACQR"]["cross_test"]
# g2 NEW-8: the Birmingham worst facility of each primary method, with its covered count and its 90% block-bootstrap interval
out["esm_worst_bir"] = {}
for m in ["split-CP", "CQR", "ACI", "ACQR"]:
    w = min(_hl[f"birmingham|{m}"]["rows"], key=lambda x: float(x["PICP"])); n = int(w["n_test"]); k = round(float(w["PICP"]) * n)
    assert abs(k / n - float(w["PICP"])) < 1e-12 and abs(float(w["PICP"]) - float(t3_row("birmingham", m)["worst_facility_PICP"])) < 5e-5
    out["esm_worst_bir"][m] = {"fac": int(w["facility_id"]), "k": k, "n": n, "PICP": w["PICP"], "lo": w["picp_ci_lo"], "hi": w["picp_ci_hi"]}
out["esm_nrange_bir"] = [min(int(x["n_test"]) for x in _hl["birmingham|split-CP"]["rows"]), max(int(x["n_test"]) for x in _hl["birmingham|split-CP"]["rows"])]
out["esm_head"] = {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in _hl.items()}
# S3: the gamma-selection fallback that fired (g3 NEW-2, T025)
_gfb = [(c, x) for c in ["belgrade", "birmingham"] for x in rd(f"2026-11-22-core-{c}-v3-gcal-per-facility.csv")
        if x["method"] in ("ACI", "ACQR") and x["gamma"] and not x["gamma_calB_picp"]]
assert all(float(x["gamma"]) == _cfg["gamma_fallback"] for _, x in _gfb)
out["esm_gfb"] = {"n_rows": len(_gfb), "cells": sorted({(c, int(x["facility_id"]), x["horizon"], int(x["n_cal"])) for c, x in _gfb})}
assert len(out["esm_gfb"]["cells"]) == 1   # one facility and horizon; the ESM sentence is written for one cell
# S5 (T012): ToD-ACI, ACI and split-CP cells below 0.80 on the three rolling-origin folds (prespecified EXP-028 arm, the
# paper's exclusion applied), from the 2026-11-25 regeneration of the 5b cells (D-054 item 2)
_5b = [x for x in rd("2026-11-25-orthogonal-5b-cells.csv") if x["arm"] == "A_folds" and x["partition"] == "time_of_day" and x["dynamic"] == "True" and x["facility_id"] not in _e3x["belgrade"]]
out["esm_5b"] = {}
for fo in ["F1", "F2", "F3"]:
    for m in ["ToD-ACI", "ACI", "split-CP"]:
        g = [float(x["PICP"]) for x in _5b if x["fold"] == fo and x["method"] == m]
        out["esm_5b"][f"{fo}|{m}"] = {"n_cells": len(g), "below": sum(v < 0.80 for v in g), "worst": min(g), "n_fac": len({x["facility_id"] for x in _5b if x["fold"] == fo and x["method"] == m}), "facs": sorted({int(x["facility_id"]) for x in _5b if x["fold"] == fo and x["method"] == m})}
# S6 (T024): the boundary-maturity replay, read in the ESM's own key; full precision from the per-facility table as for `ta`
_ta2 = rd("2026-11-25-x08-trust-abstain-excl.csv")
_tap2 = [y for y in rd("2026-11-25-trust-abstain-per-facility.csv") if y["dynamic"] == "True" and y["facility_id"] not in _e3x["belgrade"]]
for _x in _ta2:
    _g = [y for y in _tap2 if y["method"] == _x["method"] and y["commit_target"] == _x["commit_target"]]; assert len(_g) == int(float(_x["n_facilities"]))
    for _k, _h in [("commit_rate", 5e-4), ("committed_PICP", 5e-5), ("committed_MPIW", 5e-3), ("MAE_cars", 5e-4)]:
        _v = st.mean(float(y[_k]) for y in _g); assert abs(_v - float(_x[_k])) < _h; _x[_k] = repr(_v)
out["esm_ta"] = {f"{x['method']}|{x['commit_target']}": x for x in _ta2}
# S8 (T002, g2 NEW-1, NEW-2): the synchronous block bootstrap in both cities, with its exact and safe verdicts
_bb2 = rd("2026-11-25-block-bootstrap-both-cities.csv")
for x in _bb2:
    lo, hi = float(x["boot_lo"]), float(x["boot_hi"])
    assert (x["safe_boot"] == "True") == (lo >= 0.88) and (x["exact_boot"] == "True") == (lo >= 0.88 and hi <= 0.92)
_bel = {x["method"]: x for x in _bb2 if x["city"] == "belgrade"}
for m, b in out["bboot"].items(): assert abs(float(b["boot_lo"]) - float(_bel[m]["boot_lo"])) < 1e-12 and abs(float(b["boot_hi"]) - float(_bel[m]["boot_hi"])) < 1e-12
out["esm_bb2"] = {f"{x['city']}|{x['method']}": x for x in _bb2}
# S8(d) (T017): Belgrade t+15 on all 22 dynamic facilities (a training-window screen keeps facility 8), from the shipped
# per-facility table, checked against the stored control table
_ctl = {x["method"]: x for x in rd("2026-09-04-x08-core-headline-control.csv") if x["city"] == "belgrade"}
out["esm_all22"] = {}
for m in ["split-CP", "CQR", "ACI", "ACQR"]:
    g = [x for x in _pfb if x["horizon"] == "y_t+15min" and x["level"] == "0.9" and x["dynamic"] == "True" and x["method"] == m]
    p = [float(x["PICP"]) for x in g]; n = len(p); mu, sd = st.mean(p), st.stdev(p); lo = mu - _stats.t.ppf(0.95, n - 1) * sd / _math.sqrt(n)
    w = min(g, key=lambda x: float(x["PICP"])); wk = st.mean(float(x["Winkler"]) for x in g)
    assert n == int(_ctl[m]["n"]) and abs(mu - float(_ctl[m]["PICP"])) < 1e-12 and abs(sd - float(_ctl[m]["std"])) < 1e-12 and abs(wk - float(_ctl[m]["Winkler"])) < 1e-9
    out["esm_all22"][m] = {"n": n, "mean": mu, "sd": sd, "t_lower95": lo, "worst": float(w["PICP"]), "worst_fac": int(w["facility_id"]), "Winkler": wk}
# S10 (T070): every paired facility-level contrast, with its effect size; the rolling-pool contrasts (T005) beside them
out["esm_con"] = [dict(x, section="contrast") for x in con] + [dict(x, contrast=x["item"]) for x in rd("2026-11-25-exp045-rolling-inference.csv") if x["section"] == "contrast"]
out["esm_nw"] = {f"{x['city']}|{x['method']}": x for x in rd("2026-11-25-exp045-normalised-winkler.csv")}
for x in out["esm_nw"].values():
    if x["source"].endswith("gcal"): assert abs(float(x["Winkler_mean"]) - float(core_row(x["city"], x["method"])["Winkler"])) < 1e-9
# S11 (T090, T044, T028): Birmingham scored test rows by issue hour, retained against excluded candidates, release lag
_hr = [x for x in rd("2026-11-25-exp045-rows-by-hour.csv") if x["scope"] == "paper_base"]
out["esm_hour"] = {f"{x['horizon']}|{x['hour']}": int(x["n_rows"]) for x in _hr}
_bk = lambda hr: next(b[0] for b in _cfg["buckets"] if b[1] <= hr % 24 <= b[2])
_b60 = {_bk(int(x["hour"])) for x in _hr if x["horizon"] == "y_t+60min" and int(x["n_rows"]) > 0}; assert len(_b60) == 1; _cfg["bir60_bucket"] = _b60.pop()
_cfg["bir60_target_shift"] = [(int(x["hour"]), _bk(int(x["hour"]) + 1), int(x["n_rows"])) for x in _hr if x["horizon"] == "y_t+60min" and int(x["n_rows"]) > 0 and _bk(int(x["hour"]) + 1) != _cfg["bir60_bucket"]]
assert len(_cfg["bir60_target_shift"]) == 1   # revision-59 correction (4): on target time one issue hour moves to the next period
for h in [30, 60, 90]: assert sum(v for k, v in out["esm_hour"].items() if k.startswith(f"y_t+{h}min|")) == int(out["rep"][f"birmingham|t+{h}min"]["test_rows"])
out["esm_retx"] = {f"{x['horizon']}|{x['split']}|{x['group']}": x for x in rd("2026-11-25-exp045-retained-excluded.csv") if x["scope"] == "paper_base"}
out["esm_lag"] = {f"{x['city']}|{x['horizon']}": x for x in rd("2026-11-25-exp045-release-lag.csv") if x["scope"] == "paper_base"}
# S9 and the power paragraph (T014, T021, T022): the Holm-simulating successor of EXP-044 and its settings
out["esm_pow"] = {f"{x['city']}|{x['family']}|{x['item']}|{x['threshold']}|{x['quantity']}|{x['n']}": x for x in rd("2026-11-25-exp045-facility-sample-size-holm.csv")}
out["esm_powset"] = {x["setting"]: x["value"] for x in rd("2026-11-25-exp045-facility-sample-size-holm-settings.csv")}
# S12 (T010, T011, T049, T053): the allocation ladder, its section 0, the capacity perturbation and the seed table
_lad = rd("2026-11-25-exp045-allocation-ladder.csv")
out["esm_lad"] = {f"{x['window']}|{x['day']}|{x['theta']}|{x['policy']}|{x['comparator']}|{x['metric']}": x["value"] for x in _lad}
out["esm_s0"] = {f"{x['window']}|{x['theta']}": x for x in rd("2026-11-25-exp045-rel-alloc-section0.csv")}
_cap = [x for x in rd("2026-11-25-exp045-allocation-capacity.csv") if int(x["draw"]) >= 0]
out["esm_capsens"] = {}
for s in sorted({x["spread"] for x in _cap}, key=float):
    g = [x for x in _cap if x["spread"] == s]; _d = lambda p, c, m: [float(x["value"]) for x in g if x["policy"] == p and x["comparator"] == c and x["metric"] == m]
    rel, sb, mi = _d("INTERVAL", "POINT", "rel_reduction"), _d("INTERVAL", "POINT", "seeds_policy_better"), _d("INTERVAL", "MARGIN", "d_bad_per600_mean")
    assert len(rel) == len(sb) == len(mi) == len({x["draw"] for x in g})
    ns = {int(x["n_seeds"]) for x in g}; assert len(ns) == 1; ns = ns.pop()
    out["esm_capsens"][s] = {"draws": len(rel), "n_seeds": ns, "rel_min": min(rel), "rel_max": max(rel), "draws_all_seeds": sum(v == ns for v in sb), "margin_below": sum(v < 0 for v in mi)}
_sd = rd("2026-11-25-exp045-allocation-seeds.csv")
out["esm_seeds"] = sorted({int(x["seed"]) for x in _sd})
_exa = {x["excluded"] for x in out["esm_s0"].values()}; assert len(_exa) == 1
_cp = [x for x in rd("2026-09-04-vignette-capacity-proxy.csv") if x["facility_id"] not in _exa]
assert len(_cp) == int(next(iter(out["esm_s0"].values()))["n_base"])
out["esm_cap_range"] = [min(float(x["cap_train"]) for x in _cp), max(float(x["cap_train"]) for x in _cp)]
# S9 (T003): the safety leg adjusted the way the exact leg is (Holm over the four primary methods of a city), for disclosure only
out["esm_safeholm"] = {}
for c in ["belgrade", "birmingham"]:
    _p = {m: float(_stats.t.sf((float(pop_row(c, m)["mean_PICP"]) - 0.88) / float(pop_row(c, m)["se"]), int(pop_row(c, m)["n_fac"]) - 1)) for m in ["split-CP", "CQR", "ACI", "ACQR"]}
    for m, v in _p.items(): assert (v <= 0.05) == (pop_row(c, m)["SAFE_t"] == "True")   # the pointwise verdict of record is this one-sided test at 0.05
    _o = sorted(_p, key=_p.get); _adj, _run = {}, 0.0
    for i, m in enumerate(_o): _run = max(_run, min(1.0, (len(_o) - i) * _p[m])); _adj[m] = _run
    out["esm_safeholm"][c] = {m: {"raw": _p[m], "holm": _adj[m]} for m in _p}
(ROOT/"06_manuscript"/"CTR"/"_build").mkdir(exist_ok=True)
json.dump(out, open(ROOT/"06_manuscript"/"CTR"/"_build"/"typeset.json","w"), indent=1, default=str)
print("typeset.json written;", "T6 rows", out["T6_n"])
