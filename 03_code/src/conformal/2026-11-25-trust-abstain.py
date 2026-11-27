#!/usr/bin/env python3
"""
Trust/abstain (selective prediction) on the shared conformal core — Belgrade, t+15, 90%.

2026-11-25 successor of `2026-09-03-trust-abstain.py` (external-audit finding T024, EXP-045 arm A4). One change
in method: the cal-B replay that sets the width thresholds now seeds the score pool with `E_cal[:cut - gap]`,
gap = h - 1, as `core.select_gamma_on_calibration` does when it selects gamma. Before, it seeded with
`E_cal[:cut]`, so the last h - 1 cal-A scores, whose targets resolve inside cal-B, were in the pool at cal-B's
first step. The replay keeps the lower clip at 0 (`CLIP_LOW`), the clip of the test-time band, so thresholds
read off cal-B widths are compared with test widths built the same way. The selector replays without a clip,
which changes widths but never coverage (occupancy is never negative), so its cal-B PICP is still reproduced.
Two controls run inside the script, at every facility, and stop the run on failure:
  * replay: gamma, n_cal_b and the cal-B covered count equal `gamma`, `n_cal_b` and `gamma_calB_picp` x n_cal_b
    of the ACQR row (t+15, level 0.90) of `2026-11-22-core-belgrade-v3-gcal-per-facility.csv`;
  * clip: no lower end below CLIP_LOW on either side, read off the cal-B band and off the test band `lo_t` that
    the reported rows are computed from (revision 61: before, the test side was a second band built for the check,
    so the control could not see the test band drop its clip).
`--check-only selector` runs both controls and writes nothing. Negative controls: `--check-only old` (the
2026-09-03 replay, pool `E_cal[:cut]`) must fail the replay control, and `--check-only clipnone` (the gap rule
with clip_low=None on cal-B) and `--check-only testclipnone` (clip_low=None on the test band) must each pass the
replay control and fail the clip control.
Outputs carry 2026-11-25 names. The text below describes the 2026-09-03 run.
R-Phase 3b task 3 (D-014). Closes audit issues C03, C04 and D04. Logged as EXP-024.

WHY THIS SCRIPT EXISTS — three defects in the Table 5 pipeline
-------------------------------------------------------------
* **C03 — the published table is not produced by the method its caption names.**
  `ctr_word_prep.tex` line 282 captions Table 5 "Trust/abstain by **ACQR**-width thresholds", but
  `run_cond_trust_corrected.py` lines 55-56 take widths from `aci_delayed(...)` — plain ACI — and the
  figure axis in that same script is even labelled "ACI width" (X06). This script uses true ACQR widths:
  the adaptive recursion on CQR conformity scores over a CQR band.
* **C04 — the thresholds were not prequential.** That script replayed the calibration set through
  `aci_delayed` with the score pool initialised from the FULL calibration residual vector, so every
  calibration width was computed with the whole calibration set already in the pool. Thresholds here are
  selected on the **cal-B** segment of the same nested temporal split that
  `core.select_gamma_on_calibration` uses: cal-A seeds the pool, cal-B is replayed as a pseudo-test
  stream, thresholds are read off cal-B widths and applied UNCHANGED to test. One honest protocol now
  serves both the step size and the thresholds.
* **D04 — a real negative result was buried.** Table 5's committed-set coverage is 0.824-0.894, below
  0.90 at EVERY commit rate, while the prose says only that it "stays near 0.88". Width-based selection
  does NOT inherit marginal coverage: conditioning on a narrow interval selects exactly the rows where the
  model is confident, and confidence is not the same as calibration. This script reports that directly and
  adds the two comparators that make it interpretable rather than merely admitted:
    - **commit-all**  — the no-selection baseline (marginal ACQR coverage and MAE).
    - **random-selection** — commits a random subset at the SAME achieved rate, averaged over
      `--n-random` draws. This is the null: it must preserve marginal coverage while giving no MAE
      benefit. The gap between the width rule and random isolates how much of the accuracy gain is real
      selection, and the gap in coverage isolates the price paid for it.

Also verified here: the manuscript claims "abstentions concentrate in the volatile rush periods". That
sentence traces to no CSV, so this script records the time-of-day composition of the abstained set as a
LIFT over each bucket's base rate in test, and the claim stands or falls on it.

Usage:  python 2026-11-25-trust-abstain.py [--budget 150] [--n-random 20]
        python 2026-11-25-trust-abstain.py --check-only selector|old|clipnone|testclipnone   (controls, writes nothing)
Resumable: re-run until it prints ALL DONE. SKIPPED markers for facilities that yield nothing.
Output: 05_results/tables/2026-11-25-trust-abstain-per-facility.csv   (resumable unit)
        05_results/tables/2026-11-25-trust-abstain-summary.csv        (written when ALL DONE)
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT/"01_data"/"processed"; TAB = ROOT/"05_results"/"tables"
SEED = 42; DYN = 5.0
HZ = "y_t+15min"; HMIN = 15; HSTEPS = 3; LEVEL = 0.90; ALPHA = 1 - LEVEL
TARGETS = [round(x, 2) for x in np.arange(0.1, 1.0001, 0.1)]
BUCKETS = [("night", 0, 5), ("am_rush", 6, 9), ("midday", 10, 15),
           ("pm_rush", 16, 19), ("evening", 20, 23)]
ORDER = [b[0] for b in BUCKETS]
PER = TAB/"2026-11-25-trust-abstain-per-facility.csv"
SUM = TAB/"2026-11-25-trust-abstain-summary.csv"
GCAL = TAB/"2026-11-22-core-belgrade-v3-gcal-per-facility.csv"
CLIP_LOW = 0.0   # lower clip of BOTH the cal-B replay and the test-time band (T024 revision 2)


def log(m): print(f"[trust] {m}", flush=True)


def bucket_of(h):
    for nm, a, b in BUCKETS:
        if a <= h <= b:
            return nm
    return "night"


def write_summary(per: pd.DataFrame) -> None:
    d = per[(per.dynamic) & (per.degenerate != True) & (per.method != "SKIPPED-thin")]
    d = d.dropna(subset=["commit_rate"])
    out = []
    for meth in ["width-ACQR", "random", "commit-all"]:
        m = d[d.method == meth]
        if m.empty:
            continue
        for tgt in sorted(m.commit_target.unique()):
            s = m[m.commit_target == tgt]
            row = dict(method=meth, commit_target=tgt,
                       commit_rate=round(float(s.commit_rate.mean()), 3),
                       MAE_cars=round(float(s.MAE_cars.mean()), 3),
                       MAE_pct=round(float(s.MAE_pct.mean()), 3),
                       committed_PICP=round(float(s.committed_PICP.mean()), 4),
                       committed_MPIW=round(float(s.committed_MPIW.mean()), 2),
                       n_facilities=int(s.facility_id.nunique()))
            if meth == "width-ACQR":
                for bk in ORDER:
                    c = f"abst_lift_{bk}"
                    if c in s.columns:
                        row[c] = round(float(s[c].mean()), 3)
            out.append(row)
    pd.DataFrame(out).to_csv(SUM, index=False)
    log(f"wrote {SUM.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=150.0)
    ap.add_argument("--n-random", type=int, default=20)
    ap.add_argument("--check-only", choices=["selector", "old", "clipnone", "testclipnone"], default=None,
                    help="run the replay and clip controls alone and write nothing; old and clipnone are "
                         "negative controls")
    args = ap.parse_args()
    ref = pd.read_csv(GCAL, float_precision="round_trip")
    ref = ref[(ref.horizon == HZ) & np.isclose(ref.level, LEVEL) & (ref.method == "ACQR")].set_index("facility_id")
    n_fail = 0; n_fail_clip = 0; n_checked = 0

    df = pd.read_parquet(PROC/"belgrade_features_v2.parquet")
    FEAT = [c for c in df.columns if c.startswith(("lag_", "roll_"))] + \
           ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]
    sd = df[df.split == "train"].groupby("facility_id")["occupancy"].std()
    all_fac = sorted(sd.index)
    dyn_flag = {f: bool(sd[f] >= DYN) for f in all_fac}

    done = set(pd.read_csv(PER).facility_id.unique()) if (PER.exists() and not args.check_only) else set()
    todo = [f for f in all_fac if f not in done]
    log(f"Belgrade {HZ} @{LEVEL:.0%}: {len(done)} done, {len(todo)} to do")

    rows = []; t0 = time.time()
    for fid in todo:
        if time.time() - t0 > args.budget:
            log("budget hit; saving and exiting"); break
        g = df[df.facility_id == fid].sort_values("timestamp")
        if f"use_{HMIN}" in g.columns:
            g = g[g[f"use_{HMIN}"]]
        g = g.dropna(subset=["occupancy"] + FEAT + [HZ])
        tr, ca, te = g[g.split == "train"], g[g.split == "calibration"], g[g.split == "test"]
        if len(tr) < 100 or len(ca) < 100 or len(te) < 50:
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], method="SKIPPED-thin",
                             commit_target=np.nan, commit_rate=np.nan, MAE_cars=np.nan,
                             MAE_pct=np.nan, committed_PICP=np.nan, committed_MPIW=np.nan,
                             degenerate=np.nan))
            log(f"  fac {fid}: too few rows — skipped"); continue

        occ_tr, occ_ca, occ_te = tr.occupancy.values, ca.occupancy.values, te.occupancy.values
        d_tr = tr[HZ].values - occ_tr
        y_ca, y_te = ca[HZ].values, te[HZ].values

        # --- CQR band (the ACQR centre), fitted on train only -----------------------------------
        glo = HistGradientBoostingRegressor(loss="quantile", quantile=ALPHA/2, max_iter=100,
                                            random_state=SEED).fit(tr[FEAT].values, d_tr)
        ghi = HistGradientBoostingRegressor(loss="quantile", quantile=1-ALPHA/2, max_iter=100,
                                            random_state=SEED).fit(tr[FEAT].values, d_tr)
        qlo_ca = occ_ca + glo.predict(ca[FEAT].values); qhi_ca = occ_ca + ghi.predict(ca[FEAT].values)
        qlo_te = occ_te + glo.predict(te[FEAT].values); qhi_te = occ_te + ghi.predict(te[FEAT].values)
        qlo_ca, qhi_ca, _ = core.repair_quantile_crossing(qlo_ca, qhi_ca)
        qlo_te, qhi_te, _ = core.repair_quantile_crossing(qlo_te, qhi_te)
        E_cal = np.maximum(qlo_ca - y_ca, y_ca - qhi_ca)
        degenerate = bool(np.max(np.abs(E_cal)) < 1e-9)

        gam, dg = core.select_gamma_on_calibration(E_cal, qlo_ca, qhi_ca, y_ca, ALPHA, HSTEPS)

        # --- C04: thresholds from the cal-B segment of the SAME nested split ---------------------
        cut = int(len(y_ca) * 0.5); gap = HSTEPS - 1
        if args.check_only == "old":              # negative control: the 2026-09-03 replay
            seed, clip_b = E_cal[:cut], CLIP_LOW
        elif args.check_only == "clipnone":       # negative control: the gap rule without the clip
            seed, clip_b = E_cal[:cut - gap], None
        else:                                     # T024: the selector's seed rule, the test band's clip
            seed, clip_b = E_cal[:cut - gap], CLIP_LOW
        lo_b, hi_b = core.adaptive_conformal_stream(
            seed, qlo_ca[cut:], qhi_ca[cut:], y_ca[cut:], ALPHA, HSTEPS, gamma=gam, clip_low=clip_b)
        w_calB = hi_b - lo_b                      # prequential ACQR widths, pool never sees cal-B
        # control 1 (replay): the selector's cal-B PICP at the chosen gamma
        p_b = core.interval_metrics(y_ca[cut:], lo_b, hi_b, ALPHA)[0]; nb = len(y_ca) - cut
        r = ref.loc[fid]
        ok = (gam == float(r.gamma)) and (nb == int(r.n_cal_b)) and \
             (int(round(p_b * nb)) == int(round(float(r.gamma_calB_picp) * nb)))
        # --- test-time ACQR intervals, built once: the clip control reads the band the rows are computed from
        clip_t = None if args.check_only == "testclipnone" else CLIP_LOW   # negative control: test band unclipped
        lo_t, hi_t = core.adaptive_conformal_stream(E_cal, qlo_te, qhi_te, y_te, ALPHA,
                                                    HSTEPS, gamma=gam, clip_low=clip_t)
        # control 2 (clip): no lower end below CLIP_LOW, on the cal-B band and on the test band lo_t itself
        nb_below, nt_below = int(np.sum(lo_b < CLIP_LOW)), int(np.sum(lo_t < CLIP_LOW))
        ok_clip = nb_below == 0 and nt_below == 0
        n_checked += 1; n_fail += 0 if ok else 1; n_fail_clip += 0 if ok_clip else 1
        log(f"  control fac {fid}: gamma {gam:g}/{float(r.gamma):g} n_cal_b {nb}/{int(r.n_cal_b)} "
            f"calB covered {int(round(p_b * nb))}/{int(round(float(r.gamma_calB_picp) * nb))} "
            f"{'OK' if ok else 'MISMATCH'} | lower ends below clip: calB {nb_below}, test {nt_below} "
            f"{'CLIP-OK' if ok_clip else 'CLIP-MISMATCH'}")
        if args.check_only:
            continue
        if not (ok and ok_clip):
            sys.exit(f"[trust] CONTROL FAIL at facility {fid}: replay {'ok' if ok else 'MISMATCH'}, "
                     f"clip {'ok' if ok_clip else 'MISMATCH'}")

        # --- test-time ACQR intervals (lo_t, hi_t built above, before the controls) ----------------
        w_te = hi_t - lo_t
        err = np.abs(y_te - (qlo_te + qhi_te) / 2.0)
        covered = ((y_te >= lo_t) & (y_te <= hi_t)).astype(float)
        meanocc = max(float(te.occupancy.mean()), 1.0)
        b_te = np.array([bucket_of(h) for h in pd.to_datetime(te.timestamp.values).hour])
        base_share = {bk: float((b_te == bk).mean()) for bk in ORDER}
        rng = np.random.default_rng(SEED)

        def rec(meth, tgt, sel, extra=None):
            if sel.sum() == 0:
                return
            r = dict(facility_id=fid, dynamic=dyn_flag[fid], method=meth, commit_target=tgt,
                     commit_rate=float(sel.mean()), MAE_cars=float(err[sel].mean()),
                     MAE_pct=float(err[sel].mean()/meanocc*100),
                     committed_PICP=float(covered[sel].mean()),
                     committed_MPIW=float(w_te[sel].mean()), gamma=gam,
                     n_cal_b=dg.get("n_cal_b"), n_test=len(y_te), degenerate=degenerate)
            if extra:
                r.update(extra)
            rows.append(r)

        # commit-all baseline (no selection)
        rec("commit-all", 1.0, np.ones(len(y_te), dtype=bool))

        for tgt in TARGETS:
            # NOTE for the replication reviewer: this is an ORDINARY empirical percentile of cal-B
            # widths, deliberately not `core.conformal_quantile`. It selects the width below which a
            # target fraction of calibration rows fall — a commit-rate knob, not a coverage guarantee —
            # so the finite-sample (n+1) correction that C01 is about does not apply here.
            thr = float(np.quantile(w_calB, tgt))
            sel = w_te <= thr
            if sel.sum() == 0:
                continue
            # where do the abstentions fall, relative to each bucket's base rate?
            ab = ~sel
            lift = {}
            for bk in ORDER:
                share = float((b_te[ab] == bk).mean()) if ab.sum() else np.nan
                lift[f"abst_lift_{bk}"] = (share/base_share[bk]
                                           if base_share[bk] > 0 else np.nan)
            rec("width-ACQR", tgt, sel, lift)

            # matched random selection at the SAME achieved rate — the null comparator
            k = int(sel.sum()); acc = []
            for _ in range(args.n_random):
                idx = rng.choice(len(y_te), size=k, replace=False)
                m = np.zeros(len(y_te), dtype=bool); m[idx] = True
                acc.append((float(err[m].mean()), float(covered[m].mean()), float(w_te[m].mean())))
            a = np.array(acc)
            rows.append(dict(facility_id=fid, dynamic=dyn_flag[fid], method="random",
                             commit_target=tgt, commit_rate=float(k/len(y_te)),
                             MAE_cars=float(a[:, 0].mean()),
                             MAE_pct=float(a[:, 0].mean()/meanocc*100),
                             committed_PICP=float(a[:, 1].mean()),
                             committed_MPIW=float(a[:, 2].mean()), gamma=gam,
                             n_cal_b=dg.get("n_cal_b"), n_test=len(y_te), degenerate=degenerate))
        log(f"  fac {fid} done ({time.time()-t0:.0f}s)")

    if args.check_only:
        log(f"REPLAY CONTROL ({args.check_only}): {'PASS' if not n_fail else 'FAIL'} "
            f"({n_fail} of {n_checked} facilities differ from the selector)")
        log(f"CLIP CONTROL ({args.check_only}): {'PASS' if not n_fail_clip else 'FAIL'} "
            f"({n_fail_clip} of {n_checked} facilities have a lower end below the clip on cal-B or on the test band)")
        if n_fail or n_fail_clip:
            sys.exit(f"[trust] CONTROL FAIL ({args.check_only})")
        log(f"CONTROL PASS ({args.check_only}): both controls hold at all {n_checked} facilities")
        return
    if rows:
        rd = pd.DataFrame(rows)
        if PER.exists():
            rd = pd.concat([pd.read_csv(PER), rd], ignore_index=True)
        rd.to_csv(PER, index=False)

    per = pd.read_csv(PER)
    remaining = [f for f in all_fac if f not in set(per.facility_id.unique())]
    if remaining:
        log(f"REMAINING: {len(remaining)}")
    else:
        write_summary(per)
        log(f"ALL DONE: {per.facility_id.nunique()} facilities")


if __name__ == "__main__":
    main()
