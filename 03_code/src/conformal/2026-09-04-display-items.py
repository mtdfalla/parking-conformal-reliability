#!/usr/bin/env python3
"""Display items T3' and T6 for D-020 — built from logged CSVs only, no re-fit.

T3'  the two-level inference table (R-Phase 4, EXP-030), replacing the pre-audit paired-tests table.
T6   the evaluation-protocol sensitivity table: protocol choice -> mechanism -> measured effect.

Every cell traces to a CSV in 05_results/tables/. Rows whose effect is NOT separately attributable, or
whose source has no writer in the tree, are emitted with `provenance` saying so rather than being quietly
dropped or quietly included -- the manuscript rule is that every number traces to a CSV, and a row that
cannot meet it must be visible as such before R-Phase 7 decides what to print.

MIN_CELL for the facility x bucket counts is 30, as prespecified in EXP-021 and unchanged.
Outputs: 2026-09-04-T3prime-two-level-inference.csv, 2026-09-04-T6-protocol-sensitivity.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TAB = ROOT / "05_results" / "tables"
sys.path.insert(0, str(HERE))

DROP = {"belgrade": [1, 8], "birmingham": []}
ROWS = [("belgrade", "y_t+15min"), ("birmingham", "y_t+60min")]
MIN_CELL = 30


def logged_path(name) -> Path:
    """Locate a table, preferring the run's own output and falling back to the shipped reference.

    2026-09-05 (revision 44, EXP-035, lesson C14). Several inputs of this script are ARCHIVED artifacts
    that no live step regenerates -- `2026-09-02-core-{city}-per-facility.csv` (the pre-gamma-calibration
    tables), `2026-09-02-v2-representativeness.csv` and `2026-09-04-phase4-safe-mechanism.csv`. In the
    REPOSITORY they sit in `05_results/tables/`; in the SHIPPED PACKAGE that directory is the
    replicator's own, initially empty, output directory and our outputs live in `05_results/reference/`,
    so a from-scratch run raised FileNotFoundError here. Every read in this file goes through this helper
    rather than three of them: the fallback is correct for a regenerated table too, because the
    replicator's own file wins wherever one exists. Never invert the order, and never copy an archived
    file INTO tables/ -- pre-seeding a replicator's output directory with our numbers would let a run
    "reproduce" a file we handed them. Found by the clean-room run, not by reading the code (C12).
    """
    p = TAB / str(name)
    return p if p.exists() else (ROOT / "05_results" / "reference" / str(name))


def log(m):
    print(f"[display-items] {m}", flush=True)


# ---------------------------------------------------------------- T3'

def worst_cells() -> dict:
    """Belgrade facility x bucket worst cell and count below 0.80, on the excluded base (EXP-021)."""
    d = pd.read_csv(logged_path("2026-09-03-tod-facility-bucket.csv"))
    d = d[(d.dynamic) & (d.degenerate != True) & (~d.facility_id.isin(DROP["belgrade"]))
          & (d.n_cell >= MIN_CELL)]
    out = {}
    for m, s in d.groupby("method"):
        out[m] = dict(worst_cell=float(s.PICP.min()), n_cells=int(len(s)),
                      cells_below_080=int((s.PICP < 0.80).sum()))
    return out


def build_t3prime() -> pd.DataFrame:
    pop = pd.read_csv(logged_path("2026-09-04-phase4-population.csv"))
    fac = pd.read_csv(logged_path("2026-09-04-phase4-facility.csv"))
    wc = worst_cells()
    out = []
    for city, hz in ROWS:
        for meth in ["split-CP", "CQR", "ACI", "ACQR"]:
            p = pop[(pop.city == city) & (pop.method == meth) & (~pop.exploratory)].iloc[0]
            f = fac[(fac.city == city) & (fac.method == meth)].iloc[0]
            cell = wc.get(meth) if city == "belgrade" else None
            out.append(dict(
                scope="population + facility level (core method)",
                city=city, horizon=hz, method=meth, n_facilities=int(p.n_fac),
                # --- population level: equivalence IS claimed here
                mean_PICP=round(float(p.mean_PICP), 4),
                ci90_lo=round(float(p.t_lo90), 4), ci90_hi=round(float(p.t_hi90), 4),
                boot_ci90_lo=round(float(p.boot_lo90), 4), boot_ci90_hi=round(float(p.boot_hi90), 4),
                EXACT=bool(p.EXACT_t), SAFE=bool(p.SAFE_t),
                tost_p_holm=float(p.tost_p_holm), mean_Winkler=round(float(p.mean_Winkler), 2),
                # --- facility level: equivalence NOT claimed
                across_facility_sd=round(float(f.sd_PICP), 4),
                worst_facility=int(f.worst_facility), worst_facility_PICP=round(float(f.worst_PICP), 4),
                frac_facilities_below_nominal=round(float(f.frac_below_nominal), 3),
                worst_facility_bucket_cell=(round(cell["worst_cell"], 4) if cell else np.nan),
                cells_below_080=(cell["cells_below_080"] if cell else np.nan),
                n_cells=(cell["n_cells"] if cell else np.nan),
                facility_equivalence_claimed=False))
    # ToD-ACI is a Belgrade-only conditional variant; carried as its own row for the same table
    for meth in ["ToD-ACI", "Mondrian-split-CP"]:
        cell = worst_cells().get(meth)
        if cell:
            out.append(dict(scope="cell level only — reference row, the method's population/facility "
                                  "statistics live in T4, not here",
                            city="belgrade", horizon="y_t+15min", method=meth, n_facilities=21,
                            mean_PICP=np.nan, ci90_lo=np.nan, ci90_hi=np.nan, boot_ci90_lo=np.nan,
                            boot_ci90_hi=np.nan, EXACT=None, SAFE=None, tost_p_holm=np.nan,
                            mean_Winkler=np.nan, across_facility_sd=np.nan, worst_facility=np.nan,
                            worst_facility_PICP=np.nan, frac_facilities_below_nominal=np.nan,
                            worst_facility_bucket_cell=round(cell["worst_cell"], 4),
                            cells_below_080=cell["cells_below_080"], n_cells=cell["n_cells"],
                            facility_equivalence_claimed=False))
    return pd.DataFrame(out)


# ---------------------------------------------------------------- T6

def core_pf(city, hz, gcal: bool):
    f = f"2026-09-02-core-{city}-{'gcal-' if gcal else ''}per-facility.csv"
    d = pd.read_csv(logged_path(f))
    return d[(d.horizon == hz) & (d.level == 0.90) & (d.dynamic)
             & (~d.facility_id.isin(DROP[city]))].dropna(subset=["PICP"])


def paired(a: pd.Series, b: pd.Series):
    idx = a.index.intersection(b.index)
    va, vb = a.loc[idx].values, b.loc[idx].values
    p = float(stats.wilcoxon(va, vb).pvalue) if not np.allclose(va, vb) else 1.0
    return float(np.mean(va)), float(np.mean(vb)), float(np.mean(vb - va)), p, len(idx)


def build_t6() -> pd.DataFrame:
    R = []

    # --- row A: EnbPI update schedule (C07), paired INSIDE ONE FIT
    for city, hz in ROWS:
        e = pd.read_csv(logged_path(f"2026-09-03-e3-{city}-per-facility.csv"))
        e = e[(e.arm == "A12_v1_paired") & (e.dynamic) & (e.degenerate != True)
              & (e.level == 0.9) & (~e.facility_id.isin(DROP[city]))]
        old = e[e.method == "EnbPI-oldchunk"].set_index("facility_id").PICP
        new = e[e.method == "EnbPI-daychunk"].set_index("facility_id").PICP
        m_old, m_new, d, p, n = paired(old, new)
        R.append(dict(
            protocol_choice="EnbPI outcome release: fixed row chunks vs calendar-day chunks with matured-only release",
            audit_issue="C07", mechanism="the archived schedule releases the last h-1 outcomes of each chunk before they have matured, feeding the residual pool early",
            city=city, statistic="EnbPI mean PICP", before=round(m_old, 4), after=round(m_new, 4),
            delta=round(d, 4), n=n, paired_p=round(p, 6),
            direction_vs_our_claim="AGAINST US — the fix makes EnbPI slightly better, so our comparative claim mildly weakens",
            provenance=f"2026-09-03-e3-{city}-per-facility.csv (arm A12_v1_paired, paired inside one fit)"))

    # --- row B: gamma selection protocol, fixed 0.05 vs calibration-selected
    for city, hz in ROWS:
        fx, cal = core_pf(city, hz, False), core_pf(city, hz, True)
        for meth in ["ACI", "ACQR", "split-CP"]:
            a = fx[fx.method == meth].set_index("facility_id").PICP
            b = cal[cal.method == meth].set_index("facility_id").PICP
            m_a, m_b, d, p, n = paired(a, b)
            sd_a = float(fx[fx.method == meth].PICP.std()); sd_b = float(cal[cal.method == meth].PICP.std())
            R.append(dict(
                protocol_choice="step-size gamma: fixed at 0.05 vs selected on a held-out calibration block",
                audit_issue="EXP-019 / D-016", mechanism="a fixed step size is a tuning choice made once and applied to every facility; selecting it on calibration moves coverage toward target and slightly raises dispersion",
                city=city, statistic=f"{meth} mean PICP (across-facility sd)",
                before=round(m_a, 4), after=round(m_b, 4), delta=round(d, 4), n=n, paired_p=round(p, 6),
                direction_vs_our_claim=("NEGATIVE CONTROL — gamma does not touch split-CP and its numbers are identical"
                                        if meth == "split-CP" else
                                        f"HONEST TRADE — sd {sd_a:.4f} -> {sd_b:.4f}"),
                provenance=f"2026-09-02-core-{city}-per-facility.csv vs -gcal-per-facility.csv"))

    # --- row C: low-information exclusion (X08). The spine is the RATIO, so emit its components too.
    ba = pd.read_csv(logged_path("2026-09-04-x08-before-after.csv"))
    sel = ba[(ba.experiment == "EXP-017/019 core headline") & (ba.statistic == "std")
             & (ba.unit.str.startswith("belgrade"))].set_index(
                 ba[(ba.experiment == "EXP-017/019 core headline") & (ba.statistic == "std")
                    & (ba.unit.str.startswith("belgrade"))].unit.str.split("|").str[-1].str.strip())
    for meth in ["split-CP", "ACQR", "ACI", "CQR"]:
        r = sel.loc[meth]
        R.append(dict(
            protocol_choice="data-quality exclusion of low-information facility-windows (< 10 distinct readings)",
            audit_issue="X08 / D-018",
            mechanism="a stuck sensor reporting two distinct values across a 1,015-row test window inflates every dispersion statistic it enters, and it inflated the adaptive methods' more than split-CP's",
            city="belgrade", statistic=f"{meth} across-facility sd", before=round(float(r.before), 4),
            after=round(float(r.after), 4), delta=round(float(r.delta), 4), n=21, paired_p=np.nan,
            direction_vs_our_claim="MIXED — see the ratio row",
            provenance="2026-09-04-x08-before-after.csv"))
    rb, ra = float(sel.loc["split-CP"].before) / float(sel.loc["ACQR"].before), \
             float(sel.loc["split-CP"].after) / float(sel.loc["ACQR"].after)
    R.append(dict(
        protocol_choice="data-quality exclusion of low-information facility-windows (< 10 distinct readings)",
        audit_issue="X08 / D-018",
        mechanism="the exclusion rule is stated on the inputs only and is blind to every method's performance; the threshold is not delicate (facility 1 -> 1 distinct reading, facility 8 -> 2, next lowest -> 64, so any cutoff in [3, 60] selects the same two)",
        city="belgrade", statistic="split-CP / ACQR across-facility dispersion RATIO",
        before=round(rb, 2), after=round(ra, 2), delta=round(ra - rb, 2), n=21, paired_p=np.nan,
        direction_vs_our_claim="MIXED, and it must be reported both ways — the paper's spine STRENGTHENS 6.20x -> 7.76x, while our absolute baseline-failure claims WEAKEN (EnbPI worst facility 0.6640 -> 0.8010) and the EnbPI/ACI ratio weakens 5.57x -> 4.42x",
        provenance="2026-09-04-x08-before-after.csv"))

    # --- row D: unit of inference, pooled rows vs facility-clustered
    ro = pd.read_csv(logged_path("2026-09-03-rolling-origin-inference.csv"))
    ro = ro[(ro.gamma_mode == "calibrated") & (ro.population == "dynamic_all_folds_x08excl")]
    for _, r in ro.iterrows():
        R.append(dict(
            protocol_choice="unit of inference: pooled fold-facility rows vs facility-clustered",
            audit_issue="I04", mechanism="each facility appears in every fold, so pooling treats repeated measurements on the same unit as independent",
            city="belgrade", statistic=f"{r.contrast}: p-value",
            before=float(r.wilcoxon_p_pooled_ARCHIVED_STYLE), after=float(r.wilcoxon_p_holm),
            delta=np.nan, n=int(r.n_facilities), paired_p=np.nan,
            direction_vs_our_claim=f"AGAINST US — the honest p is {r.anticonservatism_ratio:.1f}x weaker; all four still survive Holm",
            provenance="2026-09-03-rolling-origin-inference.csv"))

    # --- row E: certification criterion, "CI contains nominal" vs the three-leg criterion
    fac = pd.read_csv(logged_path("2026-09-04-phase4-facility.csv"))
    for city, hz in ROWS:
        for meth in ["split-CP", "ACI"]:
            f = fac[(fac.city == city) & (fac.method == meth)].iloc[0]
            R.append(dict(
                protocol_choice='certification criterion: "the facility CI contains 0.90" vs safety + exactness + efficiency',
                audit_issue="I01", mechanism="failing to reject equality is not evidence of equality, and a wider interval passes more easily — so the retired criterion rewarded the method with the widest intervals",
                city=city, statistic=f"{meth}: fraction of facilities certified",
                before=round(float(f.RETIRED_ci_contains_nominal), 4),
                after=round(float(f.frac_below_nominal), 4), delta=np.nan, n=int(f.n_fac), paired_p=np.nan,
                direction_vs_our_claim="AGAINST US — the retired criterion certified our own ACI at 0.952-1.000 against split-CP's 0.619-0.714",
                provenance="2026-09-04-phase4-facility.csv"))

    # --- row F: capacity proxy read off the scored window
    con = pd.read_csv(logged_path("2026-09-04-vignette-contrasts.csv"))
    R.append(dict(
        protocol_choice="capacity proxy computed over the full record (test window included) vs the training window only",
        audit_issue="D01", mechanism="the proxy for one facility was the constant its dead sensor reported inside the test window (109 against a training maximum of 65), so the policy was scored against a series pinned above its own capacity",
        city="belgrade", statistic="allocation vignette: overflow reduction, POINT - INTERVAL (pp)",
        before=14.83, after=0.0, delta=-14.83, n=20, paired_p=np.nan,
        direction_vs_our_claim="AGAINST US — an entire published headline effect was one dead sensor and is now identically zero",
        provenance="2026-09-04-vignette-{capacity-proxy,contrasts,x08-attribution}.csv; before value is the EXP-015 published figure, reproduced to 4 dp by the repro gate"))

    # --- row G: facility-level safety bound at finite n
    sm = pd.read_csv(logged_path("2026-09-04-phase4-safe-mechanism.csv"))
    for _, r in sm[sm.method.isin(["split-CP", "ACQR", "ACI"])].iterrows():
        R.append(dict(
            protocol_choice="safety judged by a one-sided lower bound at the FACILITY level vs at the population level",
            audit_issue="I01 (second-order)", mechanism="at this n the lower bound sits 3-6 coverage points below the point estimate, so a facility must over-cover to be called safe",
            city=r.city, statistic=f"{r.method}: PICP a facility needs to pass the safety bound",
            before=0.88, after=float(r.implied_PICP_needed_to_pass_SAFE), delta=np.nan,
            n=int(r.n_fac), paired_p=np.nan,
            direction_vs_our_claim="AGAINST US at facility level — 0 of 21 adaptive facilities pass, while over-covering split-CP facilities do",
            provenance="2026-09-04-phase4-safe-mechanism.csv"))

    # --- row H: data rebuild. Exposure measured; effect NOT separately attributable.
    rep = pd.read_csv(logged_path("2026-09-02-v2-representativeness.csv"))
    b = rep[(rep.city.str.lower() == "birmingham")]
    if not b.empty:
        r = b.iloc[-1]
        R.append(dict(
            protocol_choice="interpolation across a closure/night boundary in the feature build",
            audit_issue="S02 / X01", mechanism="interpolate(limit=1) filled the first slot after closing with the NEXT MORNING's value, so a target could span a night",
            city="birmingham", statistic=f"{r.horizon}: % of targets interpolated",
            before=float(r.target_interpolated_pct), after=0.0, delta=np.nan,
            n=int(r.facilities), paired_p=np.nan,
            direction_vs_our_claim="EXPOSURE REMOVED — but the effect is NOT separately attributable: the data fix and the C01 fix landed in the same rerun",
            provenance="2026-09-02-v2-representativeness.csv"))

    return pd.DataFrame(R)


def main():
    t3 = build_t3prime()
    t3.to_csv(TAB / "2026-09-04-T3prime-two-level-inference.csv", index=False)
    log(f"wrote T3' ({len(t3)} rows)")
    t6 = build_t6()
    t6.to_csv(TAB / "2026-09-04-T6-protocol-sensitivity.csv", index=False)
    log(f"wrote T6 ({len(t6)} rows, {t6.protocol_choice.nunique()} distinct protocol choices)")
    print()
    print(t3.to_string(index=False))
    print()
    print(t6[["protocol_choice", "audit_issue", "city", "statistic", "before", "after",
              "direction_vs_our_claim"]].to_string(index=False))


if __name__ == "__main__":
    main()
