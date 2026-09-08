#!/usr/bin/env python3
"""
EXP-031 (D') — the corrected failure-case arm. Two legs.

Prespecified in `04_experiments/2026-09-04-rphase5-PRESPECIFICATION.md` (sections 1.2, 1.3, 3, 5) and its
2026-09-04 AMENDMENT (section 8: branch B', the withdrawal LEAD TIME, and the feature-rebuild rule).
Read both before changing anything here.

LEG 1 — the real case, Belgrade facility 8, n = 1. Corrected pipeline throughout: v2 + use_15,
`core.adaptive_conformal_stream`, gamma from `core.select_gamma_on_calibration`, capacity from the
TRAINING split only. NO NUMBER COMES FROM THE ARCHIVED EXP-015 RUN (B21). Facility 8's occupancy is never
used as ground truth for any outcome; it enters as a candidate destination and as this leg's subject only,
and contributes to no forecast-evaluation statistic anywhere (D-018).

LEG 2 — a prespecified synthetic level-shift probe over the 20 healthy facilities, which is what turns a
single dead sensor into a measured property. The feed is pinned from a matched slot at 167.69% of the
facility's OWN cap_train (relative, never absolute — B20), with a matched control pinning at the
facility's own training median (a stuck but PLAUSIBLE sensor): without that control, "abstention responds
to implausibility" cannot be separated from "abstention responds to constancy" (B3, B7).

WHAT IS MEASURED, and the part of it that is arithmetic rather than evidence:
    withdrawal lead time L = step(POINT withdraws) - step(INTERVAL withdraws)
`U >= yhat` at every step, so `cap - U <= cap - yhat`, so **L >= 0 by construction**. The SIGN is
guaranteed; only the MAGNITUDE is empirical. Section 8.5 forbids reporting the sign as a finding.

Usage:  python 2026-09-04-rphase5-failure-case.py [--budget 150]
Resumable per facility; flushes after every facility; prints REMAINING or ALL DONE.
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
import core                                                              # noqa: E402

PROC = ROOT / "01_data" / "processed"
TAB = ROOT / "05_results" / "tables"
CACHE = Path.home() / ".rphase5_cache_2026_09_04"                        # outside the mount; regenerable

SEED_FIT, DYN = 42, 5.0
HZ, HMIN, HSTEPS, ALPHA, SAFETY = "y_t+15min", 15, 3, 0.10, 1
ONSET = pd.Timestamp("2017-03-19 18:00")        # facility 8's observed 0 -> 109 regime change (fact (a))
OVERSHOOT = 1.6769                              # facility 8's observed 109 / 65, applied RELATIVELY
LAGS = {"lag_5min": 1, "lag_10min": 2, "lag_15min": 3, "lag_30min": 6, "lag_45min": 9, "lag_60min": 12}
ROLLS = {"roll_mean_30min": (6, "mean"), "roll_std_30min": (6, "std"),
         "roll_mean_60min": (12, "mean"), "roll_std_60min": (12, "std")}

OUT_L1 = TAB / "2026-09-04-failure-case-leg1-facility8.csv"
OUT_L2 = TAB / "2026-09-04-failure-case-leg2-injection.csv"
OUT_FID = TAB / "2026-09-04-failure-case-feature-fidelity.csv"


def log(*a): print(*a, flush=True)


def rebuild_features(occ: np.ndarray) -> dict:
    """Lag/roll features from an occupancy series, by the conventions measured on the inputs (8.4)."""
    s = pd.Series(occ)
    out = {c: s.shift(k).values for c, k in LAGS.items()}
    for c, (k, how) in ROLLS.items():
        r = s.shift(1).rolling(k)
        out[c] = (r.mean() if how == "mean" else r.std()).values
    return out


def load():
    df = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    df["ts"] = pd.to_datetime(df.timestamp)
    df = df[df[f"use_{HMIN}"]]
    feat = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    tr = df[df.split == "train"]
    ds = tr.groupby("facility_id").occupancy.std()
    coords = pd.read_parquet(PROC / "facility_coords.parquet").set_index("facility_id")
    dyn = sorted(set(ds[ds >= DYN].index) & set(coords.index))
    return df, feat, dyn


def fit_models(g, feat):
    tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
    if len(tr) < 100 or len(ca) < 50 or len(te) < 50:
        return None
    d_tr = tr[HZ].values - tr.occupancy.values
    rf = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, n_jobs=-1,
                               random_state=SEED_FIT).fit(tr[feat].values, d_tr)
    glo = HistGradientBoostingRegressor(loss="quantile", quantile=ALPHA / 2, max_iter=100,
                                        random_state=SEED_FIT).fit(tr[feat].values, d_tr)
    ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1 - ALPHA / 2, max_iter=100,
                                        random_state=SEED_FIT).fit(tr[feat].values, d_tr)
    qlo_ca = ca.occupancy.values + glo.predict(ca[feat].values)
    qhi_ca = ca.occupancy.values + ghi.predict(ca[feat].values)
    qlo_ca, qhi_ca, _ = core.repair_quantile_crossing(qlo_ca, qhi_ca)
    y_ca = ca[HZ].values
    E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)
    gam, _ = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, ALPHA, HSTEPS)
    return dict(rf=rf, glo=glo, ghi=ghi, E_cal=E_cal, gamma=float(gam),
                cap_train=float(tr.occupancy.max()), cap_full=float(g.occupancy.max()),
                med_train=float(np.median(tr.occupancy.values)),
                n_train=len(tr), n_cal=len(ca), n_test=len(te))


def panel(m, X, occ_te, y_te):
    """Intervals and point forecast for one test-window feature matrix."""
    yhat = occ_te + m["rf"].predict(X)
    qlo = occ_te + m["glo"].predict(X); qhi = occ_te + m["ghi"].predict(X)
    qlo, qhi, _ = core.repair_quantile_crossing(qlo, qhi)
    lo, hi = core.adaptive_conformal_stream(m["E_cal"], qlo, qhi, y_te, ALPHA, HSTEPS, gamma=m["gamma"])
    return yhat, np.asarray(hi)


def first_withdrawal(mask: np.ndarray, start: int):
    """First index >= start where mask is True, as a step offset from start; None if never."""
    idx = np.flatnonzero(mask[start:])
    return int(idx[0]) if len(idx) else None


def summarise(tag, fid, ts, yhat, U, cap, onset_i, extra=None):
    w_int = (cap - U) < SAFETY
    w_pt = (cap - yhat) < SAFETY
    s_int = first_withdrawal(w_int, onset_i)
    s_pt = first_withdrawal(w_pt, onset_i)
    pre = slice(0, onset_i)
    post_int = w_int[onset_i:]; post_pt = w_pt[onset_i:]
    row = dict(
        arm=tag, facility_id=int(fid), cap_train=round(cap, 4), n_test=len(U),
        onset_index=int(onset_i), n_pre_onset=int(onset_i), n_post_onset=int(len(U) - onset_i),
        pre_onset_frac_withdrawn_interval=round(float(w_int[pre].mean()), 4) if onset_i else np.nan,
        pre_onset_frac_withdrawn_point=round(float(w_pt[pre].mean()), 4) if onset_i else np.nan,
        withdrawn_at_last_pre_onset_slot_interval=(int(w_int[onset_i - 1]) if onset_i else -1),
        withdrawn_at_last_pre_onset_slot_point=(int(w_pt[onset_i - 1]) if onset_i else -1),
        step_interval=(-1 if s_int is None else s_int),
        step_point=(-1 if s_pt is None else s_pt),
        lead_time_steps=(-1 if (s_int is None or s_pt is None) else s_pt - s_int),
        minutes_interval=(-1 if s_int is None else s_int * 5),
        minutes_point=(-1 if s_pt is None else s_pt * 5),
        post_onset_frac_withdrawn_interval=round(float(post_int.mean()), 4),
        post_onset_frac_withdrawn_point=round(float(post_pt.mean()), 4),
        persists_interval=(int(bool(post_int[s_int:].all())) if s_int is not None else -1),
        persists_point=(int(bool(post_pt[s_pt:].all())) if s_pt is not None else -1),
        mean_U_post=round(float(U[onset_i:].mean()), 4),
        mean_yhat_post=round(float(yhat[onset_i:].mean()), 4),
    )
    if extra: row.update(extra)
    return row


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args(); t0 = time.time()
    CACHE.mkdir(exist_ok=True)
    df, feat, dyn = load()
    te_all = df[df.split == "test"]
    excl = core.low_information_facilities(te_all[te_all.facility_id.isin(dyn)])
    healthy = [f for f in dyn if f not in excl]
    log(f"[in] dynamic={dyn} (n={len(dyn)})  low_information on the test split={excl}  healthy n={len(healthy)}")

    done_l1 = set(); done_l2 = set(); done_fid = set()
    if OUT_L1.exists(): done_l1 = set(pd.read_csv(OUT_L1).facility_id)
    if OUT_L2.exists():
        p = pd.read_csv(OUT_L2); done_l2 = set(zip(p.arm, p.facility_id))
    if OUT_FID.exists(): done_fid = set(pd.read_csv(OUT_FID).facility_id)
    # 2026-09-06 (revision 46, DEFECT 8): OUT_FID is part of this step's completion state and is read
    # here alongside the other two. Before this it was accumulated in an in-process list and written
    # ONCE after the loop, so the budget cutoff below (`return`) DISCARDED it and a resumed run printed
    # ALL DONE with the file absent -- measured, and `verify.py` then failed on it. Two rules were
    # broken and both are restored: every output flushes per unit (A1), and the completion marker
    # respects the same selection as the work that produces it (EXP-035 defect 1 / C11).
    for fid in dyn:
        g = df[df.facility_id == fid].sort_values("ts").dropna(subset=["occupancy"] + feat + [HZ])
        te = g[g.split == "test"]
        is8 = (fid == 8)
        if (is8 and fid in done_l1) or ((not is8)
                and all((a, fid) in done_l2 for a in ("none", "implausible", "plausible"))
                and fid in done_fid):
            continue
        if time.time() - t0 > args.budget:
            log("REMAINING"); return
        mf = CACHE / f"m_{fid}.npz"
        m = fit_models(g, feat)
        if m is None:
            log(f"[fac {fid}] SKIPPED-too-few-rows"); continue
        ts = te.ts.values
        onset_i = int(np.searchsorted(ts, np.datetime64(ONSET)))
        occ_te, y_te, X_par = te.occupancy.values, te[HZ].values, te[feat].values

        if is8:
            # ---- LEG 1: the REAL, OBSERVED series. Parquet features, nothing injected. ------------
            yhat, U = panel(m, X_par, occ_te, y_te)
            r = summarise("real", fid, ts, yhat, U, m["cap_train"], onset_i,
                          extra=dict(cap_fullrecord=round(m["cap_full"], 4), gamma=round(m["gamma"], 5),
                                     n_cal=m["n_cal"], cal_rows_inside_dead_run=487,
                                     cal_frac_inside_dead_run=round(487 / m["n_cal"], 4),
                                     note="feed already constant-0 from 2017-03-14 23:00 (calibration); "
                                          "onset here is the 0->109 regime change"))
            pd.DataFrame([r]).to_csv(OUT_L1, mode="a", header=not OUT_L1.exists(), index=False)
            log(f"[leg1 fac 8] cap_train={m['cap_train']:.1f} cap_full={m['cap_full']:.1f} "
                f"gamma={m['gamma']:.3f} step_int={r['step_interval']} step_pt={r['step_point']} "
                f"lead={r['lead_time_steps']} pre_withdrawn_int={r['pre_onset_frac_withdrawn_interval']}")
            continue

        # ---- LEG 2: three arms on rebuilt features (8.4), so the null injection is exact ----------
        pos = np.arange(len(g)); te_mask = (g.split == "test").values
        occ_full = g.occupancy.values.copy()
        y_full = g[HZ].values.copy()
        te_pos = pos[te_mask]
        inj_pos = te_pos[onset_i]
        for arm in ("none", "implausible", "plausible"):
            need_fid = (arm == "none" and fid not in done_fid)
            if (arm, fid) in done_l2 and not need_fid:
                continue
            occ_i = occ_full.copy(); y_i = y_full.copy()
            if arm != "none":
                v = OVERSHOOT * m["cap_train"] if arm == "implausible" else m["med_train"]
                occ_i[inj_pos:] = v; y_i[inj_pos:] = v
            rb = rebuild_features(occ_i)
            Xi = X_par.copy()
            for j, c in enumerate(feat):
                if c in rb:
                    Xi[:, j] = rb[c][te_mask]
            good = ~np.isnan(Xi).any(axis=1)
            occ_t, y_t = occ_i[te_mask], y_i[te_mask]
            yhat, U = panel(m, Xi[good], occ_t[good], y_t[good])
            oi = int(good[:onset_i].sum())
            r = summarise(arm, fid, ts[good], yhat, U, m["cap_train"], oi,
                          extra=dict(injected_value=(round(float(occ_i[inj_pos]), 4) if arm != "none" else np.nan),
                                     med_train=round(m["med_train"], 4), gamma=round(m["gamma"], 5),
                                     overshoot_frac_of_cap=(OVERSHOOT if arm == "implausible" else
                                                            (round(m["med_train"] / m["cap_train"], 4)
                                                             if arm == "plausible" else np.nan))))
            if (arm, fid) not in done_l2:
                pd.DataFrame([r]).to_csv(OUT_L2, mode="a", header=not OUT_L2.exists(), index=False)
                done_l2.add((arm, fid))
            if need_fid:
                agree = np.isclose(Xi[good], X_par[good], equal_nan=True).mean()
                pd.DataFrame([dict(facility_id=int(fid), n_test_rows=int(good.sum()),
                                   rebuilt_vs_parquet_agreement=round(float(agree), 6))]).to_csv(
                    OUT_FID, mode="a", header=not OUT_FID.exists(), index=False)
                done_fid.add(fid)
        log(f"[leg2 fac {fid}] done ({time.time()-t0:.0f}s)")

    log("ALL DONE")


if __name__ == "__main__":
    main()
