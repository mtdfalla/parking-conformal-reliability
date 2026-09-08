#!/usr/bin/env python3
"""
EXP-025 — R-Phase 3b task 4: E3 baselines rerun. Closes audit issues C07 and M02.

WHAT WAS WRONG (and what this script changes)
---------------------------------------------
C07  `2026-08-04-e3-baselines.py` lines 91-95 chunked the EnbPI test stream by a FIXED ROW COUNT
     (`steps_day` = 288 Belgrade / 20 Birmingham) and then fed the WHOLE chunk to `m.update()`.
     A forecast issued at test index i is only resolved at index i + h, so the last h-1 rows of every
     chunk were released with outcomes that were not yet observable (~0.7% Belgrade, ~5% Birmingham).
     The fixed row count also need not equal a real calendar day once `dropna` has run.
     -> Here the test stream is chunked by ACTUAL CALENDAR DATE, and at each chunk boundary e only rows
        i <= e - h are released. Held-back rows are carried forward, never dropped.
     Note the bias direction: the bug gave EnbPI MORE information than the protocol allows and EnbPI
     still under-covered, so fixing it can only strengthen our conclusion.

M02  The manuscript generalised one untuned Gaussian NGBoost into a claim about "parametric predictive
     distributions" as a family. One model cannot support that.
     -> `NGBoost-conformal` is added: the SAME fitted NGBoost, its central band conformalized by the CQR
        score on the calibration split. The sentence becomes a measured statement about this
        implementation ("the same model, conformalized, recovers coverage") instead of advocacy.

WHY MAPIE IS KEPT
-----------------
C07 is a defect in the UPDATE SCHEDULE, not in the estimator. Replacing MAPIE with a hand-written EnbPI
would (a) forfeit "EnbPI = the reference implementation", which is the defence against a misimplemented-
baseline objection (the same reasoning that kept SPCI cited-not-run, D-011), and (b) destroy
attributability, because an independent reimplementation could never reproduce the archived 0.8874.
The fix is to call `update()` correctly.

THE CONTROLLED DESIGN (why there are three arms)
------------------------------------------------
The corrected headline run changes TWO things at once relative to the archive: the chunking (C07) and the
feature table (v1 -> v2, i.e. the S01/S02 fixes). Lesson B6 says hold everything else fixed so a delta is
attributable, so the arms separate them:

  A12_v1_paired    v1 features. BOTH chunking schemes are run on ONE fitted model per facility, so the
                   old-vs-new delta is paired within facility and carries no fit-to-fit variation at
                   all: it is attributable to the release schedule and to nothing else. Emits
                   `EnbPI-oldchunk` (== the archived protocol) and `EnbPI-daychunk` (C07 fixed).
  A3_v2_daychunk   v2 features + use_{H}, calendar-day chunks, matured only. All four baselines.
                   A12's daychunk arm -> A3 isolates the remaining change, the v1 -> v2 data fix.
                   A3 is the number that goes in the paper.

`EnbPI-oldchunk` is additionally checked against the archived CSV. If it does not match, the cause is
MAPIE's version having never been pinned (`requirements.txt` says only `mapie>=0.8`) -- a real finding for
R-Phase 6 -- and the C07 delta is STILL clean, because both schemes share one fitted model by
construction.

PROTOCOL NOTES
--------------
* Every conformal primitive comes from `core.py` (C01 order statistic, C02 projected state, C06 delayed
  release). The archived `aci_delayed_bounds` used the np.quantile path and is NOT reused.
* Delay h is counted in STREAM STEPS after filtering, the convention `core.adaptive_conformal_stream`
  and every other R-Phase 3b script uses.
* AgACI-style keeps its ARCHIVED gamma grid, not `core.GAMMA_GRID`: the baseline's whole point is
  aggregating over a grid rather than selecting on one, so changing the grid would confound the
  baseline with the fix.
* Learner hyperparameters are held at the ARCHIVED values (B6): RF n_estimators=100 min_samples_leaf=2,
  NGBoost n_estimators=300 lr=0.03, BlockBootstrap 30x10, seed 42.
* Bootstrap CIs use `core.moving_block_bootstrap_ci` with B=10,000 and a CADENCE-DERIVED block (audit
  I06), replacing the archived B=500 / fixed 20-row block. PICP/MPIW/Winkler do not depend on this, so
  the A1 reproduction check is unaffected.
* All facilities are evaluated and tagged `dynamic` rather than filtered up front (D05), and a
  `degenerate` flag records an all-zero calibration score pool (lesson B5).

USAGE
-----
  python 2026-09-03-e3-baselines.py --dataset belgrade   --arm A3_v2_daychunk --budget 150
  python 2026-09-03-e3-baselines.py --dataset belgrade   --witness 2
Resumable: re-run the same command until it prints ALL DONE.
"""
from __future__ import annotations
import argparse, copy, sys, time, warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from mapie.regression import TimeSeriesRegressor
from mapie.subsample import BlockBootstrap
from ngboost import NGBRegressor
from ngboost.distns import Normal
from scipy.stats import norm

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
import core  # noqa: E402

PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"

SEED = 42
DYN = 5.0
LVL = 0.90
AL = 1.0 - LVL
AGACI_GAMMAS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]   # archived grid, deliberately unchanged

CFG = {
    "belgrade":   {"v1": "belgrade_features.parquet",   "v2": "belgrade_features_v2.parquet",
                   "hz": "y_t+15min", "h": 3, "steps_day": 288, "use": "use_15", "cadence": 5.0},
    "birmingham": {"v1": "birmingham_features.parquet", "v2": "birmingham_features_v2.parquet",
                   "hz": "y_t+60min", "h": 2, "steps_day": 20,  "use": "use_60", "cadence": 30.0},
}
ARMS = ("A12_v1_paired", "A3_v2_daychunk")


def log(m): print(f"[e3] {m}", flush=True)


def flush(out_path: Path, rows: list) -> None:
    """Append completed rows immediately. Each device_bash call is capped at ~180 s, so a facility that
    overruns must not take the whole call's finished work with it (lesson A1)."""
    if not rows:
        return
    rd = pd.DataFrame(rows)
    if out_path.exists():
        rd = pd.concat([pd.read_csv(out_path), rd], ignore_index=True)
    rd.to_csv(out_path, index=False)


# ---------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------

# Chunking and the maturity rule live in core.py under the property gate (P18-P21), so the streaming
# and batch paths share ONE definition of "matured" rather than a second convention living here.
fixed_chunks = core.fixed_row_chunks          # the ARCHIVED scheme, kept to measure the C07 delta
day_chunks = core.calendar_day_chunks         # the C07 fix


def enbpi_mapie(X_tr, d_tr, X_te, occ_te, y_te, *, chunks, h, mature, fitted=None):
    """EnbPI (MAPIE reference implementation) with an explicit release schedule.

    mature=False reproduces the archived behaviour: the whole chunk is released, so the last h-1 rows of
    every chunk carry outcomes that are not yet observable (C07).
    mature=True releases, at each chunk boundary e, only rows i <= e - h -- the same maturity rule
    `core.ReleaseQueue` enforces for the adaptive methods. Held-back rows carry forward.
    """
    if fitted is None:
        est = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
        cv = BlockBootstrap(n_resamplings=30, n_blocks=10, overlapping=False, random_state=SEED)
        m = TimeSeriesRegressor(estimator=est, method="enbpi", cv=cv, agg_function="mean",
                                n_jobs=-1, random_state=SEED)
        m.fit(X_tr, d_tr)
    else:
        m = copy.deepcopy(fitted)

    n = len(y_te)
    lo = np.empty(n); hi = np.empty(n)
    released = 0                       # test rows already handed to update()
    for (s, e) in chunks:
        _, ps = m.predict(X_te[s:e], ensemble=True, confidence_level=LVL)
        lo[s:e] = occ_te[s:e] + ps[:, 0, 0]
        hi[s:e] = occ_te[s:e] + ps[:, 1, 0]
        rel_end = e if not mature else core.matured_release_end(e, h, released, n)
        if rel_end > released:
            m.update(X_te[released:rel_end], y_te[released:rel_end] - occ_te[released:rel_end],
                     ensemble=True, confidence_level=LVL)
            released = rel_end
    return lo, hi


# ---------------------------------------------------------------------------
# the other baselines
# ---------------------------------------------------------------------------

def pinball(y, b, tau):
    d = y - b
    return np.maximum(tau * d, (tau - 1.0) * d)


def agaci_ewa(resid_cal, yhat, y, alpha, h, eta=0.01):
    """EWA aggregation of delay-aware ACI experts over the archived gamma grid.

    Experts now come from `core.adaptive_conformal_stream` (C01/C02/C06 correct) instead of the retired
    `aci_delayed_bounds`. The weight schedule is unchanged and is causal: the loss of the forecast issued
    at j is added at the END of step i = j + h - 1, so it first influences the weights at step j + h,
    which is exactly when y[j] becomes observable.
    """
    K, n = len(AGACI_GAMMAS), len(y)
    LOs = np.empty((K, n)); HIs = np.empty((K, n))
    for k, g in enumerate(AGACI_GAMMAS):
        LOs[k], HIs[k] = core.adaptive_conformal_stream(
            resid_cal, yhat, yhat, y, alpha, h, gamma=g, clip_low=None)
    lo = np.empty(n); hi = np.empty(n)
    Llo = np.zeros(K); Lhi = np.zeros(K)
    for i in range(n):
        wlo = np.exp(-eta * (Llo - Llo.min())); wlo /= wlo.sum()
        whi = np.exp(-eta * (Lhi - Lhi.min())); whi /= whi.sum()
        lo[i] = float(wlo @ LOs[:, i]); hi[i] = float(whi @ HIs[:, i])
        j = i - h + 1
        if j >= 0:
            Llo += pinball(y[j], LOs[:, j], alpha / 2.0)
            Lhi += pinball(y[j], HIs[:, j], 1.0 - alpha / 2.0)
    return lo, hi


def fit_ngboost(X_tr, d_tr):
    # 2026-09-05 (revision 44, EXP-033): `random_state` does NOT determine an NGBoost fit in
    # ngboost 0.5.11 -- the estimator consumes the GLOBAL numpy RNG. Two consecutive fits in one
    # process on identical data differ by up to 1.3 cars in the predicted mean, and a fit preceded by
    # a different amount of global-RNG consumption -- i.e. a different RESUME BOUNDARY, which this
    # script produces by design (A1) -- differs by 1.9 cars. Seeding the global RNG immediately
    # before each fit makes them bit-identical (max |delta| = 0.0 on both `loc` and `scale`).
    # Measured in `05_results/tables/2026-09-05-ngboost-determinism-probe.csv`; lesson A18;
    # prespecified in `04_experiments/2026-09-05-ngboost-seeding-PRESPECIFICATION.md`.
    # The seed is placed INSIDE this function so it cannot be separated from the fit it protects.
    np.random.seed(SEED)
    ng = NGBRegressor(Dist=Normal, n_estimators=300, learning_rate=0.03,
                      random_state=SEED, verbose=False)
    ng.fit(X_tr, d_tr)
    return ng


def ngboost_band(ng, X, occ, alpha):
    """Central (1-alpha) band of the fitted predictive Normal, on the occupancy scale."""
    dist = ng.pred_dist(X)
    z = norm.ppf(1.0 - alpha / 2.0)
    mu = dist.params["loc"]; sd = dist.params["scale"]
    return occ + mu - z * sd, occ + mu + z * sd


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

FEAT_EXTRA = ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]


def load(dataset: str, arm: str):
    cfg = CFG[dataset]
    path = PROC / (cfg["v1"] if arm.startswith("A12") else cfg["v2"])
    df = pd.read_parquet(path)
    if arm.startswith("A3"):
        df = df[df[cfg["use"]].astype(bool)].copy()      # S01 embargo / same-split targets
    feats = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + FEAT_EXTRA
    return df, feats, cfg, path.name


def facility_frame(df, feats, fid, hz):
    g = (df[df.facility_id == fid]
         .sort_values("timestamp")
         .dropna(subset=["occupancy"] + feats + [hz]))
    return g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]


# ---------------------------------------------------------------------------
# the no-lookahead witness (audit C07 asks for ONE test applied uniformly to every method)
# ---------------------------------------------------------------------------

def adversarial_probe(chunks, h, n):
    """The row where C07 actually bites: the LAST row of an interior chunk.

    Its outcome matures at t + h, which is AFTER that chunk's boundary, so a scheme that releases the
    whole chunk leaks it. A probe in the middle of a chunk cannot detect this -- the first version of
    this witness used t = n // 2 and reported a false PASS for the archived scheme.
    """
    interior = chunks[1:-1] or chunks
    for (s_, e_) in interior:
        if 0 < e_ - 1 < n and e_ < n:
            return e_ - 1
    return n // 2


def witness(dataset: str, fid: int, arm: str = "A3_v2_daychunk"):
    """Perturb one test outcome and locate the FIRST index at which any bound moves.

    A causal method cannot let y[t] influence a bound before t + h. This is a black-box test on the
    script's exact call path, so it applies uniformly to MAPIE and to our own code -- which an internal
    property test could not do (audit C07 asks for exactly one such test across every method).

    Two things this witness gets right that a naive version does not:
      1. The tolerance is MEASURED. A replicate on identical input exposes this path's own
         nondeterminism (MAPIE aggregates 30 bootstrap models under n_jobs=-1; thread reduction order
         moves bounds at ~1e-14, lesson A8). Comparing at bit equality reports that noise as a lookahead.
      2. The probe is ADVERSARIAL. C07 leaks only the last h-1 rows of a chunk, so the probe is placed
         at an interior chunk boundary, per scheme.
    """
    df, feats, cfg, src = load(dataset, arm)
    hz, h = cfg["hz"], cfg["h"]
    tr, ca, te = facility_frame(df, feats, fid, hz)
    X_tr, d_tr = tr[feats].values, tr[hz].values - tr.occupancy.values
    X_ca, X_te = ca[feats].values, te[feats].values
    occ_ca, occ_te = ca.occupancy.values, te.occupancy.values
    y_te = te[hz].values.astype(float)
    n = len(y_te)
    log(f"witness: {dataset} fac {fid} arm {arm} src={src} n_test={n} h={h}")

    rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
    rf.fit(X_tr, d_tr)
    yhat_te = occ_te + rf.predict(X_te)
    resid = np.abs(ca[hz].values - (occ_ca + rf.predict(X_ca)))

    def maxdiff(a, b):
        return float(max(np.max(np.abs(a[0] - b[0])), np.max(np.abs(a[1] - b[1]))))

    def first_div_tol(a, b, tol):
        d = np.flatnonzero((np.abs(a[0] - b[0]) > tol) | (np.abs(a[1] - b[1]) > tol))
        return int(d[0]) if len(d) else None

    def perturb(t):
        yp = y_te.copy(); yp[t] += 25.0; return yp

    est = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
    cv = BlockBootstrap(n_resamplings=30, n_blocks=10, overlapping=False, random_state=SEED)
    base = TimeSeriesRegressor(estimator=est, method="enbpi", cv=cv, agg_function="mean",
                               n_jobs=-1, random_state=SEED)
    base.fit(X_tr, d_tr)
    dch = day_chunks(te.timestamp.values)
    fch = fixed_chunks(n, cfg["steps_day"])

    def run_enbpi(y, chunks, mature):
        return enbpi_mapie(X_tr, d_tr, X_te, occ_te, y, chunks=chunks, h=h, mature=mature, fitted=base)

    cases = [
        ("EnbPI calendar-day + matured [THE FIX]", dch,
         lambda y: run_enbpi(y, dch, True),  False),
        ("EnbPI fixed-row + immature [ARCHIVED]", fch,
         lambda y: run_enbpi(y, fch, False), True),
        ("AgACI-style (core.py recursion)",       dch,
         lambda y: agaci_ewa(resid, yhat_te, y, AL, h), False),
    ]

    print(f"\n  chunk boundaries: calendar-day {[e for _, e in dch][:6]} | "
          f"fixed-row {[e for _, e in fch][:6]}")
    ok_all = True
    for name, chunks, run, expected_fail in cases:
        a = run(y_te); a2 = run(y_te)
        noise = maxdiff(a, a2)
        tol = max(1e-9, 100.0 * noise)
        probes = sorted({n // 2, adversarial_probe(chunks, h, n)})
        print(f"\n   {name}   [noise floor {noise:.3e}, tol {tol:.3e}]")
        for t in probes:
            b = run(perturb(t))
            fd = first_div_tol(a, b, tol)
            kind = "adversarial (last row of a chunk)" if t == adversarial_probe(chunks, h, n) \
                   else "mid-chunk"
            if fd is None:
                verdict, ok = "no divergence", True
            elif fd >= t + h:
                verdict, ok = f"first divergence {fd} >= t+h={t + h}", True
            else:
                verdict, ok = f"first divergence {fd} < t+h={t + h}  *** LOOKAHEAD ***", False
            ok_all &= (ok or expected_fail)
            tag = "PASS" if ok else ("FAIL(expected)" if expected_fail else "FAIL")
            print(f"      {tag:14s} t={t:5d} {kind:34s} {verdict}"
                  f"  [effect {maxdiff(a, b):.3e}]")

    print("\n  NGBoost / NGBoost-conformal are fit on train and calibration only and never read a test "
          "outcome, so they cannot leak by construction.")
    print("  Expected: the FIX passes at BOTH probes; the ARCHIVED scheme fails at the adversarial "
          "probe -- that failure IS audit issue C07.")
    return ok_all


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(CFG))
    ap.add_argument("--arm", default="A3_v2_daychunk", choices=list(ARMS))
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--witness", type=int, default=None)
    a = ap.parse_args()

    if a.witness is not None:
        ok = witness(a.dataset, a.witness)
        sys.exit(0 if ok else 1)

    arm, cfg = a.arm, CFG[a.dataset]
    df, feats, cfg, src = load(a.dataset, arm)
    hz, h = cfg["hz"], cfg["h"]
    block = core.block_length_for_cadence(cfg["cadence"], 3.0)

    ds = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    dynamic = set(ds[ds >= DYN].index)
    # A1/A2 are the attribution control for EnbPI only, on the archived (dynamic) facility set.
    facs = sorted(dynamic) if arm.startswith("A12") else sorted(df.facility_id.unique())

    OUT = TAB / f"2026-09-03-e3-{a.dataset}-per-facility.csv"
    prev = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["arm", "facility_id"])
    done = set(prev[prev.arm == arm].facility_id.unique()) if len(prev) else set()
    todo = [f for f in facs if f not in done]
    log(f"{a.dataset} arm={arm} src={src} hz={hz} h={h} block={block}: "
        f"{len(done)} done, {len(todo)} to do")

    t0 = time.time(); rows = []
    for fid in todo:
        if time.time() - t0 > a.budget:
            log("budget hit; save + exit"); break
        tr, ca, te = facility_frame(df, feats, fid, hz)
        if len(tr) < 50 or len(ca) < 50 or len(te) < 10:
            rows.append(dict(arm=arm, dataset=a.dataset, facility_id=fid, horizon=hz, level=LVL,
                             method="SKIPPED-insufficient-rows", PICP=np.nan, MPIW=np.nan,
                             Winkler=np.nan, picp_lo=np.nan, picp_hi=np.nan, n_test=len(te),
                             dynamic=fid in dynamic, degenerate=False, cal_score_max=np.nan))
            flush(OUT, rows); rows = []
            log(f"fac {fid}: SKIPPED (train={len(tr)} cal={len(ca)} test={len(te)})")
            continue

        X_tr, d_tr = tr[feats].values, tr[hz].values - tr.occupancy.values
        X_ca, X_te = ca[feats].values, te[feats].values
        occ_ca, occ_te = ca.occupancy.values, te.occupancy.values
        y_ca, y_te = ca[hz].values.astype(float), te[hz].values.astype(float)
        n = len(y_te)

        rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1, random_state=SEED)
        rf.fit(X_tr, d_tr)
        yhat_te = occ_te + rf.predict(X_te)
        resid = np.abs(y_ca - (occ_ca + rf.predict(X_ca)))
        degenerate = bool(np.max(resid) <= 0.0)

        res = {}
        failed = {}
        if arm == "A12_v1_paired":
            est = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                                        random_state=SEED)
            cv = BlockBootstrap(n_resamplings=30, n_blocks=10, overlapping=False, random_state=SEED)
            shared = TimeSeriesRegressor(estimator=est, method="enbpi", cv=cv, agg_function="mean",
                                         n_jobs=-1, random_state=SEED)
            shared.fit(X_tr, d_tr)   # ONE fit; both schemes deepcopy it -> paired, no fit variation
            res["EnbPI-oldchunk"] = enbpi_mapie(X_tr, d_tr, X_te, occ_te, y_te,
                                                chunks=fixed_chunks(n, cfg["steps_day"]),
                                                h=h, mature=False, fitted=shared)
            res["EnbPI-daychunk"] = enbpi_mapie(X_tr, d_tr, X_te, occ_te, y_te,
                                                chunks=day_chunks(te.timestamp.values),
                                                h=h, mature=True, fitted=shared)
        else:
            res["EnbPI"] = enbpi_mapie(X_tr, d_tr, X_te, occ_te, y_te,
                                       chunks=day_chunks(te.timestamp.values), h=h, mature=True)
            res["AgACI-style"] = agaci_ewa(resid, yhat_te, y_te, AL, h)
            # NGBoost maximises a Gaussian likelihood, so a facility whose training target is
            # (near-)constant drives the fitted scale to zero and the gradients to NaN. Belgrade
            # facility 1 is exactly that case (lesson B5). Record the failure per method instead of
            # aborting the run: "the parametric baseline cannot be fitted here at all, while the
            # conformal methods still return a valid interval" is itself a reportable result, and a
            # silently absent row would corrupt the D05 all-facility sensitivity.
            ng = None
            try:
                ng = fit_ngboost(X_tr, d_tr)
            except Exception as exc:
                failed["NGBoost"] = f"{type(exc).__name__}: {str(exc)[:80]}"
                failed["NGBoost-conformal"] = failed["NGBoost"]
                log(f"fac {fid}: NGBoost FAILED TO FIT -> {failed['NGBoost']}")
            if ng is not None:
                res["NGBoost"] = ngboost_band(ng, X_te, occ_te, AL)
                qlo_ca, qhi_ca = ngboost_band(ng, X_ca, occ_ca, AL)
                qlo_te, qhi_te = ngboost_band(ng, X_te, occ_te, AL)
                cal_scores = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)   # CQR score (M02)
                res["NGBoost-conformal"] = core.cqr_interval(cal_scores, qlo_te, qhi_te, AL,
                                                             clip_low=0.0)
            # B8 cross-check: this script's ACI must reproduce the canonical runner.
            gam, _ = core.select_gamma_on_calibration(
                resid, occ_ca + rf.predict(X_ca), occ_ca + rf.predict(X_ca), y_ca, AL, h)
            res["ACI-crosscheck"] = core.adaptive_conformal_stream(
                resid, yhat_te, yhat_te, y_te, AL, h, gamma=gam, clip_low=0.0)

        for meth, why in failed.items():
            rows.append(dict(arm=arm, dataset=a.dataset, facility_id=fid, horizon=hz, level=LVL,
                             method=meth, PICP=np.nan, MPIW=np.nan, Winkler=np.nan,
                             picp_lo=np.nan, picp_hi=np.nan, n_test=n,
                             dynamic=fid in dynamic, degenerate=degenerate,
                             cal_score_max=float(np.max(resid)), status=f"FAILED {why}"))
        for meth, (lo, hi) in res.items():
            lo = np.maximum(np.asarray(lo, float), 0.0); hi = np.asarray(hi, float)
            picp, mpiw, wink = core.interval_metrics(y_te, lo, hi, AL)
            cov = ((y_te >= lo) & (y_te <= hi)).astype(float)
            clo, chi = core.moving_block_bootstrap_ci(cov, B=10_000, block=block, seed=SEED, level=0.90)
            rows.append(dict(arm=arm, dataset=a.dataset, facility_id=fid, horizon=hz, level=LVL,
                             method=meth, PICP=picp, MPIW=mpiw, Winkler=wink,
                             picp_lo=clo, picp_hi=chi, n_test=n,
                             dynamic=fid in dynamic, degenerate=degenerate,
                             cal_score_max=float(np.max(resid)), status="ok"))
        flush(OUT, rows); rows = []
        log(f"fac {fid} done ({time.time() - t0:.0f}s, {len(res)} methods)")

    flush(OUT, rows); rows = []

    cur = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["arm", "facility_id"])
    have = set(cur[cur.arm == arm].facility_id.unique()) if len(cur) else set()
    rem = [f for f in facs if f not in have]
    if rem:
        log(f"REMAINING {a.dataset} {arm}: {len(rem)}")
    else:
        log(f"ALL DONE {a.dataset} {arm}: {len(have)} facilities")
        d = cur[(cur.arm == arm) & (~cur.method.astype(str).str.startswith("SKIPPED"))]
        if "status" in d.columns:
            d = d[d.status.astype(str).isin(["ok", "nan"])]   # A12 rows predate the column
        d = d[d.dynamic.astype(bool) & ~d.degenerate.astype(bool)]
        print(d.groupby("method").agg(n=("PICP", "size"), mean_PICP=("PICP", "mean"),
                                      std_PICP=("PICP", "std"), mean_MPIW=("MPIW", "mean"),
                                      mean_Winkler=("Winkler", "mean")).round(4).to_string())


if __name__ == "__main__":
    main()
