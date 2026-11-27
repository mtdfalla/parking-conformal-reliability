#!/usr/bin/env python3
"""
EXP-045 arm A1 inference (external-audit finding T005): the rolling-pool fixed-alpha arm against the
adaptive methods, on the paper base.

Prespecification: 04_experiments/2026-11-25-EXP-045-audit-arms-PRESPECIFICATION.md, section 1 (A1) and the
stop rule in section 2 item 1.

Family R (new, per city, two contrasts): ACI vs RS-CP and ACQR vs RS-CQR. Statistic: the paired per-facility
difference in |PICP - 0.90|. Two-sided Wilcoxon signed-rank (scipy default, exact when untied, as phase4),
Holm over the two contrasts within a city. Also reported, unadjusted: RS-CP vs split-CP and RS-CQR vs CQR
(the refresh share), the Winkler differences, and the population rules for RS-CP and RS-CQR exactly as
phase4 applies them (pointwise SAFE_t, EXACT_t, and the Holm outcome of the TOST over the six methods).

Every statistic comes from `2026-09-04-phase4-inference.py`, imported, not re-implemented (B9). The paper
base is its `core_frame` with its computed exclusion set. GATE, run first: on the four shipped methods this
script must reproduce mean_PICP and sd_PICP of 2026-09-04-phase4-population.csv and mean_diff and
wilcoxon_p_raw of its D-dispersion contrasts to 1e-12. If not, it stops and writes nothing.

Output: 05_results/tables/2026-11-25-exp045-rolling-inference.csv
Exit status 3 means the T005 stop rule fired (the decision row says so).
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("phase4", HERE / "2026-09-04-phase4-inference.py")
P4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(P4)
TAB = P4.TAB
OUT = TAB / "2026-11-25-exp045-rolling-inference.csv"
NOM = P4.NOMINAL


def log(m): print(f"[exp045-A1] {m}", flush=True)


def frames(drop_map):
    out = {}
    for city, hz, _ in P4.ROWS:
        drop = drop_map.get(city, [])
        base = P4.core_frame(city, hz, drop)
        rs = pd.read_csv(TAB / f"2026-11-25-core-{city}-v3-rolling0-per-facility.csv")
        rs = rs[(rs.horizon == hz) & (rs.level == 0.90) & (rs.dynamic)]
        rs = rs[~rs.facility_id.isin(drop)].sort_values("facility_id", kind="stable")
        out[city] = (hz, pd.concat([base, rs], ignore_index=True))
    return out


def gate(drop_map) -> bool:
    pop = pd.read_csv(TAB / "2026-09-04-phase4-population.csv")
    con = pd.read_csv(TAB / "2026-09-04-phase4-contrasts.csv")
    new_pop = P4.population(drop_map); new_con = P4.contrasts(drop_map)
    bad = 0
    for _, r in pop[pop.family == "P-primary"].iterrows():
        n = new_pop[(new_pop.city == r.city) & (new_pop.method == r.method) & (new_pop.family == "P-primary")].iloc[0]
        bad += int(abs(n.mean_PICP - r.mean_PICP) > 1e-12 or abs(n.sd_PICP - r.sd_PICP) > 1e-12 or n.n_fac != r.n_fac)
    for _, r in con[con.family == "D-dispersion"].iterrows():
        n = new_con[(new_con.city == r.city) & (new_con.contrast == r.contrast) & (new_con.family == "D-dispersion")].iloc[0]
        bad += int(abs(n.mean_diff - r.mean_diff) > 1e-12 or abs(n.wilcoxon_p_raw - r.wilcoxon_p_raw) > 1e-12)
    log(f"gate: {len(pop[pop.family == 'P-primary'])} population rows and "
        f"{len(con[con.family == 'D-dispersion'])} D-dispersion rows checked, {bad} mismatch(es)")
    return bad == 0


def contrast_row(d, a, b, col, transform, family, city, hz):
    sa = d[d.method == a].set_index("facility_id")[col].dropna()
    sb = d[d.method == b].set_index("facility_id")[col].dropna()
    idx = sa.index.intersection(sb.index)
    va, vb = transform(sa.loc[idx].values), transform(sb.loc[idx].values)
    diff = va - vb
    mdiff, blo, bhi, bp = P4.boot_diff(diff)
    return dict(city=city, horizon=hz, section="contrast", family=family, item=f"{a} vs {b}", n_fac=len(idx),
                mean_a=float(np.mean(va)), mean_b=float(np.mean(vb)), mean_diff=mdiff,
                boot_lo95=blo, boot_hi95=bhi, boot_p=bp,
                pct_facilities_favouring_a=float((diff < 0).mean() * 100.0),
                wilcoxon_p_raw=float(stats.wilcoxon(va, vb).pvalue))


def main():
    reagg = P4.load_script("2026-09-04-x08-reaggregate.py")
    ex = reagg.exclusion_sets()
    drop_map = {"belgrade": ex[("belgrade", "use_15")], "birmingham": ex[("birmingham", "use_60")]}
    log(f"exclusion sets (computed): {drop_map}")
    if not gate(drop_map):
        log("GATE FAILED: nothing written"); sys.exit(1)

    gap = lambda v: np.abs(v - NOM)
    rows = []; stop = None
    for city, (hz, d) in frames(drop_map).items():
        fam = [contrast_row(d, a, b, "PICP", gap, "R-dispersion", city, hz)
               for a, b in (("ACI", "RS-CP"), ("ACQR", "RS-CQR"))]
        for r, a_ in zip(fam, P4.holm([r["wilcoxon_p_raw"] for r in fam])):
            r["wilcoxon_p_holm"] = a_; r["significant_holm_005"] = bool(a_ < P4.ALPHA)
        rows += fam
        rows += [contrast_row(d, a, b, "PICP", gap, "R-refresh (descriptive)", city, hz)
                 for a, b in (("RS-CP", "split-CP"), ("RS-CQR", "CQR"))]
        rows += [contrast_row(d, a, b, "Winkler", lambda v: v, "R-efficiency (descriptive)", city, hz)
                 for a, b in (("ACI", "RS-CP"), ("ACQR", "RS-CQR"))]
        # population rules, all six methods, exactly as phase4 (pointwise SAFE_t; Holm over the TOST p)
        prim = []
        for meth in P4.CORE_METHODS + ["RS-CP", "RS-CQR"]:
            x = d[d.method == meth].PICP.dropna().values
            m, sd, se, lo, hi, low95, tost_p = P4.t_legs(x)
            prim.append(dict(city=city, horizon=hz, section="population", family="P-with-rolling", item=meth,
                             n_fac=len(x), mean_PICP=m, sd_PICP=sd, worst_PICP=float(x.min()),
                             t_lo90=lo, t_hi90=hi, t_lower95=low95,
                             SAFE_t_pointwise=bool(low95 >= NOM - P4.EPS),
                             EXACT_t=bool(lo >= NOM - P4.EPS and hi <= NOM + P4.EPS),
                             tost_p_raw=tost_p, mean_Winkler=float(d[d.method == meth].Winkler.mean())))
        for r, a_ in zip(prim, P4.holm([r["tost_p_raw"] for r in prim])):
            r["tost_p_holm"] = a_; r["EXACT_holm"] = bool(a_ < P4.ALPHA)
        rows += prim
        # share of the split-to-adaptive sd reduction given by the rolling refresh
        sd = {r["item"]: r["sd_PICP"] for r in prim}
        for split, rsm, ad in (("split-CP", "RS-CP", "ACI"), ("CQR", "RS-CQR", "ACQR")):
            rows.append(dict(city=city, horizon=hz, section="decomposition", family="sd share", item=f"{split} > {rsm} > {ad}",
                             value=(sd[split] - sd[rsm]) / (sd[split] - sd[ad])))
        if city == "belgrade":
            fail = [r["item"] for r in fam if not (r["wilcoxon_p_holm"] < P4.ALPHA and r["mean_diff"] < 0)]
            stop = bool(fail)
            rows.append(dict(city=city, horizon=hz, section="decision", family="T005 stop rule",
                             item="FIRED: " + "; ".join(fail) if fail else "not fired", value=float(stop)))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    log(f"wrote {OUT.name}: {len(rows)} rows")
    if stop:
        log("T005 STOP RULE FIRED: stop and report to the author before any text work"); sys.exit(3)
    log("T005 stop rule not fired. ALL DONE")


if __name__ == "__main__":
    main()
