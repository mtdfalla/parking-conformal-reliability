#!/usr/bin/env python3
"""
EXP-031 (D') — amendment 2 (section 9): the injection-level sweep and the mask-identity check.

Prespecified in `04_experiments/2026-09-04-rphase5-PRESPECIFICATION.md` section 9, written after legs 1-2
returned a lead time of 0 and BEFORE this script was run. It changes no criterion and no claim; it exists
to attack that zero. EVERY level is reported; no level may be selected as a headline (9.2).

Reuses the leg-1/leg-2 machinery unchanged by importing it, so there is exactly one definition of the
injection, the feature rebuild and the withdrawal rule in this project (B9).
"""
from __future__ import annotations
import argparse, importlib.util, sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fc", HERE / "2026-09-04-rphase5-failure-case.py")
fc = importlib.util.module_from_spec(spec); sys.modules["fc"] = fc
sys.argv = [sys.argv[0]]
spec.loader.exec_module(fc)

ROOT = fc.ROOT; TAB = fc.TAB
LEVELS = [0.80, 0.90, 0.95, 0.98, 1.00, 1.05, 1.20, 1.6769]
OUT = TAB / "2026-09-04-failure-case-level-sweep.csv"
OUT_MASK = TAB / "2026-09-04-failure-case-mask-identity.csv"


def log(*a): print(*a, flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args(); t0 = time.time()
    df, feat, dyn = fc.load()
    te_all = df[df.split == "test"]
    excl = fc.core.low_information_facilities(te_all[te_all.facility_id.isin(dyn)])
    healthy = [f for f in dyn if f not in excl]

    done = set()
    if OUT.exists():
        p = pd.read_csv(OUT); done = set(zip(p.level_frac_of_cap.round(4), p.facility_id))

    # ---- 9.3 mask identity at facility 8, on the REAL observed series -----------------------------
    if not OUT_MASK.exists():
        g = df[df.facility_id == 8].sort_values("ts").dropna(subset=["occupancy"] + feat + [fc.HZ])
        m = fc.fit_models(g, feat)
        te = g[g.split == "test"]
        yhat, U = fc.panel(m, te[feat].values, te.occupancy.values, te[fc.HZ].values)
        onset_i = int(np.searchsorted(te.ts.values, np.datetime64(fc.ONSET)))
        w_int = (m["cap_train"] - U) < fc.SAFETY
        w_pt = (m["cap_train"] - yhat) < fc.SAFETY
        post = slice(onset_i, None)
        ident = bool((w_int[post] == w_pt[post]).all())
        pd.DataFrame([dict(
            facility_id=8, n_post_onset=int(len(U) - onset_i),
            n_slots_masks_agree=int((w_int[post] == w_pt[post]).sum()),
            masks_identical_post_onset=int(ident),
            n_withdrawn_interval=int(w_int[post].sum()), n_withdrawn_point=int(w_pt[post].sum()),
            n_slots_interval_only=int((w_int[post] & ~w_pt[post]).sum()),
            n_slots_point_only=int((w_pt[post] & ~w_int[post]).sum()),
            consequence=("request counts identical for EVERY demand seed by construction; the >=20-seed "
                         "simulation is not run (prespecification 9.3)") if ident else
                        "masks differ; the >=20-seed simulation runs as originally specified",
        )]).to_csv(OUT_MASK, index=False)
        log(f"[9.3] facility 8 post-onset masks identical = {ident} "
            f"(interval-only {int((w_int[post] & ~w_pt[post]).sum())}, "
            f"point-only {int((w_pt[post] & ~w_int[post]).sum())})")

    # ---- 9.2 the level sweep ----------------------------------------------------------------------
    for fid in healthy:
        g = df[df.facility_id == fid].sort_values("ts").dropna(subset=["occupancy"] + feat + [fc.HZ])
        if all((round(L, 4), fid) in done for L in LEVELS):
            continue
        if time.time() - t0 > args.budget:
            log("REMAINING"); return
        m = fc.fit_models(g, feat)
        if m is None:
            continue
        te_mask = (g.split == "test").values
        pos = np.arange(len(g)); te_pos = pos[te_mask]
        ts = g.ts.values[te_mask]
        onset_i = int(np.searchsorted(ts, np.datetime64(fc.ONSET)))
        inj_pos = te_pos[onset_i]
        X_par = g[feat].values[te_mask]
        occ_full = g.occupancy.values.copy(); y_full = g[fc.HZ].values.copy()
        rows = []
        for L in LEVELS:
            if (round(L, 4), fid) in done:
                continue
            v = L * m["cap_train"]
            occ_i = occ_full.copy(); y_i = y_full.copy()
            occ_i[inj_pos:] = v; y_i[inj_pos:] = v
            rb = fc.rebuild_features(occ_i)
            Xi = X_par.copy()
            for j, c in enumerate(feat):
                if c in rb:
                    Xi[:, j] = rb[c][te_mask]
            good = ~np.isnan(Xi).any(axis=1)
            yhat, U = fc.panel(m, Xi[good], occ_i[te_mask][good], y_i[te_mask][good])
            oi = int(good[:onset_i].sum())
            r = fc.summarise(f"level_{L:.4f}", fid, ts[good], yhat, U, m["cap_train"], oi,
                             extra=dict(level_frac_of_cap=round(L, 4), injected_value=round(float(v), 4)))
            rows.append(r)
        if rows:
            pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
            log(f"[9.2] fac {fid}: {len(rows)} levels ({time.time()-t0:.0f}s)")
    log("ALL DONE")


if __name__ == "__main__":
    main()
