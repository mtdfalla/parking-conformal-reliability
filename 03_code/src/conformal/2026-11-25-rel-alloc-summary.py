#!/usr/bin/env python3
"""EXP-045 arm A2 successor (findings T009, T010, T011, T053), built 2026-11-25 from
`2026-09-05-rel-alloc-summary.py` by exact replacement (`tools/make_alloc_a2_ladder.py`).

What changed and why.
* Reads the 2026-11-25 seeds and section-0 tables of `2026-11-25-relative-threshold-allocation.py`
  and imports `2026-11-25-allocation-vignette.py` for gate 3. The shipped computation of the paired
  summary is unchanged and runs on the full-window rows (day == "all").
* REPRODUCTION GATE (prespec A2): POINT, INTERVAL and MARGIN must reproduce every cell of
  `2026-09-05-rel-alloc-summary.csv`, every row of `2026-09-05-rel-alloc-seeds.csv` and every shipped
  column of `2026-09-05-rel-alloc-section0.csv`. Any difference stops the arm (exit 1).
* Writes `2026-11-25-exp045-allocation-ladder.csv` (long: window, day, theta, policy, comparator,
  metric, value, n_seeds, ...) with the T009 policies, the T053 paired seed SE and day split, and the
  T011 miss rates, and `2026-11-25-exp045-allocation-ladder-wide.csv`, the shipped summary columns
  for all six policies so the table can be typeset.
* Checks the unperturbed control row of the T010 capacity table against the ladder.

Original header follows.

EXP-034 — the paired summary and the gate for the relative-threshold allocation run.

Prespecified statistics only (`2026-09-05-rphase-C-PRESPECIFICATION.md` section 2): bad assignments PER
REQUEST as the primary, abstention rate and mean straight-line distance beside it, MARGIN as the control,
20 paired seeds, and the number of seeds in which the sign holds. No p-value: the seeds vary the requests
on one shared panel and are not independent replicates of the world.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
TAB = ROOT / "05_results" / "tables"
S_ALL = pd.read_csv(TAB / "2026-11-25-exp045-allocation-seeds.csv")   # parsed as the shipped run parsed
S = S_ALL[S_ALL.day == "all"]
S0 = pd.read_csv(TAB / "2026-11-25-exp045-rel-alloc-section0.csv")

# ---- GATE 3: the imported machinery must be the EXP-029 machinery -------------------------------
cap_ref = pd.read_csv(TAB / "2026-09-04-vignette-capacity-proxy.csv").dropna(subset=["cap_train"])
import importlib.util
spec = importlib.util.spec_from_file_location(
    "vign", ROOT / "03_code" / "src" / "conformal" / "2026-11-25-allocation-vignette.py")
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)
cur = V.phase_a(*V.load()[:1], V.load()[2], V.load()[3], 1e9, 0.0).dropna(subset=["cap_train"])
m = cap_ref.merge(cur, on="facility_id", suffixes=("_ref", "_now"))
gate3_bad = int((np.abs(m.cap_train_ref - m.cap_train_now) > 0).sum()) + \
            int((np.abs(m.gamma_ref - m.gamma_now) > 0).sum())
print(f"GATE 3 (import reproduces the EXP-029 panel): {len(m)} facilities, "
      f"{gate3_bad} mismatches on capacity proxy and gamma")
gate4_bad = int((S0.point_only_withdrawn_slots != 0).sum())
print(f"GATE 4 (POINT-only withdrawals must be 0, arithmetic): {gate4_bad} violations")
if gate3_bad or gate4_bad:
    print("GATE FAILED — branch X. Nothing is reported."); sys.exit(1)

# ---- the paired contrasts ------------------------------------------------------------------------
P = S.pivot_table(index=["window", "theta", "seed"], columns="policy",
                  values=["bad_assignments_per_request", "abstention_rate", "mean_straight_line_km"])
rows = []
for (w, th), g in P.groupby(level=[0, 1]):
    bad = g["bad_assignments_per_request"]; ab = g["abstention_rate"]; km = g["mean_straight_line_km"]
    d_iv = bad.POINT - bad.INTERVAL          # >0 means INTERVAL makes FEWER bad assignments
    d_mg = bad.POINT - bad.MARGIN
    d_iv_mg = bad.MARGIN - bad.INTERVAL      # >0 means INTERVAL beats the matched-conservatism control
    s0 = S0[(S0.window == w) & (np.isclose(S0.theta, th))].iloc[0]
    rows.append(dict(
        window=w, theta=th, n_seeds=len(g), facilities_with_event=int(s0.facilities_with_event),
        event_rate=float(s0.event_rate),
        bad_POINT=bad.POINT.mean(), bad_INTERVAL=bad.INTERVAL.mean(), bad_MARGIN=bad.MARGIN.mean(),
        d_point_minus_interval=d_iv.mean(), d_seed_min=d_iv.min(), d_seed_max=d_iv.max(),
        seeds_sign_holds=int((d_iv > 0).sum()),
        rel_reduction_vs_point=float(d_iv.mean() / bad.POINT.mean()) if bad.POINT.mean() else np.nan,
        d_point_minus_margin=d_mg.mean(),
        d_margin_minus_interval=d_iv_mg.mean(), seeds_beats_margin=int((d_iv_mg > 0).sum()),
        abst_POINT=ab.POINT.mean(), abst_INTERVAL=ab.INTERVAL.mean(), abst_MARGIN=ab.MARGIN.mean(),
        abst_cost_pp=100 * (ab.INTERVAL.mean() - ab.POINT.mean()),
        km_POINT=km.POINT.mean(), km_INTERVAL=km.INTERVAL.mean(), km_MARGIN=km.MARGIN.mean()))
D = pd.DataFrame(rows).sort_values(["window", "theta"])

# ---- EXP-045 A2 REPRODUCTION GATE ----------------------------------------------------------------
import importlib.util as _ilu
_rs = _ilu.spec_from_file_location("rel45", ROOT / "03_code" / "src" / "conformal" /
                                   "2026-11-25-relative-threshold-allocation.py")
REL = _ilu.module_from_spec(_rs); _rs.loader.exec_module(REL)
RT = dict(float_precision="round_trip")
ref_seeds = pd.read_csv(TAB / "2026-09-05-rel-alloc-seeds.csv", **RT)
new_seeds = pd.read_csv(TAB / "2026-11-25-exp045-allocation-seeds.csv", **RT)
new_seeds = new_seeds[(new_seeds.day == "all") & new_seeds.policy.isin(REL.SHIPPED_POLICIES)]
new_seeds = new_seeds.reset_index(drop=True)[list(ref_seeds.columns)]
ref_sum = pd.read_csv(TAB / "2026-09-05-rel-alloc-summary.csv", **RT)
new_sum = D.reset_index(drop=True)[list(ref_sum.columns)]
ref_s0 = pd.read_csv(TAB / "2026-09-05-rel-alloc-section0.csv", **RT)
new_s0 = pd.read_csv(TAB / "2026-11-25-exp045-rel-alloc-section0.csv", **RT)[list(ref_s0.columns)]
g_bad = g_ulp = 0
for lab, r_, n_ in (("seeds", ref_seeds, new_seeds), ("summary", ref_sum, new_sum),
                    ("section0", ref_s0, new_s0)):
    b_, u_, c_ = REL.frames_identical(r_, n_, lab)
    print(f"REPRODUCTION GATE {lab}: {len(r_)} rows, {c_} cells, {b_} mismatches, "
          f"{u_} last-ulp storage differences")
    g_bad += b_; g_ulp += u_
if g_bad:
    print("REPRODUCTION GATE FAILED. The arm stops (prespec section 2 rule 2)."); sys.exit(1)
print("REPRODUCTION GATE PASSED" + (" (last-ulp storage differences only)" if g_ulp else " (exact)"))

pd.set_option("display.width", 250)
print("\n=== PAIRED SUMMARY (20 seeds, identical requests within a seed) ===")
print(D[["window", "theta", "facilities_with_event", "bad_POINT", "bad_INTERVAL", "bad_MARGIN",
         "d_point_minus_interval", "seeds_sign_holds", "rel_reduction_vs_point",
         "d_margin_minus_interval", "seeds_beats_margin",
         "abst_POINT", "abst_INTERVAL", "abst_MARGIN", "abst_cost_pp"]].round(4).to_string(index=False))

# ---- EXP-045 A2: the ladder (long) ---------------------------------------------------------------
LONG = []
for (w, day, th), g in S_ALL.groupby(["window", "day", "theta"], sort=False):
    for r in REL.cell_metrics(g):
        r.update(window=w, day=day, theta=th, n_facility_slots=np.nan, n_slots=int(g.n_slots.iloc[0]),
                 n_base=int(g.n_base.iloc[0]))
        LONG.append(r)
for _, s0 in S0.iterrows():                               # T011 at the facility-slot level
    for p in REL.POLICIES:
        c = REL.colname(p)
        for m, unit in (("withdraw_rate", "share of facility-slots"),
                        ("upper_miss_all_slots", "share of facility-slots"),
                        ("upper_miss_offered_slots", "share of offered facility-slots"),
                        ("event_rate_offered_slots", "share of offered facility-slots")):
            src = {"upper_miss_all_slots": f"upper_miss_all_{c}",
                   "upper_miss_offered_slots": f"upper_miss_offered_{c}",
                   "event_rate_offered_slots": f"event_rate_offered_{c}"}.get(m, f"{m}_{c}")
            LONG.append(dict(window=s0.window, day="all", theta=s0.theta, policy=p, comparator="",
                             metric=m, value=float(s0[src]), n_seeds=np.nan, unit=unit,
                             n_facility_slots=int(s0.n_facility_slots), n_slots=int(s0.n_slots),
                             n_base=int(s0.n_base)))
L = pd.DataFrame(LONG)[["window", "day", "theta", "policy", "comparator", "metric", "value", "n_seeds",
                        "unit", "n_facility_slots", "n_slots", "n_base"]]
L = L.sort_values(["window", "day", "theta"], kind="stable").reset_index(drop=True)
L["n_seeds"] = L.n_seeds.astype("Int64"); L["n_facility_slots"] = L.n_facility_slots.astype("Int64")
OUT_L = TAB / "2026-11-25-exp045-allocation-ladder.csv"
OUT_W = TAB / "2026-11-25-exp045-allocation-ladder-wide.csv"
for _o in (OUT_L, OUT_W):
    if _o.exists() and "--overwrite" not in sys.argv[1:]:
        print(f"{_o.name} exists, refusing to overwrite"); sys.exit(1)
L.to_csv(OUT_L, index=False)

# ---- the wide companion: the shipped summary columns, extended to the three added policies ------
P6 = S.pivot_table(index=["window", "theta", "seed"], columns="policy",
                   values=["bad_assignments_per_request", "abstention_rate", "mean_straight_line_km"])
W = []
for (w, th), g in P6.groupby(level=[0, 1]):
    bad = g["bad_assignments_per_request"]; ab = g["abstention_rate"]; km = g["mean_straight_line_km"]
    r = D[(D.window == w) & (D.theta == th)].iloc[0].to_dict()
    d_iv = 600 * (bad.POINT - bad.INTERVAL)
    r.update(d_point_minus_interval_per600_sd=d_iv.std(ddof=1),
             d_point_minus_interval_per600_se=d_iv.std(ddof=1) / np.sqrt(len(d_iv)))
    for p in REL.EXTRA_POLICIES:
        c = REL.colname(p)
        d_p = bad.POINT - bad[p]
        d_x = bad[p] - bad.INTERVAL
        r.update({f"bad_{c}": bad[p].mean(), f"d_point_minus_{c}": d_p.mean(),
                  f"seeds_sign_holds_{c}": int((d_p > 0).sum()),
                  f"rel_reduction_vs_point_{c}": float(d_p.mean() / bad.POINT.mean()) if bad.POINT.mean() else np.nan,
                  f"share_of_point_to_interval_{c}": float(d_p.mean() / d_iv.mean() * 600) if d_iv.mean() else np.nan,
                  f"d_{c}_minus_interval": d_x.mean(), f"seeds_interval_beats_{c}": int((d_x > 0).sum()),
                  f"abst_{c}": ab[p].mean(), f"km_{c}": km[p].mean()})
    W.append(r)
WD = pd.DataFrame(W).sort_values(["window", "theta"])
WD.to_csv(OUT_W, index=False)

# ---- T010 control: the unperturbed capacity row equals the ladder cell ---------------------------
CAPX = TAB / "2026-11-25-exp045-allocation-capacity.csv"
if CAPX.exists():
    C = pd.read_csv(CAPX, **RT)
    c0 = C[(C.draw == -1) & (C.metric == "bad_per600_mean")].set_index("policy").value
    l0 = L[(L.window == "weekend") & (L.day == "all") & np.isclose(L.theta, 0.90) &
           (L.metric == "bad_per600_mean")].set_index("policy").value
    dmax = float((c0 - l0.loc[c0.index]).abs().max())
    print(f"T010 CONTROL (unperturbed capacity equals the ladder, weekend 0.90): max |diff| {dmax:.3g}")
    if dmax > 1e-9:
        print("T010 CONTROL FAILED"); sys.exit(1)
else:
    print("T010 capacity table not found; run --phase cap first")

pd.set_option("display.max_rows", 2000)
pr = L[L.metric.isin(["bad_per600_mean", "extra_m", "d_bad_per600_se", "seeds_policy_better",
                      "share_of_point_to_interval_reduction", "upper_miss_assigned_mean"])]
print("\n=== LADDER (selected metrics) ===")
print(pr.to_string(index=False))
print(f"\nwrote {OUT_L.name} ({len(L)} rows) and {OUT_W.name} ({len(WD)} rows)")
