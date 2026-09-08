#!/usr/bin/env python3
"""
R-PHASE 6 — C01 ATTRIBUTION, RE-MEASURED ON THE PUBLISHED BASE, PAIRED INSIDE ONE FIT.

Prespecified in `04_experiments/2026-09-04-rphase6-PRESPECIFICATION.md`, section 7 option (2) and
amendment 2 (section 11), both written before this script existed.

WHY THIS EXISTS
---------------
The C01 order-statistic attribution recorded in EXP-017's prose (PICP 0.8988 -> 0.8858, MPIW -15.4%,
Winkler -7.8%, "8 Belgrade facilities") has NO CSV anywhere in the tree, and the 8 facilities are not
named — so it cannot be printed under the project's own rule, and the retired pre-C01 path cannot
reproduce it even in principle. This script replaces it with a traceable measurement on the PUBLISHED
base. It is a re-measurement, not a reproduction, and it must never be described as one.

DESIGN (amendment 2)
--------------------
* Population: Belgrade v2, `use_15`, y_t+15min, level 0.90, train-sd >= 5 minus
  `core.low_information_facilities` on the test split -> the published 21 facilities.
* ONE fit per facility (RandomForest delta model + HistGBR quantile pair), shared by both arms, so the
  delta carries no fit-to-fit or between-version variation (D-017, A13).
* The two arms differ in EXACTLY ONE LINE: `core.conformal_quantile` (the k-th order statistic) versus
  the archived `np.quantile(pool, lv, method="higher")` with `lv = min(1, k/m)`, which returns the
  (k+1)-th for k < m. The archived rule is scoped over the adaptive call ONLY, because the archived
  `run_corrected.py` computed split-CP and CQR correctly (`np.sort(...)[cq_idx(n,a)-1]`).
* Gamma is held at the corrected arm's calibration-selected value in BOTH arms (B6). The gamma the legacy
  rule would have selected is recorded and used for nothing.
* NEGATIVE CONTROL, built in: split-CP and CQR must be bit-identical across arms (B7, B11).
* GATE: the corrected arm must reproduce `2026-09-02-core-belgrade-gcal-per-facility.csv` to 4 dp for ACI
  and ACQR before any legacy number is read (B17).

Usage:  python 2026-09-04-c01-attribution.py [--budget 150]
Resumable per facility; flushes after every unit; prints REMAINING / ALL DONE (A1, A2).
Output: 05_results/tables/2026-09-04-c01-attribution.csv     (refuses to overwrite; supersede by date)
"""
from __future__ import annotations
import argparse, contextlib, math, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import core  # noqa: E402

p = HERE
while p != p.parent and not (p / "01_data").is_dir():
    p = p.parent
ROOT = p
PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"
OUT_BY_MODE = {"calibrated": TAB / "2026-09-04-c01-attribution.csv",
               "fixed": TAB / "2026-09-04-c01-attribution-gfixed.csv"}
REF = TAB / "2026-09-02-core-belgrade-gcal-per-facility.csv"

SEED = 42; N_TREES = 100; DYN = 5.0
HZ, HMIN, HSTEPS = "y_t+15min", 15, 3
LEVEL = 0.90
TOL = 5e-5           # "to 4 dp", i.e. half a unit in the 4th decimal


def log(m):
    print(f"[c01] {m}", flush=True)


# ---------------------------------------------------------------------------------------------
# The archived pre-C01 rule, transcribed from `run_corrected.py` lines 20 and 30. Kept here and
# NOWHERE else: it is a defect being measured, not a primitive, so it must never enter `core.py`.
# ---------------------------------------------------------------------------------------------
def legacy_conformal_quantile(scores, alpha: float) -> float:
    pool = np.asarray(scores, dtype=float)
    m = len(pool)
    k = min(math.ceil((m + 1) * (1.0 - alpha)), m)
    lv = min(1.0, k / m)
    return float(np.max(pool)) if lv >= 1.0 else float(np.quantile(pool, lv, method="higher"))


@contextlib.contextmanager
def archived_quantile_rule():
    """Scope the archived rule over core.conformal_quantile, then restore it unconditionally."""
    original = core.conformal_quantile
    core.conformal_quantile = legacy_conformal_quantile
    try:
        yield
    finally:
        core.conformal_quantile = original


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--gamma-mode", choices=["calibrated", "fixed"], default="calibrated",
                    help="calibrated = the published protocol (primary arm); fixed = gamma 0.05, the "
                         "retired setting, run only as the amendment-3 mechanism check")
    args = ap.parse_args()
    global OUT
    OUT = OUT_BY_MODE[args.gamma_mode]
    GATE_ON = (args.gamma_mode == "calibrated")   # the logged CSV IS the calibrated protocol

    if not REF.exists():
        sys.exit(f"[c01] reference {REF.name} missing — cannot gate. STOP.")
    ref = pd.read_csv(REF)
    ref = ref[(ref.horizon == HZ) & (np.isclose(ref.level, LEVEL))]

    df = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    low = set(core.low_information_facilities(df[df.split == "test"]))
    base = [f for f in sorted(sd.index) if sd[f] >= DYN and f not in low]
    log(f"published base = {len(base)} facilities (excluded low-information {sorted(low)})")

    done = set(pd.read_csv(OUT).facility_id.unique()) if OUT.exists() else set()
    todo = [f for f in base if f not in done]
    if done:
        log(f"resuming: {len(done)} done, {len(todo)} to do")

    t0 = time.time()
    for fid in todo:
        if time.time() - t0 > args.budget:
            log("budget hit; saving and exiting")
            break
        g = df[df.facility_id == fid].sort_values("timestamp")
        g = g[g[f"use_{HMIN}"]] if f"use_{HMIN}" in g.columns else g
        g = g.dropna(subset=["occupancy"] + FEAT + [HZ])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
            pd.DataFrame([dict(facility_id=fid, method="SKIPPED-thin")]).to_csv(
                OUT, mode="a", header=not OUT.exists(), index=False)
            log(f"  fac {fid}: too few rows — SKIPPED marker written")
            continue

        al = 1 - LEVEL
        occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
        d_tr = tr[HZ].values - occ_tr
        y_ca, y_te = ca[HZ].values, te[HZ].values

        # ---- ONE fit, shared by both arms --------------------------------------------------
        rf = RandomForestRegressor(n_estimators=N_TREES, min_samples_leaf=2, n_jobs=-1,
                                   random_state=SEED).fit(tr[FEAT].values, d_tr)
        yhat_ca = occ_ca + rf.predict(ca[FEAT].values)
        yhat_te = occ_te + rf.predict(te[FEAT].values)
        resid = np.abs(y_ca - yhat_ca)

        glo = HistGradientBoostingRegressor(loss="quantile", quantile=al / 2, max_iter=100,
                                            random_state=SEED).fit(tr[FEAT].values, d_tr)
        ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1 - al / 2, max_iter=100,
                                            random_state=SEED).fit(tr[FEAT].values, d_tr)
        qlo_ca = occ_ca + glo.predict(ca[FEAT].values); qhi_ca = occ_ca + ghi.predict(ca[FEAT].values)
        qlo_te = occ_te + glo.predict(te[FEAT].values); qhi_te = occ_te + ghi.predict(te[FEAT].values)
        qlo_ca, qhi_ca, _ = core.repair_quantile_crossing(qlo_ca, qhi_ca)
        qlo_te, qhi_te, _ = core.repair_quantile_crossing(qlo_te, qhi_te)
        E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)

        # ---- gamma: selected under the CORRECTED rule, held in both arms (B6) ---------------
        if args.gamma_mode == "calibrated":
            g_aci, _ = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca, al, HSTEPS)
            g_acqr, _ = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, al, HSTEPS)
        else:
            g_aci = g_acqr = 0.05        # the retired project-wide step size (amendment 3)
        with archived_quantile_rule():
            g_aci_leg, _ = core.select_gamma_on_calibration(resid, yhat_ca, yhat_ca, y_ca, al, HSTEPS)
            g_acqr_leg, _ = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, al, HSTEPS)

        rows = []

        def emit(method, cur, leg, extra=None):
            r = dict(facility_id=fid, horizon=HZ, level=LEVEL, method=method, n_test=len(y_te),
                     n_cal=len(y_ca),
                     PICP_corrected=cur[0], MPIW_corrected=cur[1], Winkler_corrected=cur[2],
                     PICP_legacy=leg[0], MPIW_legacy=leg[1], Winkler_legacy=leg[2],
                     d_PICP=leg[0] - cur[0], d_MPIW=leg[1] - cur[1], d_Winkler=leg[2] - cur[2],
                     rel_MPIW=(leg[1] - cur[1]) / cur[1] if cur[1] else np.nan,
                     rel_Winkler=(leg[2] - cur[2]) / cur[2] if cur[2] else np.nan)
            if extra:
                r.update(extra)
            rows.append(r)

        # ---- controls: split-CP and CQR, corrected rule in BOTH arms (archived code was correct)
        cur = core.interval_metrics(y_te, *core.split_conformal_interval(resid, yhat_te, al), al)
        emit("split-CP", cur, cur, dict(arm_role="negative-control"))
        cur = core.interval_metrics(y_te, *core.cqr_interval(E_cal, qlo_te, qhi_te, al), al)
        emit("CQR", cur, cur, dict(arm_role="negative-control"))

        # ---- treated: ACI and ACQR, one line different -------------------------------------
        cur_aci = core.interval_metrics(
            y_te, *core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, al, HSTEPS,
                                                  gamma=g_aci), al)
        cur_acqr = core.interval_metrics(
            y_te, *core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, al, HSTEPS,
                                                  gamma=g_acqr), al)
        with archived_quantile_rule():
            leg_aci = core.interval_metrics(
                y_te, *core.adaptive_conformal_stream(resid, yhat_te, yhat_te, y_te, al, HSTEPS,
                                                      gamma=g_aci), al)
            leg_acqr = core.interval_metrics(
                y_te, *core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, al, HSTEPS,
                                                      gamma=g_acqr), al)
        assert core.conformal_quantile is not legacy_conformal_quantile, "patch not restored"

        emit("ACI", cur_aci, leg_aci, dict(arm_role="treated", gamma_held=g_aci,
                                           gamma_legacy_would_select=g_aci_leg))
        emit("ACQR", cur_acqr, leg_acqr, dict(arm_role="treated", gamma_held=g_acqr,
                                              gamma_legacy_would_select=g_acqr_leg))

        # ---- GATE: corrected arm must reproduce the logged CSV to 4 dp (B17) ---------------
        for r in rows:
            if not GATE_ON:
                r["gate"] = "N/A-mechanism-arm"
                continue
            m = ref[(ref.facility_id == fid) & (ref.method == r["method"])]
            if m.empty:
                r["gate"] = "NO-REF-ROW"
                continue
            m = m.iloc[0]
            fails = []
            for q, col in (("PICP", "PICP"), ("MPIW", "MPIW"), ("Winkler", "Winkler")):
                if col in m and pd.notna(m[col]):
                    if abs(float(m[col]) - r[f"{q}_corrected"]) > TOL:
                        fails.append(f"{q} {float(m[col]):.6f} vs {r[f'{q}_corrected']:.6f}")
            r["gate"] = "PASS" if not fails else "FAIL: " + "; ".join(fails)

        out = pd.DataFrame(rows)
        if OUT.exists():
            out = pd.concat([pd.read_csv(OUT), out], ignore_index=True)
        out.to_csv(OUT, index=False)
        bad = [r["gate"] for r in rows if str(r["gate"]).startswith("FAIL")]
        log(f"  fac {fid} done ({time.time()-t0:.0f}s) gate={'FAIL' if bad else 'pass'}")
        if bad:
            log("  GATE FAILURE — stopping before any further facility is read: " + " | ".join(bad))
            sys.exit(2)

    have = set(pd.read_csv(OUT).facility_id.unique()) if OUT.exists() else set()
    rem = [f for f in base if f not in have]
    log(f"REMAINING {len(rem)}" if rem else "ALL DONE")


if __name__ == "__main__":
    main()
