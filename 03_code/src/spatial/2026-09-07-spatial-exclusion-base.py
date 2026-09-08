#!/usr/bin/env python3
"""Recompute the spatial leg (§5.5) on the paper's evaluation base (D-030, revision 49, 2026-09-07).

Prespecification: 04_experiments/2026-09-07-spatial-exclusion-base-PRESPECIFICATION.md.

WHY: the two live spatial scripts select facilities by `coords AND (train-window occupancy std >= 5)`, which
retains facility 8 -- the X08 dead sensor that D-018 excludes from every other reported statistic -- and omits
facility 24 (no coordinates). Both sets happen to be 21 facilities, which is why the mismatch survived to
revision 49. The correct population is `evaluation base AND has coordinates` = 20 facilities.

HOW: read-only re-aggregation. No model is fitted. The residual-correlation and distance matrices are
reconstructed from the stored pairwise table; the common test index is identical on both rosters (1,018
timestamps), so the stored correlations are exactly right for the subset. Same estimators, same seed, same
permutation counts as the live scripts -- only the roster differs.

Writes ONE new table and no tracker (defect-7 class). The frozen 2026-06-21 tables are read, never written;
the live spatial scripts and 2026-09-06-spatial-statistics.csv are untouched (A21).
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
TAB = ROOT / "05_results" / "tables"
PROC = ROOT / "01_data" / "processed"
sys.path.insert(0, str(ROOT / "03_code" / "src" / "conformal"))
import core  # noqa: E402

HZ = "y_t+15min"
FLAG = "use_15"
SEED = 42
N_PERM_MORAN = 999
N_PERM_MANTEL = 9999
OUT = TAB / "2026-09-07-spatial-statistics-exclusion-base.csv"


def log(m):
    print(f"[spatial-excl] {m}", flush=True)


def haversine(lo1, la1, lo2, la2):
    R = 6371.0
    p = math.pi / 180
    dlo = (lo2 - lo1) * p
    dla = (la2 - la1) * p
    a = math.sin(dla / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def morans_I(x, W):
    n = len(x)
    xb = x - x.mean()
    S0 = W.sum()
    return (n / S0) * ((W * np.outer(xb, xb)).sum() / (xb ** 2).sum())


def mantel(A, B, perms=N_PERM_MANTEL, seed=SEED):
    n = A.shape[0]
    iu = np.triu_indices(n, 1)
    a = A[iu]
    b = B[iu]
    r = float(np.corrcoef(a, b)[0, 1])
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(perms):
        pm = rng.permutation(n)
        Bp = B[np.ix_(pm, pm)]
        if abs(np.corrcoef(a, Bp[iu])[0, 1]) >= abs(r):
            cnt += 1
    return r, (cnt + 1) / (perms + 1)


def matrices(pairs, fids):
    """Distance and residual-correlation matrices for `fids`, from the stored pairwise table."""
    ix = {f: i for i, f in enumerate(fids)}
    n = len(fids)
    D = np.zeros((n, n))
    C = np.eye(n)
    seen = 0
    for fi, fj, dk, rc in pairs[["fi", "fj", "dist_km", "resid_corr"]].itertuples(index=False):
        if fi in ix and fj in ix:
            i, j = ix[fi], ix[fj]
            D[i, j] = D[j, i] = dk
            C[i, j] = C[j, i] = rc
            seen += 1
    assert seen == n * (n - 1) // 2, (seen, n)
    return D, C


def common_test_index(te, fids):
    idx = None
    for f in fids:
        s = set(pd.to_datetime(te[te.facility_id == f]["timestamp"]).values)
        idx = s if idx is None else (idx & s)
    return sorted(idx)


def raw_occupancy_corr(te, fids, index):
    ix = pd.DatetimeIndex(index)
    cols = {}
    for f in fids:
        g = te[te.facility_id == f].sort_values("timestamp")
        s = pd.Series(g["occupancy"].values, index=pd.to_datetime(g["timestamp"].values))
        cols[f] = s.loc[ix]
    O = pd.DataFrame(cols)
    Co = O.corr().loc[fids, fids].values
    iu = np.triu_indices(len(fids), 1)
    return float(Co[iu].mean())


def stats_for(name, fids, pairs, P, te):
    D, C = matrices(pairs, fids)
    n = len(fids)
    iu = np.triu_indices(n, 1)
    # Moran's I on the per-facility uncertainty descriptor, inverse-haversine weights
    Q = P[P.facility_id.isin(fids)].set_index("facility_id").loc[fids].reset_index()
    W = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                d = haversine(Q.lon[i], Q.lat[i], Q.lon[j], Q.lat[j])
                W[i, j] = 1.0 / d if d > 0 else 0.0
    x = Q["mean_aci_halfwidth"].values
    I = morans_I(x, W)
    rng = np.random.default_rng(SEED)
    perm = np.array([morans_I(rng.permutation(x), W) for _ in range(N_PERM_MORAN)])
    p_mi = float((np.sum(np.abs(perm) >= abs(I)) + 1) / (len(perm) + 1))
    r_m, p_m = mantel(D, C)
    rho, p_sp = spearmanr(D[iu], C[iu])
    near = float(C[(D < 2) & (D > 0)].mean())
    far = float(C[D > 5].mean())
    index = common_test_index(te, fids)
    occ = raw_occupancy_corr(te, fids, index)
    log(f"{name}: n={n} pairs={len(iu[0])} common_test_timestamps={len(index)}")
    log(f"{name}: Moran I={I:.6f} p={p_mi:.6f} | Mantel r={r_m:.6f} p={p_m:.6f} | naive rho={rho:.6f} p={p_sp:.6f}")
    log(f"{name}: mean_resid_corr={C[iu].mean():.6f} near={near:.6f} far={far:.6f} raw_occ_corr={occ:.6f}")
    note = "paper evaluation base (dynamic AND NOT low-information) INTERSECT has-coordinates" if name == "exclusion_base" \
        else "published roster: coords AND train-window std>=5 (retains facility 8, omits 24) -- NEGATIVE CONTROL"
    common = dict(population=name, city="belgrade", horizon=HZ, n_facilities=n,
                  facility_ids=";".join(str(f) for f in fids), n_pairs=len(iu[0]),
                  n_common_test_timestamps=len(index), seed=SEED, note=note)
    return [
        dict(statistic="morans_I_mean_aci_halfwidth", value=f"{I:.6f}", p_value=f"{p_mi:.6f}",
             n_permutations=N_PERM_MORAN, **common),
        dict(statistic="mantel_r_distance_vs_residcorr", value=f"{r_m:.6f}", p_value=f"{p_m:.6f}",
             n_permutations=N_PERM_MANTEL, **common),
        dict(statistic="spearman_rho_residcorr_vs_distance_naive", value=f"{rho:.6f}", p_value=f"{p_sp:.6f}",
             n_permutations="", **common),
        dict(statistic="mean_pairwise_resid_corr", value=f"{C[iu].mean():.6f}", p_value="", n_permutations="", **common),
        dict(statistic="mean_resid_corr_near_lt2km", value=f"{near:.6f}", p_value="", n_permutations="", **common),
        dict(statistic="mean_resid_corr_far_gt5km", value=f"{far:.6f}", p_value="", n_permutations="", **common),
        dict(statistic="mean_pairwise_raw_occupancy_corr", value=f"{occ:.6f}", p_value="", n_permutations="", **common),
    ]


def main():
    pairs = pd.read_csv(TAB / "2026-06-21-spatial-corr-distance.csv")
    P = pd.read_csv(TAB / "2026-06-21-spatial-facility-uncertainty.csv")
    d = pd.read_parquet(PROC / "belgrade_features_v2.parquet")
    te = d[d.split == "test"]
    sub = te[te[FLAG]]
    drop = set(int(f) for f in core.low_information_facilities(sub))
    evaluated = sorted(int(f) for f in sub.facility_id.unique() if int(f) not in drop)
    with_coords = sorted(int(f) for f in P.facility_id.unique())
    published = with_coords                      # the roster the live scripts use
    excl = [f for f in evaluated if f in set(with_coords)]   # the paper's base, coordinate-limited
    log(f"X08 exclusions on {FLAG} test rows: {sorted(drop)}")
    log(f"evaluation base (n={len(evaluated)}): {evaluated}")
    log(f"published spatial roster (n={len(published)}): {published}")
    log(f"exclusion base INTERSECT coords (n={len(excl)}): {excl}")
    rows = stats_for("published_21", published, pairs, P, te) + stats_for("exclusion_base", excl, pairs, P, te)
    cols = ["population", "city", "horizon", "n_facilities", "n_pairs", "n_common_test_timestamps",
            "statistic", "value", "p_value", "n_permutations", "seed", "facility_ids", "note"]
    out = pd.DataFrame(rows, columns=cols).sort_values(["population", "statistic"], kind="mergesort")
    out.to_csv(OUT, index=False)
    log(f"wrote {OUT.name} ({len(out)} rows)")
    log("ALL DONE")


if __name__ == "__main__":
    main()
