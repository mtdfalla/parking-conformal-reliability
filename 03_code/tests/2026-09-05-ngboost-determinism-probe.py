#!/usr/bin/env python3
"""PROBE for the NGBoost seeding defect (LESSONS_LOG A18). Contributes to NO reported number.

Three arms, all on ONE facility's real training data, built exactly as
`2026-09-03-e3-baselines.py` builds it (same features, same delta target):

  A  two consecutive NGBRegressor(random_state=SEED) fits in one process, nothing else done
     between them.                          -> tests whether `random_state` determines the fit
  B  the same, with np.random.seed(SEED) immediately before each fit
                                            -> tests whether the proposed fix removes the drift
  C  the RESUME-BOUNDARY simulation: a fit preceded by an arbitrary amount of global-RNG
     consumption (as a different resume boundary would produce), with and without the fix
                                            -> tests A18's actual claim, that the archived numbers
                                               depend on where the resume boundaries fell

Success for the fix requires B == 0 exactly AND C_seeded == 0 exactly. A18 is only established if
A > 0 and C_unseeded > 0.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from ngboost import NGBRegressor
from ngboost.distns import Normal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
import core  # noqa: E402

SEED = 42
PROC = ROOT / "01_data" / "processed"
OUT = ROOT / "05_results" / "tables" / "2026-09-05-ngboost-determinism-probe.csv"
FEAT_EXTRA = ["tod_sin", "tod_cos", "dow", "is_weekend", "is_holiday"]


def build(fid: int):
    df = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    df = df[df["use_15"]] if "use_15" in df.columns else df
    feats = [c for c in df.columns if c.startswith("lag_") or c.startswith("roll_")]
    feats += [c for c in FEAT_EXTRA if c in df.columns]
    d = df[df.facility_id == fid].sort_values("timestamp")
    hz = "y_t+15min"
    d = d.dropna(subset=feats + [hz, "occupancy"])
    tr = d[d.split == "train"]
    te = d[d.split == "test"]
    return tr[feats].values, tr[hz].values - tr.occupancy.values, te[feats].values


def fit(X, y, *, seeded: bool):
    if seeded:
        np.random.seed(SEED)
    ng = NGBRegressor(Dist=Normal, n_estimators=300, learning_rate=0.03,
                      random_state=SEED, verbose=False)
    ng.fit(X, y)
    return ng


def pred(ng, X):
    p = ng.pred_dist(X).params
    return np.asarray(p["loc"], float), np.asarray(p["scale"], float)


def mx(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


def main():
    fid = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    X_tr, d_tr, X_te = build(fid)
    print(f"[probe] facility {fid}: n_train={len(d_tr)} n_test={len(X_te)} p={X_tr.shape[1]}",
          flush=True)
    rows = []

    # ARM A -- no global seeding, two consecutive fits
    a1 = pred(fit(X_tr, d_tr, seeded=False), X_te)
    a2 = pred(fit(X_tr, d_tr, seeded=False), X_te)
    rows.append(dict(arm="A_unseeded_repeat", facility_id=fid,
                     max_abs_loc=mx(a1[0], a2[0]), max_abs_scale=mx(a1[1], a2[1]),
                     note="two NGBRegressor(random_state=42) fits, one process, identical data"))

    # ARM B -- the proposed fix
    b1 = pred(fit(X_tr, d_tr, seeded=True), X_te)
    b2 = pred(fit(X_tr, d_tr, seeded=True), X_te)
    rows.append(dict(arm="B_seeded_repeat", facility_id=fid,
                     max_abs_loc=mx(b1[0], b2[0]), max_abs_scale=mx(b1[1], b2[1]),
                     note="np.random.seed(42) immediately before each fit"))

    # ARM C -- the resume-boundary simulation
    np.random.seed(7); np.random.random(100_000)          # a different process history
    c_un = pred(fit(X_tr, d_tr, seeded=False), X_te)
    np.random.seed(7); np.random.random(100_000)
    c_se = pred(fit(X_tr, d_tr, seeded=True), X_te)
    rows.append(dict(arm="C_resume_boundary_unseeded", facility_id=fid,
                     max_abs_loc=mx(c_un[0], a1[0]), max_abs_scale=mx(c_un[1], a1[1]),
                     note="vs arm A fit 1 -- a different resume boundary, no fix"))
    rows.append(dict(arm="C_resume_boundary_seeded", facility_id=fid,
                     max_abs_loc=mx(c_se[0], b1[0]), max_abs_scale=mx(c_se[1], b1[1]),
                     note="vs arm B fit 1 -- a different resume boundary, WITH the fix"))

    rd = pd.DataFrame(rows)
    if OUT.exists():
        rd = pd.concat([pd.read_csv(OUT), rd], ignore_index=True)
    rd.to_csv(OUT, index=False)
    print(rd.to_string(index=False), flush=True)

    ok = (rows[0]["max_abs_loc"] > 0 and rows[2]["max_abs_loc"] > 0
          and rows[1]["max_abs_loc"] == 0.0 and rows[1]["max_abs_scale"] == 0.0
          and rows[3]["max_abs_loc"] == 0.0 and rows[3]["max_abs_scale"] == 0.0)
    print("\nPROBE " + ("PASS -- A18 reproduced AND the fix removes it, including across a "
                        "simulated resume boundary." if ok else
                        "FAIL -- see the table above; do not apply the fix on this evidence."),
          flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
