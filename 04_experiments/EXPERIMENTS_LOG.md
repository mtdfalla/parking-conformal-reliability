# EXPERIMENTS LOG

One row per run. Append newest at the bottom of the table. Keep configs reproducible (seed, split, params).

## Index

| ID | Date | Base model | CP variant | Facility/scope | Horizon | Target cov. | Empirical cov. | Mean width | Notes / artifacts |
|----|------|-----------|-----------|----------------|---------|-------------|----------------|------------|-------------------|
| _(none yet)_ | | | | | | | | | |

---

## Detailed entries

<!-- Template:
### EXP-001 — YYYY-MM-DD — <short name>
- **Goal:**
- **Data/split:** train/cal/test = …; seed = …
- **Base model + params:**
- **CP variant + params:**
- **Scope:** facility / all-23
- **Metrics:** coverage (target vs empirical), interval width, MAE/RMSE
- **Result summary:**
- **Artifacts:** figures/tables paths in 05_results/
- **Decision/next:**
-->

_First planned run: single-facility split-CP baseline (see PROJECT_STATUS → NEXT ACTIONS)._

### EXP-001 — 2026-06-21 — Split-CP baseline (single facility)
- **Facility:** 3 (Garaža „Zeleni venac“); **base model:** RandomForest(200, leaf>=2), seed 42
- **Split:** train 2072 / calib 766 / test 1018 (temporal)
- **Method:** split conformal, absolute-residual score
- **Results (PICP target / actual, MPIW, Winkler):**

|   facility_id | horizon   |   level |   MAE |   RMSE |   q_hat |   PICP |   target_cov |   cov_gap |   MPIW |   Winkler |
|--------------:|:----------|--------:|------:|-------:|--------:|-------:|-------------:|----------:|-------:|----------:|
|             3 | y_t+5min  |    0.9  |  3.66 |   5.09 |    7.01 | 0.833  |         0.9  |   -0.067  |  14.03 |     23.9  |
|             3 | y_t+5min  |    0.95 |  3.66 |   5.09 |    9.25 | 0.9273 |         0.95 |   -0.0227 |  18.51 |     27.34 |
|             3 | y_t+15min |    0.9  |  5.74 |   8.15 |   11.22 | 0.8664 |         0.9  |   -0.0336 |  22.44 |     39.05 |
|             3 | y_t+15min |    0.95 |  5.74 |   8.15 |   14.84 | 0.9303 |         0.95 |   -0.0197 |  29.67 |     48.72 |
|             3 | y_t+30min |    0.9  |  8.5  |  12.15 |   16.01 | 0.8585 |         0.9  |   -0.0415 |  32.02 |     58.18 |
|             3 | y_t+30min |    0.95 |  8.5  |  12.15 |   20.46 | 0.9253 |         0.95 |   -0.0247 |  40.92 |     74.87 |

- **Artifacts:** `2026-06-21-splitcp-baseline-metrics.csv`, `2026-06-21-splitcp-baseline-fac3.png`
- **Read:** coverage (PICP) should be >= target; check it holds at t+30 too.

### EXP-002 — 2026-06-21 — Adaptive CP (ACI) vs split-CP
- **Facility:** 3 (Garaža „Zeleni venac“); RF(200); ACI gamma=0.05, sliding window=766
- **Goal:** close the under-coverage gap from EXP-001

|   facility_id | horizon   |   level | method   |   PICP |   cov_gap |   MPIW |   Winkler |
|--------------:|:----------|--------:|:---------|-------:|----------:|-------:|----------:|
|             3 | y_t+5min  |    0.9  | split-CP | 0.833  |   -0.067  |  14.03 |     23.9  |
|             3 | y_t+5min  |    0.9  | ACI      | 0.9008 |    0.0008 |  15.38 |     19.81 |
|             3 | y_t+5min  |    0.95 | split-CP | 0.9273 |   -0.0227 |  18.51 |     27.34 |
|             3 | y_t+5min  |    0.95 | ACI      | 0.9509 |    0.0009 |  20.37 |     24.78 |
|             3 | y_t+15min |    0.9  | split-CP | 0.8664 |   -0.0336 |  22.44 |     39.05 |
|             3 | y_t+15min |    0.9  | ACI      | 0.8988 |   -0.0012 |  23.54 |     30.16 |
|             3 | y_t+15min |    0.95 | split-CP | 0.9303 |   -0.0197 |  29.67 |     48.72 |
|             3 | y_t+15min |    0.95 | ACI      | 0.9499 |   -0.0001 |  30.86 |     37.71 |
|             3 | y_t+30min |    0.9  | split-CP | 0.8585 |   -0.0415 |  32.02 |     58.18 |
|             3 | y_t+30min |    0.9  | ACI      | 0.8988 |   -0.0012 |  30.85 |     43.32 |
|             3 | y_t+30min |    0.95 | split-CP | 0.9253 |   -0.0247 |  40.92 |     74.87 |
|             3 | y_t+30min |    0.95 | ACI      | 0.9499 |   -0.0001 |  40.28 |     51.81 |

- **Artifacts:** `2026-06-21-aci-vs-splitcp-metrics.csv`, `2026-06-21-aci-vs-splitcp-fac3.png`
- **Read:** ACI PICP should sit at/above target; running-coverage curve converges to 0.90.

### EXP-003 — 2026-06-21 — Split-CP vs ACI across ALL facilities
- **Scope:** 24 facilities (22 dynamic, train occ std>=5.0); RF(100); ACI gamma=0.05

| horizon   |   level | method   |   mean_PICP |   median_PICP |   std_PICP |   mean_MPIW |   mean_Winkler |   frac_at_target |
|:----------|--------:|:---------|------------:|--------------:|-----------:|------------:|---------------:|-----------------:|
| y_t+15min |    0.9  | ACI      |      0.8995 |        0.8998 |     0.0025 |     22.2325 |        28.2374 |           1      |
| y_t+15min |    0.9  | split-CP |      0.8677 |        0.9101 |     0.1468 |     21.8437 |        54.8611 |           0.5455 |
| y_t+15min |    0.95 | ACI      |      0.9497 |        0.9504 |     0.0028 |     27.8168 |        34.0044 |           1      |
| y_t+15min |    0.95 | split-CP |      0.9447 |        0.9499 |     0.0405 |     32.7764 |        48.1805 |           0.6364 |
| y_t+30min |    0.9  | ACI      |      0.8996 |        0.8998 |     0.0023 |     29.1557 |        36.7783 |           1      |
| y_t+30min |    0.9  | split-CP |      0.8643 |        0.8816 |     0.1388 |     30.8441 |        63.3184 |           0.4545 |
| y_t+30min |    0.95 | ACI      |      0.9497 |        0.9504 |     0.0025 |     37.3285 |        45.1064 |           1      |
| y_t+30min |    0.95 | split-CP |      0.9395 |        0.9479 |     0.0467 |     42.6076 |        66.9096 |           0.5455 |
| y_t+5min  |    0.9  | ACI      |      0.8991 |        0.8998 |     0.0017 |     15.0767 |        20.0068 |           1      |
| y_t+5min  |    0.9  | split-CP |      0.8693 |        0.9032 |     0.1316 |     13.6962 |        39.1713 |           0.6364 |
| y_t+5min  |    0.95 | ACI      |      0.9494 |        0.9499 |     0.0019 |     19.8727 |        25.0372 |           1      |
| y_t+5min  |    0.95 | split-CP |      0.9163 |        0.9474 |     0.1381 |     18.5567 |        61.3506 |           0.5455 |

- **Artifacts:** `2026-06-21-all-facilities-per-facility.csv`, `2026-06-21-all-facilities-summary.csv`, `2026-06-21-coverage-distribution.png`
- **Read:** ACI mean PICP ~ target with high fraction-at-target; split-CP systematically lower.

### EXP-004 — 2026-06-21 — Delta-modelling re-run (supersedes EXP-001..003)
- **Fix:** predict change vs current occupancy; persistence baseline. RF(100); ACI gamma=0.05.
- **Model quality (dynamic facilities):** RF-delta <= persistence on 65% of facility-horizons; mean MAE RF-delta 3.41 vs persistence 4.14.
- **Coverage (dynamic facilities):**

| horizon   |   level | method   |   mean_PICP |   median_PICP |   std_PICP |   mean_MPIW |   mean_Winkler |   frac_at_target |
|:----------|--------:|:---------|------------:|--------------:|-----------:|------------:|---------------:|-----------------:|
| y_t+15min |    0.9  | ACI      |      0.8991 |        0.8993 |     0.0013 |     15.1985 |        20.7253 |           1      |
| y_t+15min |    0.9  | split-CP |      0.8998 |        0.9018 |     0.0412 |     17.3185 |        27.4218 |           0.6818 |
| y_t+15min |    0.95 | ACI      |      0.9495 |        0.9499 |     0.0013 |     20.7201 |        27.0631 |           1      |
| y_t+15min |    0.95 | split-CP |      0.947  |        0.9548 |     0.037  |     23.2617 |        34.2102 |           0.6818 |
| y_t+30min |    0.9  | ACI      |      0.8994 |        0.8998 |     0.0016 |     22.2222 |        29.5597 |           1      |
| y_t+30min |    0.9  | split-CP |      0.9012 |        0.9047 |     0.0553 |     27.1683 |        41.9641 |           0.6818 |
| y_t+30min |    0.95 | ACI      |      0.9497 |        0.9499 |     0.0017 |     30.0756 |        37.9972 |           1      |
| y_t+30min |    0.95 | split-CP |      0.9437 |        0.9538 |     0.0454 |     35.0004 |        53.2859 |           0.6818 |
| y_t+5min  |    0.9  | ACI      |      0.899  |        0.8988 |     0.0009 |      7.259  |        10.1366 |           1      |
| y_t+5min  |    0.9  | split-CP |      0.9019 |        0.9116 |     0.0337 |      7.5216 |        12.6472 |           0.7273 |
| y_t+5min  |    0.95 | ACI      |      0.9495 |        0.9499 |     0.0009 |     10.1236 |        13.5867 |           1      |
| y_t+5min  |    0.95 | split-CP |      0.9505 |        0.9563 |     0.0239 |     10.8057 |        15.3592 |           0.8182 |

- **Artifacts:** `2026-06-21-delta-summary.csv`, `2026-06-21-delta-model-mae.csv`, `2026-06-21-delta-coverage-distribution.png`, `2026-06-21-delta-aci-vs-splitcp-fac3.png`
- **Read:** RF-delta should beat persistence on most facilities; ACI PICP ~ target with low spread.

### EXP-005 — 2026-06-21 — Birmingham EXTERNAL VALIDATION (delta-model)
- **Scope:** 28 facilities (28 dynamic); 30-min cadence; horizons 30/60/90 min; RF(100); ACI gamma=0.05.
- **Model quality:** RF-delta <= persistence on 94% of facility-horizons; mean MAE RF-delta 30.56 vs persistence 61.00.
- **Coverage (dynamic facilities):**

| horizon   |   level | method   |   mean_PICP |   median_PICP |   std_PICP |   mean_MPIW |   mean_Winkler |   frac_at_target |
|:----------|--------:|:---------|------------:|--------------:|-----------:|------------:|---------------:|-----------------:|
| y_t+30min |    0.9  | ACI      |      0.8955 |        0.8942 |     0.0073 |     77.2828 |        108.373 |           0.8214 |
| y_t+30min |    0.9  | split-CP |      0.9012 |        0.9088 |     0.0469 |     76.3439 |        106.957 |           0.6429 |
| y_t+30min |    0.95 | ACI      |      0.9468 |        0.9463 |     0.0046 |    105.921  |        136.079 |           0.9286 |
| y_t+30min |    0.95 | split-CP |      0.9503 |        0.9495 |     0.0268 |    100.368  |        128.565 |           0.7143 |
| y_t+60min |    0.9  | ACI      |      0.8942 |        0.8926 |     0.0075 |    135.02   |        175.391 |           0.75   |
| y_t+60min |    0.9  | split-CP |      0.9031 |        0.9028 |     0.0502 |    136.776  |        181.556 |           0.7143 |
| y_t+60min |    0.95 | ACI      |      0.9456 |        0.9463 |     0.007  |    173.869  |        215.272 |           0.8571 |
| y_t+60min |    0.95 | split-CP |      0.9509 |        0.9497 |     0.0375 |    178.008  |        220.611 |           0.6429 |
| y_t+90min |    0.9  | ACI      |      0.8951 |        0.8926 |     0.0083 |    183.51   |        229.393 |           0.7857 |
| y_t+90min |    0.9  | split-CP |      0.8999 |        0.8997 |     0.0499 |    180.329  |        239.563 |           0.6429 |
| y_t+90min |    0.95 | ACI      |      0.9457 |        0.9463 |     0.0065 |    229.874  |        272.089 |           0.8214 |
| y_t+90min |    0.95 | split-CP |      0.956  |        0.9567 |     0.0369 |    248.599  |        292.706 |           0.75   |

- **Artifacts:** `2026-06-21-bham-summary.csv`, `2026-06-21-bham-model-mae.csv`, `2026-06-21-bham-coverage-distribution.png`
- **Read:** replicate Belgrade pattern — ACI near-exact low-variance coverage; split-CP variable.

### EXP-006 — 2026-06-21 — Spatial uncertainty analysis (RQ4, Belgrade)
- **Scope:** 21 coord-matched dynamic facilities; delta residuals, t+15min, test.
- **Residual co-movement vs distance:** Spearman rho=-0.121 (p=8.02e-02); near<2km 0.025 vs far>5km -0.005.
- **Moran's I (uncertainty clustering):** -0.009, perm p=0.905.
- **Artifacts:** spatial-facility-uncertainty.csv, spatial-corr-distance.csv, spatial-uncertainty-map.png, spatial-corr-vs-distance.png, uncertainty-by-hour.png
- **Read:** negative Spearman + positive Moran's I => spatially structured uncertainty => motivates spatial/graph CP.

- **EXP-006 follow-up (complementary):** raw occupancy LEVELS co-move strongly (mean corr 0.52; near<2km 0.567 vs far>5km 0.499, Spearman −0.166 p=0.016); differenced demand mean corr 0.089. => predictable demand is (weakly) spatial, but RESIDUAL uncertainty is facility-local. Conclusion: spatial/graph CP not needed; per-facility ACI suffices. See `05_results/SPATIAL_FINDINGS.md`.

### EXP-007 — 2026-06-21 — Time-of-day CONDITIONAL CP (Belgrade, t+15min, 90%)
- **Scope:** 22 dynamic facilities pooled; delta-model. Buckets: night/am_rush/midday/pm_rush/evening.
- **Conditional coverage (target 0.90):**

| bucket   |    n |   split |   ACI |   Msplit |   ToD_ACI |
|:---------|-----:|--------:|------:|---------:|----------:|
| night    | 6336 |   0.973 | 0.953 |    0.892 |     0.906 |
| am_rush  | 4224 |   0.898 | 0.803 |    0.905 |     0.901 |
| midday   | 5500 |   0.833 | 0.888 |    0.874 |     0.903 |
| pm_rush  | 3762 |   0.841 | 0.902 |    0.894 |     0.898 |
| evening  | 2574 |   0.951 | 0.945 |    0.922 |     0.911 |

- **Overall (PICP, MPIW, worst-bucket PICP):**

|                |   PICP |    MPIW |   worst_bucket_PICP |
|:---------------|-------:|--------:|--------------------:|
| split-CP       | 0.8998 | 17.3185 |              0.8335 |
| ACI            | 0.8991 | 15.1985 |              0.8026 |
| Mondrian-split | 0.8935 | 15.3247 |              0.8736 |
| ToD-ACI        | 0.9036 | 15.5504 |              0.8977 |

- **Artifacts:** `2026-06-21-conditional-coverage.csv/.png`, `2026-06-21-conditional-overall.csv`

### EXP-007 — 2026-06-21 — Time-of-day CONDITIONAL CP (Belgrade, t+15min, 90%)
- **Scope:** 22 dynamic facilities pooled; delta-model. Buckets: night/am_rush/midday/pm_rush/evening.
- **Conditional coverage (target 0.90):**

| bucket   |    n |   split |   ACI |   Msplit |   ToD_ACI |
|:---------|-----:|--------:|------:|---------:|----------:|
| night    | 6336 |   0.973 | 0.953 |    0.892 |     0.906 |
| am_rush  | 4224 |   0.898 | 0.803 |    0.905 |     0.901 |
| midday   | 5500 |   0.833 | 0.888 |    0.874 |     0.903 |
| pm_rush  | 3762 |   0.841 | 0.902 |    0.894 |     0.898 |
| evening  | 2574 |   0.951 | 0.945 |    0.922 |     0.911 |

- **Overall (PICP, MPIW, worst-bucket PICP):**

|                |   PICP |    MPIW |   worst_bucket_PICP |
|:---------------|-------:|--------:|--------------------:|
| split-CP       | 0.8998 | 17.3185 |              0.8335 |
| ACI            | 0.8991 | 15.1985 |              0.8026 |
| Mondrian-split | 0.8935 | 15.3247 |              0.8736 |
| ToD-ACI        | 0.9036 | 15.5504 |              0.8977 |

- **Artifacts:** `2026-06-21-conditional-coverage.csv/.png`, `2026-06-21-conditional-overall.csv`

### EXP-008 — 2026-06-21 — Model-agnostic robustness (Belgrade, t+15min)
- **Scope:** 22 dynamic facilities; base learners RandomForest, GradBoost (HistGBR), Ridge(linear); delta-model.

| base          |   MAE |   level | method   |   meanPICP |   stdPICP |   MPIW |   Winkler |
|:--------------|------:|--------:|:---------|-----------:|----------:|-------:|----------:|
| RandomForest  |  3.41 |    0.9  | split-CP |     0.8998 |    0.0403 |  17.32 |     27.42 |
| RandomForest  |  3.41 |    0.9  | ACI      |     0.8991 |    0.0012 |  15.2  |     20.73 |
| RandomForest  |  3.41 |    0.95 | split-CP |     0.947  |    0.0362 |  23.26 |     34.21 |
| RandomForest  |  3.41 |    0.95 | ACI      |     0.9495 |    0.0013 |  20.72 |     27.06 |
| GradBoost     |  3.57 |    0.9  | split-CP |     0.8997 |    0.042  |  17.49 |     27.93 |
| GradBoost     |  3.57 |    0.9  | ACI      |     0.8993 |    0.0011 |  15.49 |     21.54 |
| GradBoost     |  3.57 |    0.95 | split-CP |     0.9487 |    0.0283 |  23.29 |     34.38 |
| GradBoost     |  3.57 |    0.95 | ACI      |     0.9496 |    0.0011 |  21    |     27.57 |
| Ridge(linear) |  3.42 |    0.9  | split-CP |     0.8837 |    0.1027 |  15.9  |     25.98 |
| Ridge(linear) |  3.42 |    0.9  | ACI      |     0.8991 |    0.001  |  15.23 |     20.51 |
| Ridge(linear) |  3.42 |    0.95 | split-CP |     0.9387 |    0.0444 |  20.97 |     32.03 |
| Ridge(linear) |  3.42 |    0.95 | ACI      |     0.9497 |    0.0011 |  20.33 |     26.24 |

- **Artifacts:** `2026-06-21-model-agnostic.csv`
- **Read:** ACI gives ~nominal PICP with low std for every base learner; widths scale with base accuracy.

### EXP-009 — 2026-06-21 — Trust/abstain (selective prediction by ACI width)
- **Scope:** 22 dynamic facilities; Belgrade t+15min, 90%; MAE normalised to % of mean occupancy.

|   commit_frac |   sel_MAE_pct |   sel_coverage |   random_MAE_pct |   MAE_reduction_% |
|--------------:|--------------:|---------------:|-----------------:|------------------:|
|           0.1 |         0.942 |          0.863 |            3.355 |            71.934 |
|           0.2 |         1.107 |          0.874 |            3.355 |            67.016 |
|           0.3 |         1.322 |          0.878 |            3.355 |            60.59  |
|           0.4 |         1.536 |          0.882 |            3.355 |            54.232 |
|           0.5 |         1.71  |          0.883 |            3.355 |            49.03  |
|           0.6 |         1.878 |          0.886 |            3.355 |            44.024 |
|           0.7 |         2.136 |          0.887 |            3.355 |            36.344 |
|           0.8 |         2.374 |          0.888 |            3.355 |            29.229 |
|           0.9 |         2.761 |          0.892 |            3.355 |            17.707 |
|           1   |         3.355 |          0.899 |            3.355 |             0     |

- **Rush-hour share:** abstained (widest 30%) 0.42 vs overall 0.36 — abstention concentrates on volatile periods.
- **Artifacts:** `2026-06-21-trust-abstain.csv`, `2026-06-21-trust-abstain.png`
- **Read:** committing the most-confident predictions sharply lowers error vs acting on all/random; the interval width is an actionable trust signal.

### Strengthening additions (2026-06-21) — incorporated into manuscript v4
- **Fig 1 framework** schematic — `2026-06-21-framework.png`.
- **EXP-008 model-agnostic** — `2026-06-21-model-agnostic.csv` (RF/GradBoost/Ridge; ACI ~0.899 std≈0.001 all; split-CP variable, Ridge std 0.10).
- **EXP-009 trust/abstain** — `2026-06-21-trust-abstain.csv/.png`: commit most-confident 70% → MAE −36% (3.4%→2.1% of mean occ), coverage ~0.89; abstained widest-30% rush-hour share 0.42 vs 0.36.

### EXP-010 — 2026-06-25 — CORRECTED: delay-aware ACI + CQR baseline (supersedes EXP-004/005)
- **Fix:** ACI now releases each forecast's residual/score AND alpha-update only after h steps (no lookahead). Intervals lower-clipped at 0.
- **Baselines:** added CQR (conformalized quantile regression on the delta target). Levels 0.80/0.85/0.90/0.95 for split-CP & ACI.
- **Belgrade @90% (t+15):** ACI PICP 0.899 std 0.001 (100% of facility bootstrap-CIs contain 0.90); split-CP 0.900 std 0.041 (64%); CQR 0.904 std 0.030 (64%, tighter MPIW 13.0 vs ACI 17.6).
- **Birmingham @90% (t+60):** ACI 0.892 std 0.009 (100% CI-contains); split-CP 0.903 std 0.050 (79%); CQR 0.904 std 0.039 (71%).
- **Takeaway:** the lookahead-corrected result HOLDS — ACI keeps near-exact low-variance per-facility coverage; CQR gives tighter but per-facility-variable intervals. ACI's edge is per-facility CONSISTENCY.
- **Artifacts:** `2026-06-25-corr-{belgrade,birmingham}-{per-facility,summary,fractarget,basemodel}.csv`, `2026-06-25-corr-*-coverage.png`, `*-calibration.png`

### EXP-007b/009b — 2026-06-25 — Conditional + trust/abstain (DELAY-AWARE ACI)
- **Conditional (worst bucket PICP):** split-CP 0.833, ACI 0.801, ToD-ACI 0.893.
- **Trust/abstain (calibration-chosen width thresholds):** at ~70% commit, MAE 2.35 cars (2.3% of mean occ), coverage 0.875.
- **Artifacts:** `2026-06-25-corr-conditional.csv/.png`, `2026-06-25-corr-trustabstain.csv/.png`

### EXP-006b — 2026-06-25 — Spatial: Mantel test + defined weights
- **Spatial weights:** inverse geographic (haversine) distance; **per-facility uncertainty** = mean ACI interval half-width.
- **Mantel test** (geo-distance vs residual-correlation, 9999 perms): r=-0.129, p=0.151 -> no significant association.
- Naive Spearman (for reference, not independence-corrected): rho=-0.121, p=8.02e-02. Mean residual corr 0.007.
- **Conclusion (softened):** In these Belgrade data we find no evidence that residual uncertainty is spatially structured; graph-based pooling is not clearly justified for this setting (not a general claim).

### EXP-011 — 2026-08-04 — ACQR: Adaptive CQR (ACI on CQR scores, delay-aware)
- **Motivation:** prior review, majors 1–2 (ACI-favoring criterion; CQR wins Winkler). Compose the two:
  CQR quantile band (shape) + delayed ACI alpha-update on CQR scores E=max(qlo−y, y−qhi), symmetric margin.
- **Protocol:** identical to EXP-010 (seed 42, same splits/features; GBM quantile models, gamma 0.05,
  window=|cal|, feedback released after h steps, lower clip at 0). Levels 0.90/0.95.
- **Belgrade @90:** PICP 0.899 std 0.002–0.002, 100% CI-at-target ALL horizons; Winkler t+5 8.55 / t+15 22.09 / t+30 40.16
  (ACI: 9.91/24.16/41.62; CQR: 8.52/20.36/33.23). ACQR beats ACI everywhere; ties CQR at t+5.
- **Birmingham @90:** PICP 0.890–0.897 std 0.010–0.012, 100% CI-at-target ALL horizons; Winkler 105.4/181.1/250.7
  (ACI 108.4/187.9/253.9). Beats ACI in all rows; CQR still best on Winkler (103.2/174.0/233.7) but only 71–82% at target.
- **Takeaway:** ACQR strictly dominates plain ACI (same perfect per-facility consistency, better efficiency);
  reframes results as a reliability–efficiency frontier.
- **Artifacts:** `2026-08-04-acqr-{belgrade,birmingham}-per-facility.csv`, `2026-08-04-fourmethod-summary-90.csv`,
  script `03_code/src/conformal/2026-08-04-adaptive-cqr.py`.

### EXP-012 — 2026-08-04 — Paired inferential tests between methods (R3 major 3)
- **Method:** per city/horizon @90%, paired per-facility differences on Winkler and |PICP−0.90|;
  Wilcoxon signed-rank + 10k-resample bootstrap 90% CI on the mean difference. Pairs: ACI/ACQR vs split-CP/CQR, ACQR vs ACI.
- **Reliability (|coverage gap|):** ACI & ACQR better than split-CP AND CQR in every city-horizon (p<0.001
  in 17/18 comparisons; ACQR better at 68–100% of facilities). ACQR ≈ ACI (n.s.) — consistency preserved.
- **Efficiency (Winkler):** CQR significantly better than ACI in all 6 rows (confirms R3); ACQR significantly
  improves on ACI (Belgrade t+5/t+15 p<0.001; negative mean diff in all 6 rows) and is n.s. vs split-CP in
  most rows. Honest note: Birmingham t+90 split-CP beats ACI (+14.3, p=0.001); ACQR shrinks it to +11.1 n.s.
- **Artifacts:** `2026-08-04-paired-tests.csv`, script `2026-08-04-paired-tests.py`.

### EXP-013 — 2026-08-04 — Rolling-origin evaluation, Belgrade (R3 minor: thin 4-day test window)
- **Design:** 3 expanding-window folds, distinct 3-day test windows (Mar 13–15 / 16–18 / 19–21; 9 test days
  total vs 4); t+15, 90%, same 22 dynamic facilities; methods split-CP/ACI/CQR/ACQR (delay-aware).
- **Result:** ACQR within ±0.02 of target at 100% of facility-folds in EVERY fold (ACI 95–100%); CQR 32–55%,
  split-CP 32–55% and collapses in F2 (std 0.161, Winkler 34.9 vs ACQR 22.1). Pooled fold-facility paired
  |gap| tests (n=66): ACI/ACQR better than split-CP/CQR at p<1e-10.
- **Takeaway:** the per-facility reliability gap is not a one-window artifact; ACQR beats ACI on Winkler in
  all 3 folds.
- **Artifacts:** `2026-08-04-rolling-origin-belgrade.csv`, script `2026-08-04-rolling-origin.py`.

### EXP-014 — 2026-08-04 — Lean E3 baselines: EnbPI (MAPIE), AgACI-style, NGBoost (prior review, baseline request)
- **Scope:** headline settings (Belgrade t+15, Birmingham t+60, 90%), all dynamic facilities, delta target,
  seed 42, identical splits/features. EnbPI = MAPIE TimeSeriesRegressor (BlockBootstrap 30×10, day-chunked
  causal residual updates); AgACI-style = EWA over γ∈{0.001…0.2} of delay-aware ACI experts (pinball-loss
  weights, matured feedback only; labeled "-style" — EWA, not Zaffran's exact BOA); NGBoost = Gaussian
  predictive distribution (parametric, no finite-sample guarantee). SPCI cited-not-run (D-011).
- **Belgrade t+15 @90:** EnbPI 0.887 std 0.068 (68% CI-at-target), Winkler 28.4; AgACI-style 0.933 (over-covers)
  std 0.009, Wink 22.6; NGBoost 0.760 std 0.087, Wink 27.7. [ACQR 0.899/0.002/22.1/100%]
- **Birmingham t+60 @90 (external):** EnbPI 0.845 std 0.078 (61%); AgACI-style 0.907 std 0.020 (93%), Wink 177.6;
  **NGBoost 0.384** std 0.158 (0%) — parametric intervals collapse under the train→test shift.
- **Paired tests (addendum):** ACQR better than EnbPI on |coverage gap| BOTH cities p<1e-4 and on Belgrade
  Winkler p=0.003; ACQR vs AgACI-style Winkler n.s. (ACQR hits exact target; AgACI-style drifts conservative).
- **Takeaways:** (1) the 2026 benchmark warning that EnbPI can under-cover replicates on parking data —
  strengthens the per-facility reliability finding; (2) γ-aggregation removes tuning but over-covers as
  configured; (3) the non-conformal probabilistic baseline is dramatically miscalibrated out-of-city →
  strongest possible motivation for distribution-free CP. The baseline request (SOTA of the same method characteristic) is closed.
- **Artifacts:** `2026-08-04-e3-{belgrade,birmingham}-per-facility.csv`,
  `2026-08-04-headline-sevenmethod-summary.csv`, `2026-08-04-paired-tests-e3.csv`,
  script `03_code/src/conformal/2026-08-04-e3-baselines.py`.

### EXP-015 — 2026-08-04 — Risk-aware allocation vignette (Belgrade, t+15, 90% ACQR)
- **Design:** 21 coord-matched dynamic facilities; proxy capacity = historical max occupancy (stated proxy);
  600 seeded requests over test-window weekday afternoons (Mar 20–21, 12:00–19:00); destinations 65%
  concentrated (~350 m) around the tight downtown cluster (fac 8/9/10/23 run ≥90% of cap), 35% uniform.
  Greedy nearest-first policies, safety margin s=1: POINT commits if cap−ŷ≥1; INTERVAL commits only if
  worst-case cap−U≥1 (ACQR upper bound) — trust/abstain inside allocation. Independent requests (no
  queueing/rerouting) — illustrative vignette, NOT a simulator (D-010 scope).
- **Result:** POINT overflow **14.8%** of requests (driver reaches a full facility); INTERVAL **0.0%**,
  at +49 m mean detour (1.183 vs 1.134 km; p90 identical); both assign 100% of requests.
- **Read:** calibrated upper bounds convert directly into a guarantee-based assignment rule; the cost of
  eliminating failed trips is ~4% extra walking distance. CTR-facing demonstration that intervals change
  a transportation decision.
- **Artifacts:** `2026-08-04-allocation-vignette.csv`, `2026-08-04-allocation-vignette-requests.csv`,
  `figures/2026-08-04-allocation-vignette.png`, script `2026-08-04-allocation-vignette.py`.

### EXP-016 — 2026-09-02 — R-Phase 1: causally corrected feature pipelines (v2), both cities
- **Purpose:** close audit issues S01 (split-boundary target leakage), S02/X01 (Birmingham cross-night
  construction), and the disclosure gap on interpolation rates. See D-014; plan in
  `2026-09-02-audit-validation-and-remediation-plan.md`.
- **Scripts (new; v1 builders and v1 parquets left untouched):**
  `03_code/src/features/2026-09-02-build_features_v2.py`,
  `03_code/src/features/2026-09-02-build_features_birmingham_v2.py`,
  `03_code/tests/2026-09-02-test_split_integrity.py`.
- **Outputs:** `01_data/processed/{belgrade,birmingham}_features_v2.parquet` (+ `*_v2_report.json`),
  `05_results/tables/2026-09-02-split-integrity-report.json`,
  `05_results/tables/2026-09-02-v2-representativeness.csv`.
- **Design changes:** explicit `target_ts_{H}`; per-horizon masks `use_{H} = split_ok_{H} & embargo_ok_{H}`
  (same-split constraint + h-step boundary embargo) rather than row deletion, so short horizons keep their
  sample size; Birmingham resampled and interpolated **within facility-day sessions only** (1,973 sessions),
  making cross-night construction impossible by design; provenance columns `occ_interpolated`,
  `target_interpolated_{H}`. Grid, lags, rolling windows, calendar features, horizons, split cutoffs,
  sparse-facility exclusion and negative clipping are unchanged, so the causal structure is the only delta.

| City | Horizon | Usable rows (v2) | % of v1 | Anchor interp. | Target interp. | Cross-split targets |
|---|---|---|---|---|---|---|
| Belgrade | t+5 | 92,448 | 99.90% | 0.00% | 0.00% | 0 |
| Belgrade | t+15 | 92,256 | 99.69% | 0.00% | 0.00% | 0 |
| Belgrade | t+30 | 91,968 | 99.38% | 0.00% | 0.37% | 0 |
| Birmingham | t+30 | 17,487 | 90.00% | 26.27% | 26.25% | 0 |
| Birmingham | t+60 | 17,487 | 90.00% | 26.27% | 26.82% | 0 |
| Birmingham | t+90 | 17,487 | 90.00% | 26.27% | 25.21% | 0 |

- **Key results:**
  1. **Belgrade cost is negligible.** 480 cross-split targets across the three horizons in v1 are now
     blocked; combined with the embargo, ≥99.4% of rows survive at every horizon. The headline Belgrade
     sample is effectively unchanged, so S01 should not move Belgrade numbers.
  2. **Birmingham loses exactly 1,942 rows (10.0%)** — precisely the count of rows whose t+90 target had
     been interpolated across a night in v1. The session-safe build removes the contaminated rows by
     construction; the match to the independently measured figure is exact.
  3. **Interpolation is pervasive but benign and within-day:** 26.3% of retained Birmingham slots are
     interpolated, a consequence of ~33-min native sampling on a 30-min grid, not of the night bug.
     Belgrade is 0% (2-min source on a 5-min grid). This rate was never reported and must appear in
     Table 1 or the ESM.
- **Gate:** `2026-09-02-test_split_integrity.py` — **43/43 checks PASS**, exit 0. Covers duplicate
  timestamps, per-facility monotonicity, exact target arithmetic, same-split constraint on used rows,
  embargo, Birmingham session containment, no cross-day targets, flag typing, and a v1-regression witness.
- **Read:** the corrected Belgrade sample is ~unchanged (expect ~unchanged results); Birmingham t+90 is the
  row to watch when Phase 3 reruns, since 10% of its sample was contaminated.
- **Next:** R-Phase 2 — shared tested conformal core (`core.py`), then rerun (R-Phase 3 gate).

### EXP-017 — 2026-09-02 — R-Phase 2/3: shared conformal core + first corrected rerun (4 core methods)
- **Purpose:** close audit issues C01 (order statistic), C02 (unprojected state), C06 (immediate feedback)
  and I06 (bootstrap design) by consolidating every primitive into one tested module, then rerun
  split-CP / CQR / ACI / ACQR on the v2 causal feature tables. D-014; see EXP-016 for the data fix.
- **New code:** `03_code/src/conformal/core.py` (conformal_quantile, AdaptiveState with projection,
  ReleaseQueue, one `adaptive_conformal_stream` serving both ACI and ACQR, metrics, cadence-derived
  moving-block bootstrap, quantile-crossing repair);
  `03_code/src/conformal/2026-09-02-run-core-methods.py` (canonical runner, supersedes `run_corrected.py`
  and `2026-08-04-adaptive-cqr.py`); `03_code/tests/2026-09-02-test_conformal_core.py`.
- **Retired** to `03_code/src/conformal/_retired/` (moved, not deleted; see its README): `model_agnostic.py`
  (the C06 offender), `aci_cp.py`, `split_cp_baseline.py`, `run_all_facilities.py`, `run_delta_cp.py`,
  `run_delta_cp_birmingham.py`, `conditional_cp.py`, `trust_abstain.py`, `_fac3_corrected.py`.
- **Gate:** property suite **20/20 PASS**, including the decisive no-lookahead test (perturbing y at step t
  leaves every bound before t+h bit-identical, and does change the bound at t+h) and a synthetic-shift
  validation (split-CP 0.673, adaptive 0.896 against a 0.90 target).
- **Environment recorded** in `05_results/tables/2026-09-02-environment.json` (Python 3.10.12,
  numpy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, scipy 1.15.3). The archived numbers came from an
  unpinned older stack (R01), so the runner takes `--features v1|v2` to separate code from data effects.

**Headline comparison @90%, dynamic facilities (old -> corrected):**

| City | Method | PICP | std | MPIW | Winkler | at target (old rule) |
|---|---|---|---|---|---|---|
| Belgrade t+15 | split-CP | 0.900→0.899 | 0.041→0.041 | 16.8→16.8 | 26.9→26.8 | 64%→64% |
| Belgrade t+15 | CQR | 0.904→0.899 | 0.030→0.028 | 13.0→12.5 | 20.4→20.1 | 64%→77% |
| Belgrade t+15 | ACI | 0.899→**0.886** | 0.001→0.006 | 17.6→14.7 | 24.2→22.3 | 100%→100% |
| Belgrade t+15 | ACQR | 0.899→**0.887** | 0.002→0.005 | 16.7→13.8 | 22.1→**20.1** | 100%→**91%** |
| Birmingham t+60 | split-CP | 0.903→0.907 | 0.050→0.051 | 136.8→134.4 | 181.6→175.4 | 79%→71% |
| Birmingham t+60 | CQR | 0.904→0.902 | 0.039→0.042 | 141.6→135.3 | 174.0→172.7 | 71%→75% |
| Birmingham t+60 | ACI | 0.892→0.888 | 0.009→0.009 | 144.0→132.6 | 187.9→176.3 | 100%→100% |
| Birmingham t+60 | ACQR | 0.893→0.891 | 0.010→0.014 | 143.9→136.6 | 181.1→176.8 | 100%→100% |

- **Attribution (controlled test, 8 Belgrade facilities, identical data/seed, only the quantile rule
  differing):** PICP 0.8988 → 0.8858 (−0.0129), MPIW −15.4%, Winkler −7.8%. **The entire shift is the C01
  fix.** The data fixes contribute ~nothing on Belgrade, as EXP-016 predicted (0.3% of rows).
- **Interpretation — two findings, opposite signs:**
  1. **The efficiency penalty largely disappears.** Belgrade t+15 ACQR Winkler 22.1 → 20.1, equal to CQR's
     20.1, with per-facility std 0.005 vs CQR's 0.028. The retired bug had been inflating our own adaptive
     intervals by ~15%, so the "reliability costs 8% efficiency" trade-off was partly an artifact.
  2. **The adaptive family now slightly under-covers** (0.886–0.891 against 0.90). The retired +1-rank
     padding had been masking a real property of delayed multi-step ACI: with h-step feedback the control
     loop lags during clustered misses. "Statistically at target at every facility" is no longer supportable
     — ACQR Belgrade falls to 91% even under the lenient retired criterion.
- **Phase-4 criterion preview** (`2026-09-02-phase4-criterion-preview.csv`, eps = 0.02): the adaptive family
  scores 0% on both SAFE (lower CI bound ≥ 0.88) and EXACT (CI inside [0.88, 0.92]); split-CP/CQR score
  25–41% SAFE and 0% EXACT. **Every method scores 0% EXACT**, which is a POWER problem, not a method
  problem: at n≈1,100 test points per facility with 3-hour blocks the CI half-width is ≈ ±0.02–0.03, so no
  CI can fit inside a ±0.02 band. The equivalence design needs revisiting in R-Phase 4.
- **Not yet rerun:** EnbPI / AgACI-style / NGBoost, ToD-ACI, trust/abstain, rolling-origin, vignette,
  base-learner robustness.
- **Read:** the per-facility *dispersion* result — the paper's actual thesis — survives and is if anything
  cleaner. The *"exactly at target everywhere"* claim does not survive. Gate decision required.

### EXP-018 — 2026-09-02 — Is the multi-step under-coverage a tuning artifact or intrinsic? (R-Phase 3 gate)
- **Question:** EXP-017 found corrected ACI/ACQR under-cover, worsening with the feedback delay h. Can the
  step size γ or the score-window length buy the coverage back, and at what width cost?
- **Design:** Belgrade and Birmingham v2 tables, 90%, 8–10 dynamic facilities, all three horizons;
  γ ∈ {0.002, 0.005, 0.01, 0.02, 0.05, 0.10}; window ∈ {½, 1, 2}× calibration size (window had almost no
  effect and was collapsed to 1× for the fine grid). split-CP is the control: it has no feedback loop, so
  it isolates the delay mechanism. Script `2026-09-02-delay-sensitivity.py`; outputs
  `2026-09-02-delay-sensitivity-{belgrade,birmingham}.csv`.
- **Free prior test (from EXP-017 runs): the shortfall is monotone in h in BOTH cities.**
  Belgrade ACI 0.8952 / 0.8858 / 0.8718 at h = 1 / 3 / 6; Birmingham 0.8938 / 0.8882 / 0.8826 at h = 1 / 2 / 3.
  split-CP and CQR stay flat at ~0.90 at every horizon. A dose-response in two independent cities, absent
  from the two methods that have no feedback loop.

**Belgrade — γ × h interaction (mean PICP; MPIW in parentheses):**

| γ | h=1 | h=3 | h=6 |
|---|---|---|---|
| 0.002 | 0.8977 (12.3) | 0.8998 (27.1) | 0.9056 (40.3) |
| 0.005 | 0.8979 (11.4) | 0.8990 (26.1) | **0.9006 (40.2)** |
| 0.010 | 0.8979 (10.9) | 0.8954 (25.6) | 0.8944 (39.4) |
| 0.020 | 0.8971 (10.4) | 0.8931 (24.4) | 0.8876 (38.1) |
| **0.050 (project default since EXP-002)** | 0.8953 (9.5) | 0.8858 (22.8) | 0.8718 (37.2) |
| 0.100 | 0.8890 (9.4) | 0.8704 (22.6) | 0.8468 (36.3) |
| split-CP control | 0.8866 (10.3) | 0.8841 (26.1) | 0.8888 (41.5) |

Coverage cost of γ = 0.05 versus γ = 0.005: **−0.26 pts at h=1, −1.32 at h=3, −2.88 at h=6.**

**Birmingham — γ has essentially NO effect:** cost of γ = 0.05 vs 0.005 is +0.36 / −0.06 / −0.01 pts at
h = 1 / 2 / 3. Coverage sits at 0.88–0.89 for every γ.

- **Two distinct mechanisms, now separated:**
  1. **Step-size × delay (Belgrade, long continuous streams).** With h-step delayed feedback a large γ
     over-reacts during clustered misses and the correction arrives too late, producing a systematic
     coverage debt that scales with h. It is a TUNING failure, not a method failure: at γ = 0.005 coverage
     is 0.898 / 0.899 / 0.901 across the three horizons **and** MPIW is at or below split-CP at h = 3 and
     h = 6. The direction is counter-intuitive — smaller γ is better — which is presumably why the default
     went unquestioned.
  2. **Insufficient online convergence (Birmingham, ~128 test steps per facility on daytime-only
     sessions).** No γ helps, because the recursion never gets a long enough stream. The manuscript already
     flags this qualitatively ("shorter daytime-only test sequences limiting online convergence"); this
     quantifies it and shows it is a different failure from mechanism 1.
- **Literature anchor:** Wang & Hyndman (2024/2026, AcMCP, arXiv:2410.13115 — already in `references.bib`)
  prove that for finite samples the coverage error of online conformal methods "admits an upper bound that
  increases with the forecasting horizon", and propose a PID-style correction (proportional + integral +
  MA(h−1) autocorrelation). Our measurement is an independent empirical confirmation on real transportation
  data, in two cities, with an explicit dose-response — and it identifies the step size as the lever.
  A second 2024 paper (arXiv:2409.14792) allows per-step error and learning rates, consistent with our
  conclusion that γ must be indexed by h.
- **CRITICAL PROTOCOL NOTE for R-Phase 3b:** γ = 0.005 must NOT be adopted by reading it off this table —
  that is test-set tuning, exactly the class of error this audit exists to remove. γ is to be selected
  **per facility and horizon on the calibration set only** (prequentially), and the sensitivity surface
  reported as a finding in its own right.
- **Read:** the under-coverage is real, explained, and largely remediable on Belgrade; on Birmingham it is
  a genuine limit of short daily sessions. Either way the paper gains a mechanism and a deployment rule it
  did not previously have.

### EXP-019 — 2026-09-02 — Calibration-selected step size (honest remedy for the EXP-018 debt)
- **Protocol (the point of this experiment):** γ is chosen per facility and horizon by a NESTED TEMPORAL
  SPLIT of the calibration set — earlier segment cal-A seeds the score pool, later segment cal-B is
  replayed as a pseudo-test stream, γ minimises |PICP(cal-B) − target| with Winkler as tie-break.
  **The test set is never touched.** Reading γ = 0.005 off the EXP-018 test surface would have been
  test-set tuning; this is the deployable version of the same idea. The same nested split is what audit
  issue C04 requires for the trust/abstain thresholds, so both now share one protocol.
  Implemented as `core.select_gamma_on_calibration`; runner flag `--gamma-mode calibrated` (now default).
- **Artifacts:** `2026-09-02-core-{belgrade,birmingham}-gcal-per-facility.csv`,
  `2026-09-02-corrected-headline-gcal.csv`. Property suite still 20/20.

**Fixed γ = 0.05 → calibration-selected γ (mean PICP, dynamic facilities, 90%):**

| City | h | ACI | ACQR | median γ chosen |
|---|---|---|---|---|
| Belgrade t+5 | 1 | 0.8952 → 0.8939 | 0.8962 → 0.8966 | **0.050** |
| Belgrade t+15 | 3 | 0.8858 → **0.8929** | 0.8866 → **0.8931** | **0.020** |
| Belgrade t+30 | 6 | 0.8718 → **0.8891** | 0.8710 → **0.8914** | **0.010** |
| Birmingham t+30 | 1 | 0.8938 → 0.8940 | 0.8959 → 0.8952 | 0.050 |
| Birmingham t+60 | 2 | 0.8882 → 0.8890 | 0.8913 → 0.8928 | 0.050 / 0.020 |
| Birmingham t+90 | 3 | 0.8826 → 0.8763 | 0.8859 → 0.8846 | 0.020 |

- **The result that makes this publishable:** the median γ selected **on calibration data alone** falls
  monotonically with the horizon — 0.050 at h=1, 0.020 at h=3, 0.010 at h=6. The calibration set
  independently rediscovers the horizon-scaling rule that EXP-018 found on test data. That is
  self-validating evidence that the mechanism is real, and — more importantly for a transportation
  audience — that it is **learnable in deployment** without ever seeing the outcomes you are calibrating
  for. It recovers 1.7–2.0 coverage points at Belgrade t+30 at negligible width cost
  (ACQR Winkler 33.4 → 32.9; at t+15, 20.1 → 19.8, still level with CQR's 20.1).
- **Belgrade / Birmingham asymmetry confirmed again:** γ selection helps only where the mechanism is
  step-size × delay. On Birmingham's ~128-step daily sessions it changes nothing (and at t+90 drifts
  slightly worse, 0.883 → 0.876 — honest selection variance on short streams). Two mechanisms, one
  remediable, one a structural limit of daytime-only data.
- **Residual debt is NOT eliminated:** corrected PICP is 0.889–0.893, not 0.900. Report as such.

**Corrected headline @90% (calibration-selected γ):**

| City / horizon | Method | PICP | std | Winkler | CI-contains | SAFE (lower bound ≥ 0.88) |
|---|---|---|---|---|---|---|
| Belgrade t+15 | split-CP | 0.899 | 0.041 | 26.8 | 64% | 41% |
| Belgrade t+15 | CQR | 0.899 | 0.028 | 20.1 | 77% | 36% |
| Belgrade t+15 | ACI | 0.893 | 0.011 | 24.2 | 91% | 5% |
| Belgrade t+15 | **ACQR** | 0.893 | **0.007** | **19.8** | 95% | 0% |
| Birmingham t+60 | split-CP | 0.907 | 0.051 | 175.4 | 71% | 25% |
| Birmingham t+60 | CQR | 0.902 | 0.042 | 172.7 | 75% | 25% |
| Birmingham t+60 | ACI | 0.889 | 0.015 | 175.3 | 100% | 4% |
| Birmingham t+60 | **ACQR** | 0.893 | 0.023 | 176.3 | 89% | 11% |

- **Dispersion ratio (split-CP std ÷ ACQR std): 6.2× Belgrade, 2.2× Birmingham.** The paper's spine.
- **Honest tension to resolve in R-Phase 4:** on the one-sided SAFE criterion (lower CI bound ≥ 0.88) the
  adaptive family scores WORSE than split-CP/CQR (0–11% vs 25–41%), because it sits a little below nominal
  everywhere while split-CP scatters on both sides. Dispersion and safety are genuinely different
  questions and the paper must report both rather than choosing the flattering one. This is exactly the
  separation audit issue I01 demanded, and it materially complicates the "use the adaptive family"
  recommendation — a conservative method that scatters high can be safer than a precise one that sits low.
- **Next:** R-Phase 3b remainder — base learners (C06), ToD (C05), trust/abstain (C03/C04), E3 (C07),
  rolling-origin (I04/I05), vignette (D01).

### EXP-020 — 2026-09-03 — R-Phase 3b task 1: base-learner robustness on the shared core (Belgrade, t+15)
- **Purpose:** close audit issue **C06**. The manuscript's Section 5.4 robustness sentence was generated by
  `model_agnostic.py` — the one script in the project that updated the ACI state immediately within the
  same iteration, violating our own delay-aware protocol — and its output
  `2026-06-21-model-agnostic.csv` supplied the published numbers verbatim (ACI std 0.0012/0.0011/0.0010 →
  "std ≤ 0.002"; split-CP Ridge std 0.1027 → "std 0.103").
- **Script (new; the 2026-08-04 originals and `_ma_delay.py` untouched):**
  `03_code/src/conformal/2026-09-03-base-learner-robustness.py`. Resumable (`--budget`, resume keyed on
  facilities already in the per-facility CSV, `SKIPPED-*` marker rows, `REMAINING`/`ALL DONE`).
- **Outputs:** `05_results/tables/2026-09-03-base-learner-robustness-per-facility.csv` (288 rows,
  24 facilities, 22 dynamic) and `05_results/tables/2026-09-03-base-learner-robustness.csv`
  (archived schema, dynamic facilities only, for a direct before/after delta).
- **Protocol:** every primitive from `core.py` — delayed feedback via `ReleaseQueue` (h = 3 steps) [C06],
  direct k-th order statistic [C01], projected adaptive state [C02]; reads `belgrade_features_v2.parquet`
  filtered by `use_15` [S01]; γ per facility and level from `core.select_gamma_on_calibration`
  (nested cal-A/cal-B, n_cal_b = 380, test never touched). All facilities evaluated and tagged `dynamic`
  rather than filtered up front [D05].
- **Controlled comparison:** learner hyperparameters held at the ARCHIVED values (RF n_estimators=100
  min_samples_leaf=2; HistGBR **max_iter=200**, not `_ma_delay.py`'s 150; Ridge alpha=1.0), so the delta is
  attributable to the protocol and quantile fixes, not to a hyperparameter change. Two deliberate
  residual differences: intervals clipped at 0 (occupancy cannot be negative; the retired script did not
  clip) and v2 rather than v1 features (EXP-016 measured the Belgrade v2 cost at ≤ 0.6% of rows).

**Archived (immediate feedback) → corrected (delay-aware), 22 dynamic facilities:**

| base | level | method | meanPICP | stdPICP | MPIW | Winkler |
|---|---|---|---|---|---|---|
| RandomForest | 0.90 | split-CP | 0.8998→0.8992 | 0.0403→0.0399 | 17.32→16.77 | 27.42→26.83 |
| RandomForest | 0.90 | ACI | 0.8991→**0.8929** | 0.0012→**0.0106** | 15.20→15.97 | 20.73→24.23 |
| RandomForest | 0.95 | split-CP | 0.9470→0.9463 | 0.0362→0.0358 | 23.26→22.24 | 34.21→33.42 |
| RandomForest | 0.95 | ACI | 0.9495→0.9447 | 0.0013→0.0079 | 20.72→21.19 | 27.06→30.64 |
| GradBoost | 0.90 | split-CP | 0.8997→0.8992 | 0.0420→0.0410 | 17.49→16.96 | 27.93→27.60 |
| GradBoost | 0.90 | ACI | 0.8993→**0.8924** | 0.0011→**0.0049** | 15.49→15.71 | 21.54→24.06 |
| GradBoost | 0.95 | split-CP | 0.9487→0.9455 | 0.0283→0.0308 | 23.29→22.46 | 34.38→34.03 |
| GradBoost | 0.95 | ACI | 0.9496→0.9451 | 0.0011→0.0067 | 21.00→21.87 | 27.57→31.90 |
| Ridge(linear) | 0.90 | split-CP | 0.8837→0.8835 | 0.1027→**0.1030** | 15.90→15.59 | 25.98→25.70 |
| Ridge(linear) | 0.90 | ACI | 0.8991→**0.8880** | 0.0010→**0.0126** | 15.23→15.53 | 20.51→23.95 |
| Ridge(linear) | 0.95 | split-CP | 0.9387→0.9386 | 0.0444→0.0446 | 20.97→20.49 | 32.03→31.61 |
| Ridge(linear) | 0.95 | ACI | 0.9497→0.9401 | 0.0011→0.0111 | 20.33→19.82 | 26.24→30.28 |

- **The manuscript sentence is DEAD as written.** "ACI std ≤ 0.002 across base learners" was an artifact of
  immediate feedback: with the delay restored the across-facility std is **0.0049–0.0126 at 90%**, four to
  ten times larger. No wording of the current sentence survives.
- **The underlying claim survives in a weaker, defensible form.** At 90% the adaptive family's
  across-facility dispersion is still **3.8× / 8.4× / 8.2×** lower than split-CP on the same learner
  (0.0106 vs 0.0399 RF; 0.0049 vs 0.0410 GBM; 0.0126 vs 0.1030 Ridge), and ACI beats split-CP on Winkler
  in all six configurations. The model-agnostic *reliability-stability* result is real; only its magnitude
  was inflated.
- **`split-CP Ridge std 0.103` is CONFIRMED** (0.1027 → 0.1030). split-CP is touched by neither C01 nor
  C06, exactly as predicted — a useful negative control on the whole correction.
- **Coverage falls to 0.888–0.893 at 90%** (0.940–0.945 at 95%), matching the residual debt EXP-019
  reported. The base-learner table no longer supports any "at target" phrasing either.
- **Independent cross-check:** this script's RandomForest arm reproduces the canonical runner
  (`2026-09-02-core-belgrade-gcal-per-facility.csv`, EXP-019) to four decimals on the same 22 dynamic
  facilities — split-CP PICP 0.8992 (std 0.0399) and ACI PICP 0.8929 (std 0.0106) in both. Two
  independently written scripts on the same core agree exactly. The median γ selected here (0.020 at 90%)
  also reproduces EXP-019's Belgrade t+15 median of 0.020.
- **Verification:** decisive no-lookahead witness re-run on this script's exact call path (facility 2,
  γ = 0.002): perturbing the outcome at step t leaves every bound before t+h bit-identical and the first
  divergence occurs at **exactly** t+h. Frozen manifest re-checked after the run — 130 files, zero drift.
  *(Note: facility 1 is degenerate — constant occupancy, all-zero score pool, q ≡ 0 — so it cannot serve as
  a witness; its α state does still shift at exactly t+h. It is one of the 2 non-dynamic facilities and is
  excluded from the summary, retained in the per-facility CSV per D05.)*
- **Read:** C06 is closed. Section 5.4 must be rewritten in R-Phase 7 around "3.8–8.4× lower
  across-facility dispersion than split-CP at every base learner, at 0.888–0.893 coverage", never
  "std ≤ 0.002". Ridge remains the persuasive case: split-CP's reliability collapses to std 0.103 under a
  weak learner while the adaptive family holds at 0.013.
- **Next:** R-Phase 3b task 2 — time-of-day conditional (C05, I03).

**EXP-020 addendum (same day) — self-audit of the run, four findings:**

1. **Second negative control, free: the base learners themselves did not move.** Mean test MAE
   RandomForest 3.41→3.40, GradBoost 3.57→3.58, Ridge 3.42→3.42. The point predictors are unchanged, so
   the entire delta lives in the conformal layer — it cannot be a base-model or library-drift artifact.
   Together with the unchanged split-CP Ridge std this is two independent controls on the correction.
2. **Degenerate-facility flag added (gap in the first run, now fixed).** Facility 1 has an identically
   zero calibration score pool: q ≡ 0, MPIW = 0, and PICP is *vacuously* 1.0. It is non-dynamic so it never
   entered the summary, but it sat unflagged in the per-facility table, where the planned **D05
   all-facility sensitivity** would later have absorbed it as if it were evidence — inflating both mean
   coverage and dispersion. The script now records `degenerate` and `cal_score_max` per row and excludes
   degenerate facilities from the summary. Rerun to regenerate: **PICP identical for all 288 rows**;
   MPIW/Winkler/MAE differ by ≤ 5.7e-14 on 7 rows, all RandomForest, i.e. thread-reduction-order float
   noise from `n_jobs=-1` — fifteen orders of magnitude below any reported digit. Superseded originals
   kept in `05_results/tables/_superseded/` with a README. *(Useful for R-Phase 6: the pipeline is
   reproducible to ~1e-14 on the same machine, and the only nondeterminism is threaded RF.)*
3. **LIMITATION — the γ grid saturates at its lower boundary.** Of 66 dynamic facility × learner
   selections at 90%, **11 (17%) choose the grid minimum γ = 0.002** and 3 (5%) choose the maximum 0.10
   (at 95%: 12% and 5%). A selection at the boundary means the calibration optimum may lie outside the
   grid, so those facilities are not actually optimised — they are clipped. `core.GAMMA_GRID` is shared,
   so it would affect EXP-019's headline numbers too, not only EXP-020.
   **MEASURED, not assumed — and it turns out to be immaterial.** Re-selecting on a grid extended down to
   2e-4 for the RandomForest facilities that clipped (3 of 22 at 90%): 2 of 3 moved below the old floor,
   and the effect on test coverage is **+0.0010 mean PICP for +0.17 Winkler** — inside noise, and not even
   consistently favourable (facility 17 went 0.8897 → 0.8887). The coverage debt is therefore NOT an
   artifact of the grid floor, which independently strengthens EXP-018's reading that the residual debt on
   Belgrade is structural rather than tuning-limited.
   **Resolution: keep `core.GAMMA_GRID` as prespecified, report the floor and this sensitivity check in
   the ESM. No rerun of EXP-019 or the γ-dependent R-Phase 3b tasks is required.**
4. **LIMITATION — γ selection is noisy at the 95% level.** cal-B is 380 rows for every Belgrade facility,
   so a single miss moves cal-B PICP by 0.0026; at 95% only ≈19 misses are expected in the whole segment.
   The selection criterion |PICP(cal-B) − target| is therefore resolving differences comparable to its own
   sampling noise, which is consistent with the flatter, boundary-heavy γ distribution seen at 95%. The
   90% selections (≈38 expected misses) are better resolved. A related asymmetry deserves a sentence in
   the paper: γ is chosen while replaying cal-B against a **380**-score pool but deployed at test time
   against a **760**-score pool. Both belong in the R-Phase 4 inference redesign.

### EXP-021 — 2026-09-03 — R-Phase 3b task 2: time-of-day conditional coverage (Belgrade, t+15, 90%)
- **Purpose:** close **C05** (every ToD bucket was initialised from the same GLOBAL residual pool, so
  "group-conditional (Mondrian-style)" overstated the implementation) and **I03** (Table 4 pooled over
  facilities before reporting bucket coverage — the paper's own thesis is that pooling hides
  facility-level failure, so the table contradicted the argument it was supporting).
- **New code:** `core.grouped_adaptive_conformal_stream` — per-group score pool AND per-group adaptive
  state, one shared release queue carrying the ISSUING group so delayed feedback returns to the group
  that made the forecast; shrinkage fallback (own scores ∪ global pool) for groups below `min_group`,
  with per-group counts in the diagnostics. Also fixes an inconsistency in the retired code, where
  ToD-ACI let each bucket's pool grow unbounded while global ACI applied a window.
- **Property gate extended 20/20 → 27/27** (`tests/2026-09-02-test_conformal_core.py`), including the
  decisive reduction test **P14: the grouped stream with one group is bit-identical to the ungrouped
  stream**, plus per-group feedback routing, delayed release, fallback-is-a-union, and P17: each group
  opens on its own calibration quantile to 1e-12. Split-integrity suite still 43/43.
- **Script:** `03_code/src/conformal/2026-09-03-tod-conditional.py` (resumable, SKIPPED markers,
  `--min-group`, `--min-cell`). **Outputs:** `2026-09-03-tod-facility-bucket.csv` (the I03 deliverable),
  `2026-09-03-tod-summary.csv`.
- **γ:** selected per facility by `core.select_gamma_on_calibration` and shared by ACI and ToD-ACI.
  Deliberately NOT per bucket: cal-B is ~380 rows per facility, so a per-bucket selection would run on
  ~76 rows and resolve differences smaller than its own sampling noise (see the EXP-020 addendum). The
  step size is a control-loop gain; the bucket-specific quantities are the pool and the state.

**THE NEW TABLE 4 — facility × bucket coverage distribution (110 cells = 22 dynamic facilities × 5 buckets):**

| method | mean | sd | min | p10 | max | range | cells <0.85 | cells <0.80 | MPIW |
|---|---|---|---|---|---|---|---|---|---|
| split-CP | 0.8987 | 0.0993 | **0.5160** | 0.7745 | 1.0000 | 0.484 | 23 | 14 | 16.81 |
| Mondrian-split-CP | 0.8965 | 0.0772 | 0.6200 | 0.7684 | 1.0000 | 0.380 | 23 | 15 | 15.13 |
| ACI (global) | 0.8930 | 0.0753 | 0.6720 | 0.7916 | 1.0000 | 0.328 | 33 | 12 | 16.21 |
| **ToD-ACI** | 0.8982 | **0.0280** | **0.8421** | 0.8677 | 1.0000 | **0.158** | **3** | **0** | 16.22 |

- **This is the strongest result the project has produced, and it rescues Table 4 from contradicting the
  paper.** split-CP reports a respectable marginal 0.899 while **14 of its 110 facility-bucket cells fall
  below 0.80 coverage and its worst cell is 0.516** — a near coin flip at a 90% nominal level. ToD-ACI has
  **zero cells below 0.80**, three below 0.85, and a worst cell of 0.842 — at essentially the same mean
  width (16.22 vs 16.81; it is in fact *narrower* than split-CP).
- **What pooling hid, quantified:** split-CP's worst POOLED bucket is 0.8335 (midday); its worst
  FACILITY-BUCKET is **0.5160** (facility 9, midday, n = 250). The pooled table understated the worst
  observed failure by 32 coverage points. This is exactly the I03 claim, now demonstrated with our own data.
- **Facility 9 is the worked example the paper needs:** split-CP gives 0.516 at midday and 0.556 at
  pm_rush there, while reporting 0.899 marginally. ToD-ACI gives 0.892 and 0.842 in the same cells.
- **Night-bucket over-coverage is removed at a large width saving:** split-CP 0.973 at MPIW 17.04 →
  ToD-ACI 0.907 at MPIW **10.48** (38% narrower, and closer to nominal). Wasted width, not just miscalibration.
- **Honest complication — global ACI is worse than split-CP on the conditional criterion.** ACI has the
  lower sd (0.0753 vs 0.0993) yet **33** cells below 0.85 against split-CP's 23, because it sits slightly
  low nearly everywhere while split-CP scatters both ways. This is the same
  marginal-vs-conditional tension EXP-019 found on the SAFE criterion, reappearing on a second axis. It
  strengthens the case for the *conditional* variant specifically rather than for adaptivity in general —
  and that distinction should drive the practitioner recommendation.
- **CAVEAT — NOW ADDRESSED BY EXP-022 (read that entry before quoting any number here):** ToD-ACI conditions on time-of-day and
  is then *evaluated* by time-of-day coverage, so part of its advantage is definitional. The two claims
  that do NOT depend on the conditioning variable are (i) the width cost is nil, and (ii) pooling hides
  catastrophic cells. **Recommended before submission:** re-evaluate the same runs on an ORTHOGONAL
  partition the method does not condition on (day-of-week, or occupancy-level tercile). If ToD-ACI's
  advantage survives there, the result generalises; if it does not, the claim must be narrowed to
  "conditioning on the axis you care about works". A reviewer will raise this.
  **Outcome (EXP-022): the advantage is real but axis-dependent.** ToD-ACI removes 99% of time-of-day
  conditional structure, 81% of occupancy-tercile structure (Cramér's V 0.59 with ToD) and 45% of
  day-of-week structure (V 0.15) — a dose-response in the association between the evaluation axis and the
  conditioning axis. Global ACI actually beats ToD-ACI on day-of-week. Quote EXP-021's headline only
  alongside that transfer rule.
- **Shrinkage fallback never fired on Belgrade:** the smallest own-bucket calibration pool is 96 scores
  (threshold 50), so all 115 cells used their own pool. The machinery is property-tested but dormant here;
  it will matter if ToD is ever run on Birmingham, whose daytime-only sessions leave the night bucket empty.
- **Next:** R-Phase 3b task 3 — trust/abstain (C03, C04, D04).

### EXP-022 — 2026-09-03 — Adversarial check on EXP-021: does the conditional advantage survive off-axis?
- **Purpose:** EXP-021 evaluated ToD-ACI by time-of-day coverage while ToD-ACI *conditions* on time of day,
  so part of its margin is definitional. A referee will say so. This experiment scores the **identical
  intervals** (same seed, features, γ, conditioning) on four partitions of the same test rows.
- **Script:** `03_code/src/conformal/2026-09-03-orthogonal-partition-check.py`. **Outputs:**
  `2026-09-03-orthogonal-partition-{cells,summary}.csv`.
- **Design — the two things that make this interpretable:**
  1. **Association is measured, not assumed.** Cramér's V of each partition against the ToD buckets:
     time_of_day 1.000, occupancy_tercile 0.588, day_of_week 0.153, random_5 0.061. Occupancy is *driven*
     by time of day, so it is only partly orthogonal — treating it as independent would have been wrong.
  2. **A matched noise floor.** `random_5` uses seeded random labels with the same cell count (and hence
     cell size) as the ToD partition. Dispersion there is pure sampling noise plus facility-level
     differences, and it is **not the same for every method** (split-CP 0.0442, ToD-ACI 0.0266). Comparing
     raw dispersion across methods without this baseline would have overstated the effect.
  Excess structure is then `sqrt(max(sd_partition² − sd_random², 0))` — the conditional miscoverage a
  method failed to remove, net of noise.

**RESULT — a clean dose-response: conditional validity transfers in proportion to association.**

| evaluation axis | Cramér's V vs ToD | split-CP excess sd | ToD-ACI excess sd | structure removed |
|---|---|---|---|---|
| time_of_day | 1.000 | 0.0889 | **0.0087** | **99%** |
| occupancy_tercile | 0.588 | 0.0961 | 0.0424 | **81%** |
| day_of_week | 0.153 | 0.0522 | 0.0386 | **45%** |

- **On its own axis ToD-ACI does not merely reduce conditional miscoverage — it eliminates it.** Excess
  dispersion 0.0087 against a noise floor of 0.0266: the ToD-conditional structure is gone, and what
  remains is indistinguishable from sampling noise.
- **The advantage is real but NOT free off-axis.** The claim that survives is precise and quantitative:
  *conditioning buys conditional validity on the axis you condition on, and on other axes in proportion to
  their association with it.* That is a stronger contribution than "ToD-ACI is more reliable" — it is a
  measurable deployment rule, and it is the project's **second** dose-response (the first being γ × horizon
  in EXP-018).
- **HONEST FINDING AGAINST US: global ACI beats ToD-ACI on day-of-week.** Excess sd 0.0304 vs 0.0386
  (1.72× vs 1.35× relative to split-CP), and a marginally better worst cell (0.774 vs 0.771). Conditioning
  on the wrong axis costs a little off-axis performance. This must be reported; it also means the
  practitioner recommendation is "choose the conditioning axis to match the axis your application cares
  about", not "always condition".
- **Worst-cell protection DOES hold on every partition**, which is the facility-level advantage showing
  through and is independent of the conditioning axis:

| partition | split-CP | ACI | ToD-ACI |
|---|---|---|---|
| time_of_day | 0.516 | 0.672 | **0.842** |
| day_of_week | 0.688 | **0.774** | 0.771 |
| occupancy_tercile | 0.582 | 0.744 | **0.767** |
| random_5 | 0.732 | 0.825 | **0.831** |

- **LIMITATION FOUND, AND IT IS BIGGER THAN THIS EXPERIMENT: the Belgrade test window is only 4 calendar
  days** (2017-03-18 → 2017-03-21; Sat, Sun, Mon, Tue). Consequences: (i) day_of_week has only four levels
  and each weekday occurs exactly once, so "day-of-week effect" is fully confounded with "which day" —
  the 45% figure is the weakest leg of the dose-response and should be reported as indicative only;
  (ii) the ToD and tercile arms are unaffected, since those cells recur within every day; (iii) more
  broadly this is the same short-horizon sample that drives the **R-Phase 4 power problem** (n ≈ 1,015
  test rows per facility, no CI fits inside a ±0.02 band). **Action: re-run this check on the
  rolling-origin folds in R-Phase 3b task 5, which supply 3× the test days and would give day-of-week a
  properly replicated test.**
- **Also noted:** Mondrian-split-CP has a *higher* noise floor than split-CP (0.0572 vs 0.0442) — its
  per-bucket calibration quantiles are estimated on ~1/5 the data and are correspondingly noisier. Its
  apparent dispersion advantage in EXP-021 was therefore partly an artifact of a noisier baseline; net of
  noise it removes only 42% of ToD structure against ToD-ACI's 99%.
- **Read:** EXP-021's headline survives, with the wording narrowed and made quantitative. The paper gains a
  measured transfer rule and loses an overclaim it would have been challenged on.
- **Next:** R-Phase 3b task 3 — trust/abstain (C03, C04, D04).

### EXP-023 — 2026-09-03 — Is the equivalence-test power failure a data problem or an estimand problem?
- **Purpose:** EXP-017 reported that under the prespecified ε = 0.02 criterion **every method scores 0%
  EXACT**, and read this as a power problem requiring more data. Before acquiring data (D-016), test the
  alternative explanation: that the criterion was specified at the wrong unit of analysis.
- **Method:** recompute the EXACT (CI ⊂ [0.88, 0.92]) and SAFE (lower bound ≥ 0.88) criteria with the
  **facility** as the unit rather than the row — i.e. a t-interval on mean PICP across facilities, which
  is what audit issue **I04 requires for clustered inference in any case**. Source tables:
  `2026-09-02-core-{belgrade,birmingham}-gcal-per-facility.csv` (no rerun needed).

| city / horizon | method | n_fac | mean PICP | sd | SE | 95% CI (facility-clustered) | EXACT | SAFE |
|---|---|---|---|---|---|---|---|---|
| Belgrade t+15 | split-CP | 22 | 0.8992 | 0.0408 | 0.0087 | [0.8811, 0.9173] | YES | YES |
| Belgrade t+15 | CQR | 22 | 0.8993 | 0.0282 | 0.0060 | [0.8868, 0.9118] | YES | YES |
| Belgrade t+15 | ACI | 22 | 0.8929 | 0.0109 | 0.0023 | [0.8881, 0.8978] | YES | YES |
| Belgrade t+15 | ACQR | 22 | 0.8931 | 0.0066 | 0.0014 | [0.8902, 0.8961] | YES | YES |
| Birmingham t+60 | split-CP | 28 | 0.9066 | 0.0513 | 0.0097 | [0.8867, 0.9265] | no | YES |
| Birmingham t+60 | CQR | 28 | 0.9021 | 0.0417 | 0.0079 | [0.8859, 0.9183] | YES | YES |
| Birmingham t+60 | ACI | 28 | 0.8890 | 0.0155 | 0.0029 | [0.8830, 0.8950] | YES | YES |
| Birmingham t+60 | ACQR | 28 | 0.8928 | 0.0234 | 0.0044 | [0.8837, 0.9019] | YES | YES |

- **Answer: an estimand problem, not a data problem.** Per-facility CI half-widths have median 0.033
  (range 0.016–0.093) at n ≈ 1,015, so the ±0.02 band is unreachable at that level and would remain so
  under any realistic increase in data. At the facility-clustered level **7 of 8 configurations are EXACT
  and all 8 are SAFE**. This is the finding that removed the case for acquiring more data (D-016).
- **But the two levels answer DIFFERENT questions, and the paper must say so.** Population-level
  equivalence asks whether *mean* coverage sits at nominal; the per-facility criterion asks whether
  *every* facility does. They are not interchangeable.
- **The demonstration that makes this publishable:** at Belgrade, **split-CP passes both EXACT and SAFE at
  the population level while holding a facility × bucket cell at 0.516 coverage** (EXP-021). Population
  equivalence testing is exactly the instrument that conceals the failure this paper exists to expose.
  The paper can now make that argument with its own numbers instead of asserting it.
- **Consequence for R-Phase 4 (D-016 decision 3):** adopt a two-level estimand — population-level TOST +
  SAFE, facility-clustered with Holm; facility-level reported as dispersion, worst cell, and fraction
  below threshold, with equivalence explicitly NOT claimed there and the reason stated. This also
  dissolves the EXP-019 SAFE-vs-dispersion tension by assigning the two questions to two levels instead of
  forcing one criterion to carry both.
- **Caveat:** the t-interval assumes facilities are exchangeable and independent. R-Phase 4 should confirm
  with a facility-level bootstrap or a hierarchical model; the conclusion is unlikely to move given how
  far inside the band the adaptive methods sit, but the check is cheap and belongs in the final inference.
- **Read:** no new data is needed for this submission. The remaining genuine data limitation is Belgrade's
  4-day test window for *day-of-week* analysis, which is closed by running that check on Birmingham
  instead (15 test dates, all 7 weekdays, ~2.1 replicates each).

### EXP-024 — 2026-09-03 — R-Phase 3b task 3: trust/abstain with true ACQR widths (Belgrade, t+15, 90%)
- **Purpose:** close **C03** (Table 5's caption claims ACQR widths; the code used plain ACI, and the figure
  axis said "ACI width" — X06), **C04** (thresholds were not prequential: the calibration replay
  initialised the score pool from the FULL calibration residual vector), and **D04** (committed-set
  coverage was 0.824–0.894, below nominal at every commit rate, while the prose said only "near 0.88").
- **Script:** `03_code/src/conformal/2026-09-03-trust-abstain.py` (resumable, SKIPPED markers,
  `--n-random`). **Outputs:** `2026-09-03-trust-abstain-{per-facility,summary}.csv`.
- **Protocol:** true ACQR widths (adaptive recursion on CQR scores over a CQR band); thresholds read off
  the **cal-B** segment of the same nested split `core.select_gamma_on_calibration` uses (cal-A seeds the
  pool, cal-B replayed prequentially, n_cal_b = 380) and applied unchanged to test. Step size and
  thresholds now share one honest protocol, as C04 requires.

**Archived (ACI widths, non-prequential) → corrected (ACQR, cal-B thresholds):**

| target | commit rate | MAE (cars) | committed coverage |
|---|---|---|---|
| 0.1 | 0.179 → 0.196 | 1.386 → 0.990 | 0.824 → **0.9045** |
| 0.3 | 0.377 → 0.442 | 1.629 → 1.553 | 0.861 → **0.9057** |
| 0.5 | 0.553 → 0.615 | 2.063 → 1.985 | 0.870 → **0.8976** |
| 0.7 | 0.697 → 0.742 | 2.354 → 2.381 | 0.875 → **0.8923** |
| 0.9 | 0.884 → 0.896 | 2.872 → 2.923 | 0.888 → **0.8902** |
| commit-all | — | 3.405 | 0.8931 |

- **D04 DOES NOT SURVIVE THE METHOD FIX — this is a reversal, and it is in our favour.** The audit was
  right about the *published* numbers: with ACI widths and in-sample thresholds, committed coverage was
  0.824–0.894, below nominal everywhere. With the method the caption actually claims, committed coverage
  is **0.8902–0.9076** — at or above 0.90 at 4 of 10 commit rates and never more than **0.0029** below the
  marginal ACQR rate of 0.8931. The "selective-coverage failure" was an artifact of taking widths from the
  wrong method: ACI widths are near-homoscedastic (one global quantile modulated by the adaptive level),
  so a narrow ACI interval does not mark an easy row, whereas ACQR widths inherit the CQR band's
  heteroscedasticity and do. *(Recorded honestly: the session began by expecting to confirm D04 and write
  up an honest negative result; the data said otherwise.)*
- **The comparators are what make this claimable rather than lucky.** Matched **random selection** at the
  same achieved rate preserves marginal coverage by construction (0.8923–0.8948) and delivers no accuracy
  benefit; width-ACQR sits **+0.0046** above random on coverage while cutting MAE **38.4%** below it at the
  same commit rate. Selection is doing real work, and it is not paying for it in coverage. Without the
  random arm, "MAE falls when you commit less" would have been indistinguishable from a smaller-sample
  artifact — which is exactly why D04 demanded comparators.
- **The manuscript's headline sentence survives, slightly improved:** committing the most-confident 74%
  cuts MAE from 3.40 to 2.38 vehicles (**30%**) at committed coverage 0.892. (Archived: 3.24 → 2.35, ~27%.)
- **DO NOT OVERCLAIM.** Marginal validity does **not** transfer to a selected subset in general — that is
  the point of the selective-conformal / risk-control literature, which must still be cited. What we have
  is an *empirical* finding on one city and one horizon: with ACQR widths, selective coverage happens to
  track the marginal rate here. State it as measured, not as a guarantee, and keep the comparator table so
  the reader can see the basis.
- **MANUSCRIPT CLAIM FALSIFIED — "abstentions concentrate in the volatile rush periods."** Measured lift
  (abstention share ÷ bucket base rate) at a 70% commit target: night **0.25**, am_rush **0.79**,
  midday **1.69**, pm_rush **1.74**, evening **0.62**. The morning rush is *under*-represented among
  abstentions, and midday — which the sentence never mentions — is concentrated almost as strongly as the
  evening peak. **Correct wording: abstentions concentrate in midday and the evening peak, and are rare
  overnight.**
- **Independent internal corroboration:** those are precisely the two buckets where EXP-021 found the worst
  facility-bucket coverage (split-CP 0.516 midday, 0.556 pm_rush at facility 9). Two experiments built on
  different machinery agree on which periods are hard, and the abstention rule rediscovers them without
  being told. That is worth a sentence in the paper.
- **Next:** R-Phase 3b task 4 — E3 baselines (C07 calendar-day EnbPI chunking, M02 conformalized NGBoost).

### CORRECTION — 2026-09-03 — the split-integrity suite emits 36 checks, not 43
EXP-016 and several later entries record the split-integrity gate as "43/43". That figure came from a
**hardcoded string** in `03_code/tests/2026-09-02-verify-state.sh` line 39 (`echo "OK ... 43/43"`), which
printed regardless of the actual result; it was never a measured count. The suite
`2026-09-02-test_split_integrity.py` is **unmodified** (mtime 2026-09-02 18:53, and it post-dates the
R-Phase 0 freeze so it is legitimately absent from the manifest) and passes with **36 checks and 0
failures** — 12 `check()` call sites, several inside loops over horizons and cities. The gate has always
genuinely passed; only the total was wrong. Historical entries above are left as written so the record
stays honest; `2026-09-03-verify-state.sh` now derives the count instead of asserting it. No result,
table or conclusion depends on this number. See LESSONS_LOG A9.

### EXP-025 — 2026-09-03 — R-Phase 3b task 4: E3 baselines rerun (C07 chunking, M02 conformalized NGBoost)
- **Purpose:** close **C07** (EnbPI chunked the test stream by a FIXED ROW COUNT and fed the whole chunk to
  `update()`, so the last h-1 rows of every chunk were released with outcomes not yet observable) and
  **M02** (one untuned Gaussian NGBoost was generalised into a claim about parametric predictive
  distributions as a family).
- **Script:** `03_code/src/conformal/2026-09-03-e3-baselines.py` (the 2026-08-04 original untouched).
  Resumable, `SKIPPED-*` markers, incremental flush after every facility, `status` column, `degenerate`
  and `dynamic` flags, all facilities evaluated (D05).
- **Outputs:** `05_results/tables/2026-09-03-e3-{belgrade,birmingham}-per-facility.csv`,
  `2026-09-03-e3-summary.csv`.
- **New core machinery (B9):** `core.calendar_day_chunks`, `core.fixed_row_chunks`,
  `core.matured_release_end` — the maturity rule now has ONE definition shared by the streaming and
  batch paths. **Property gate extended 27/27 -> 39/39** with P18-P21.

**DESIGN — why MAPIE was kept, and how the delta is attributed.** C07 is a defect in the update
*schedule*, not in the estimator, so `update()` is called correctly rather than EnbPI being rewritten.
Replacing the reference implementation would have forfeited the defence against a misimplemented-baseline
objection (the reasoning that kept SPCI cited-not-run, D-011) and, decisively, would have made the delta
unattributable — an independent reimplementation could never reproduce the archived 0.8874. Two arms:

| arm | data | chunking | purpose |
|---|---|---|---|
| `A12_v1_paired` | v1 | BOTH schemes on **one shared fit per facility** | isolates C07 with zero fit-to-fit variation |
| `A3_v2_daychunk` | v2 + `use_{H}` | calendar-day, matured only | the numbers for the paper |

**REPRODUCTION of the archived protocol** (`EnbPI-oldchunk` vs `2026-08-04-e3-*`):
Birmingham **exact on all 28 facilities** (max |dPICP| = 0, max |dMPIW| = 5.7e-14 = RF thread noise).
Belgrade exact to 4 dp on **17 of 22**; the other 5 differ by exactly 1-2 coverage indicators out of 1,018
rows (<= 0.002 PICP), all in the same direction, with widths essentially unchanged. **Measured, not
assumed:** two independent fits in the CURRENT environment are identical (bounds to 2.3e-13, PICP to the
row), so this is a genuine between-version difference from `requirements.txt` pinning nothing
(`mapie>=0.8`), not run-to-run noise. See LESSONS_LOG A13. The C07 delta is unaffected because it is
paired inside one fitted model.

**C07 DELTA (paired within facility, one shared fit):**

| city | n | PICP old -> new | MPIW | Winkler | Wilcoxon |
|---|---|---|---|---|---|
| Belgrade t+15 | 22 | 0.8877 -> **0.8918** (+0.0042) | 16.013 -> 16.178 (+0.165) | 28.420 -> 28.310 (-0.110) | dPICP p=0.00029; dWinkler p=0.12 |
| Birmingham t+60 | 28 | 0.8448 -> **0.8471** (+0.0022) | 104.98 -> 105.26 (+0.280) | 182.18 -> 180.54 (-1.641) | dPICP p=0.082; dWinkler p=0.0011 |

- **THE AUDIT'S DIRECTIONAL PREDICTION IS WRONG, AND WE MUST NOT REPEAT IT.** The plan states that the bug
  "gives EnbPI **more** information than the protocol allows" and therefore "fixing it can only strengthen
  our conclusion". Measured, the fix makes EnbPI *slightly better on every axis*: coverage rises toward
  nominal, across-facility dispersion falls (0.0678 -> 0.0632 Belgrade, 0.0782 -> 0.0763 Birmingham) and
  Winkler improves. Releasing outcomes early did not corrupt the residual pool, it merely fed it *sooner*,
  which made intervals marginally narrower and coverage marginally lower. So the correction mildly
  **weakens** our comparative claim instead of strengthening it. The effect is small and the conclusion
  survives intact — EnbPI still under-covers in both cities (9/22 and 22/28 facilities below 0.90) with
  4-5x the dispersion of the adaptive family — but the sentence must not appear in the response letter.
  *(Recorded per lesson C4: the script was written before the direction was known.)*

**HEADLINE — corrected E3 table (arm A3, v2 features, dynamic non-degenerate facilities, 90%):**

| city | method | n | PICP | sd | MPIW | Winkler | archived PICP/sd |
|---|---|---|---|---|---|---|---|
| Belgrade t+15 | EnbPI | 22 | 0.8916 | 0.0607 | 16.166 | 28.202 | 0.8874 / 0.0680 |
| | AgACI-style | 22 | 0.9129 | 0.0103 | 15.207 | 22.008 | 0.9330 / 0.0090 |
| | NGBoost | 22 | 0.7602 | 0.0825 | 8.783 | 25.707 | 0.7600 / 0.0867 |
| | **NGBoost-conformal** | 22 | **0.8909** | **0.0367** | 12.516 | **22.826** | (new, M02) |
| | *ACI cross-check* | 22 | *0.8929* | *0.0109* | *15.968* | *24.233* | — |
| Birmingham t+60 | EnbPI | 28 | 0.8413 | 0.0802 | 104.005 | 178.553 | 0.8448 / 0.0782 |
| | AgACI-style | 28 | 0.8977 | 0.0144 | 130.859 | 171.026 | 0.9066 / 0.0199 |
| | NGBoost | 28 | 0.3727 | 0.1443 | 28.900 | 408.082 | 0.3837 / 0.1575 |
| | **NGBoost-conformal** | 28 | **0.9011** | **0.0491** | 134.227 | **175.270** | (new, M02) |
| | *ACI cross-check* | 28 | *0.8890* | *0.0155* | *131.554* | *175.309* | — |

- **M02 IS NOW A MEASUREMENT, NOT ADVOCACY — and it is the strongest baseline result in the paper.** The
  SAME fitted NGBoost, conformalized with the CQR score on the calibration split, recovers coverage in
  both cities: Belgrade **0.7602 -> 0.8909** (+0.131), Birmingham **0.3727 -> 0.9011** (+0.528). Dispersion
  falls 2.2x and 2.9x (0.0825 -> 0.0367; 0.1443 -> 0.0491), facilities below 0.90 fall 22/22 -> 12/22 and
  28/28 -> 12/28, and — the part that makes it unarguable — **Winkler, a strictly proper score, IMPROVES**
  by 11.2% and 57.1%. The parametric model is not a weak forecaster; its *uncertainty quantification* is
  what fails, and conformalizing the identical model repairs it. The manuscript sentence becomes: this
  implementation's failure is a calibration failure, demonstrated by repairing it without changing the
  model. The family-wide claim is dropped as M02 requires.
- **Bonus finding on the degenerate facility.** NGBoost cannot be **fitted at all** on Belgrade facility 1
  (constant training target -> zero scale -> NaN gradients, `ValueError: Input y contains NaN`), while every
  conformal method returns a valid interval there. Recorded as an explicit `FAILED` row rather than a
  silently absent one, which would have corrupted the D05 all-facility sensitivity (lesson A2/B5).
- **B8 cross-check passes on BOTH cities.** This script's independent ACI arm reproduces the canonical
  runner exactly: Belgrade 0.8929 / sd 0.0109 and Birmingham 0.8890 / sd 0.0155, matching EXP-023's
  facility-clustered table to four decimals. Two independently written scripts on the shared core agree.
- **The paper's spine holds against the corrected baselines.** Across-facility dispersion: EnbPI 0.0607 /
  0.0802 against ACI 0.0109 / 0.0155 — 5.6x and 5.2x. The per-facility reliability gap is not an artifact
  of a mis-run baseline.
- **AgACI-style also moved** (Belgrade 0.9330 -> 0.9129, Birmingham 0.9066 -> 0.8977) because its experts now
  run on `core.adaptive_conformal_stream` instead of the retired buggy `np.quantile` path (C01/C02/C06).
  Its archived gamma grid was deliberately NOT changed to `core.GAMMA_GRID`: aggregating over a grid is
  what the baseline *is*, so changing it would confound the baseline with the fix. "Over-covers as
  configured" survives on Belgrade; on Birmingham it is now essentially at nominal.

**VERIFICATION.**
1. **Property gate 27 -> 39** (P18-P21): calendar-day chunks partition the stream exactly and hold one date
   each; the release rule never hands over an immature outcome at h = 1, 2, 3, 6; held-back rows carry
   forward and are released exactly once; and at h = 1 the rule reduces to releasing the whole chunk.
   **P19 carries a negative control** — the archived fixed-row scheme is asserted to VIOLATE the same
   property (10 premature releases at h=3), so the gate is demonstrably able to detect C07 rather than
   vacuously passing.
2. **Black-box no-lookahead witness** on the script's exact call path, applied uniformly to every method
   (`--witness`), which an internal property test could not do because MAPIE is third-party. Two things
   the first version of this witness got wrong and that are now fixed: the tolerance is **measured** from
   a replicate on identical input (5.684e-14 — MAPIE aggregates 30 bootstrap models under `n_jobs=-1`;
   comparing at bit equality reported that noise as a lookahead), and the probe is **adversarial** — C07
   leaks only the last h-1 rows of a chunk, so a mid-chunk probe gives a FALSE PASS, which is exactly what
   the first run produced. With both fixed, on Belgrade facility 2: the archived scheme **fails** (y[575]
   moves a bound at 576 but matures at 578 — this is C07, measured rather than read off the code) while
   the fix diverges only at 788, the next day boundary after maturity; AgACI diverges at exactly t+h
   (502, 510), so the release semantics are exact, not merely conservative.
3. Relocating the chunking into `core.py` was verified to change nothing: core's chunk lists and release
   ends are identical to those the run actually used, on every facility of both cities and both arms.
4. Frozen manifest re-checked after the run: **130 files, zero drift**. Gate: 36 / 39 / 130.
- **LIMITATION — the witness is not equally sensitive everywhere.** On Birmingham the archived arm showed
  *no* divergence at its adversarial probe: with only 116 test rows against a large training residual
  pool, one perturbed residual does not move the selected order statistic. Absence of divergence there is
  insufficient sensitivity, NOT evidence of causality. The structural violation is still proven by P19's
  negative control. The two tests are complementary and both are needed.
- **Environment (must go in the R-Phase 6 lock file):** mapie 1.5.0, ngboost 0.5.11, scikit-learn 1.7.2,
  pyarrow 25.0.1, numpy 2.2.6, pandas 2.3.3, scipy 1.15.3. mapie/ngboost were installed off-volume this
  session (LESSONS_LOG A10/A11).
- **Manuscript consequences:** every Table 2 baseline row changes; the M02 sentence is rewritten as a
  measured result; the "fixing C07 can only strengthen our conclusion" argument is dead and must not be
  used in the response letter.
- **Next:** R-Phase 3b task 5 — rolling-origin (I04, I05), which also re-runs the EXP-022 orthogonal check
  on the folds and on Birmingham to close the day-of-week confound.

### EXP-026 — 2026-09-03 — R-Phase 3b task 5: rolling-origin rerun (I04, I05) + **X08, a new data defect**
- **Scripts:** `03_code/src/conformal/2026-09-03-rolling-origin.py` (run),
  `2026-09-03-rolling-origin-inference.py` (all inference), `2026-09-03-stuck-sensor-diagnostic.py` (X08).
- **Outputs:** `2026-09-03-rolling-origin-belgrade.csv` (432 rows, 72 fold-facility units),
  `-foldsummary.csv`, `-inference.csv`, `2026-09-03-stuck-sensor-{diagnostic,impact}.csv`.
- **Analysis plan fixed IN ADVANCE:** `04_experiments/2026-09-03-rolling-origin-PRESPECIFICATION.md`
  (written before the run; contrast family, unit of analysis and decision rules all pre-committed).
- **Environment:** the EXP-025 lock, verified by version: scikit-learn 1.7.2, scipy 1.15.3, numpy 2.2.6,
  pandas 2.3.3, mapie 1.5.0, pyarrow 25.0.1. See LESSONS_LOG A14/A15 for how it was restored.

**I05 — per-fold facility selection. Measured effect: one fold-facility.**
Recomputing the dynamic set inside each fold's own training window instead of the main train window
changes the inclusion of exactly **one** fold-facility out of 72 (F3/facility 10, train std 7.85 in F3's
own window, 4.6 on the main window). The set of facilities dynamic in all three folds is n = 22 and is
IDENTICAL to the archived set. The audit's downgrade of I05 to MINOR is confirmed by measurement. The
all-facility sensitivity arm (n = 23 after dropping the degenerate facility 1) is in the same CSV and
changes no conclusion; it makes split-CP look slightly WORSE, not better.

**I04 — facility-clustered inference. The result survives, and the anti-conservatism is now measured.**
Unit = facility; per-facility statistic = mean over folds of |PICP - 0.90|; four prespecified contrasts;
Holm-corrected; confirmed by a facility-clustered bootstrap (B = 10,000, resampling facilities).

| contrast | mean diff | boot 95% CI | Wilcoxon p (n=22) | Holm p | pooled p (n=66, archived style) | anti-conservatism |
|---|---|---|---|---|---|---|
| ACI vs split-CP | -0.0326 | [-0.0595, -0.0160] | 1.0e-6 | 6.0e-6 | 3.4e-7 | 4.2x |
| ACI vs CQR | -0.0201 | [-0.0285, -0.0126] | 1.7e-6 | 6.8e-6 | 2.6e-7 | 9.1x |
| ACQR vs CQR | -0.0216 | [-0.0297, -0.0143] | 1.7e-6 | 6.8e-6 | 2.9e-9 | 810x |
| ACQR vs split-CP | -0.0342 | [-0.0599, -0.0177] | 1.7e-6 | 6.8e-6 | 2.8e-9 | 850x |

All four survive Holm; every bootstrap CI excludes zero; 91-96% of facilities favour the adaptive method.
**The honest p is ~1e-6, not the archived p < 1e-10** — and the pooled test is anti-conservative by a
factor of 4x to 850x on the SAME data, so the size of the defect is measured rather than asserted.
*(Prespecified note: the two-sided Wilcoxon floor at n = 22 is ~4.8e-7. Our p-values sit above it, so
they are real values and not a truncation artifact.)*

**Gamma protocol, decomposed paired inside one fit.** Calibration-selected gamma vs the archived fixed
0.05, on the same fitted models: coverage moves toward target (ACI F2 0.8875 -> 0.8903, F3 0.8856 ->
0.8876) while across-facility dispersion rises slightly (F3 ACI sd 0.0064 -> 0.0113). A small, honest
coverage-versus-dispersion trade in the selection protocol itself; worth one sentence, not a claim.

---

## X08 — NEW DATA DEFECT, found while verifying this run. Not in the audit; not caught by R-Phase 1.

**How it surfaced.** The archived EXP-013 headline "split-CP collapses in fold F2 (std 0.161, Winkler
34.9)" was predicted NOT to survive the C01 fix and v2 features. It reproduced almost exactly
(sd 0.157, Winkler 33.6) — so the prediction was wrong and the *next* question was why.

**What it is.** `Garaza "Vukov spomenik"` (facility_id 8) behaves normally 4-14 March (12-64 distinct
readings per day), then reports **exactly 0.0 for 15-18 March** and **exactly 109.0** — evidently its
capacity — **all day on 20 March**. Across its entire 1,015-row MAIN test window it takes **two distinct
values**: 0.0 (44.5%) and 109.0 (55.5%). Sensor failure followed by a stuck-at-full reading.
**The pattern is present in `01_data/raw/belgrade_RAW.csv`**, so it is a property of the source export,
not something the v1 or v2 pipeline introduced. It is the same defect class as S02/X01 and the same one
D-016 cites for rejecting the Luxembourg file.

**Why R-Phase 1 missed it.** The integrity suite checks split boundaries, embargoes, target alignment and
interpolation. None of those ask whether a retained series carries any information. Facility 8 passes
every one of them, and its TRAIN window is healthy (std 18.1), so the dynamic-facility filter admits it.

**A candidate rule, stated on the inputs only and blind to any method's performance:** exclude a
facility-window with fewer than 10 distinct occupancy readings. The threshold is not delicate —
facility 1 has 1 distinct value, facility 8 has 2, and **the next lowest facility has 64** — so any
threshold in [3, 60] selects the same two facilities. Facility 1 is already excluded as degenerate (B5),
so the rule adds exactly one facility to the exclusion list and formalises the one already handled.

**Blast radius — recomputed from the logged per-facility CSVs, nothing re-fitted:**

| what | with fac 8 | without | read |
|---|---|---|---|
| **EXP-013 / this rerun: split-CP F2 sd** | 0.1574 | **0.0537** | the "F2 collapse" **IS** facility 8 — **DEAD** |
| split-CP F2 worst facility PICP | 0.1611 | 0.7533 | ditto |
| **EXP-025 EnbPI: worst facility** | 0.6640 | **0.8010** | our baseline-failure claim was inflated |
| EXP-025 EnbPI across-facility sd | 0.0609 | 0.0326 | -46.5% |
| EXP-025 NGBoost worst facility | 0.4867 | 0.6621 | M02's starting point was inflated |
| EXP-025 ACI-crosscheck sd | 0.0239 | 0.0076 | **-68.2%** |
| **EnbPI / ACI dispersion RATIO (within EXP-025)** | **2.55x** | **4.29x** | the ratio claim gets **STRONGER** |
| Core methods, t+15 (EXP-017/019) | sd 0.030-0.071 | 0.025-0.068 | conclusions unchanged |
| EXP-021 worst cell 0.516 | **facility 9** | unaffected | **Table 4 is NOT contaminated** |

> **CORRECTION — 2026-09-04 (EXP-027). The base of the table above is the ALL-24 facility set, not the
> published one.** The rule catches degenerate facility 1 as well as facility 8, so the "without" column
> drops both, and facility 1 (PICP vacuously 1.0, B5) appears in no published number. On the published
> `dynamic & !degenerate` base of 22 -> 21, measured in EXP-027: **the EnbPI/ACI ratio WEAKENS, 5.57x ->
> 4.42x**, not 2.55x -> 4.29x. The EnbPI and NGBoost worst-facility rows and the EXP-021 row are correct
> as written and were confirmed exactly. The split-CP F2 rows are unaffected by this (rolling-origin
> summaries are computed on their own fold populations). Rows in this table are left as originally
> written so the record stays honest; quote EXP-027 instead. See LESSONS_LOG B17.

**Read — and it cuts both ways, which is why it must be reported carefully.** The absolute worst-case
statements about EnbPI and NGBoost are inflated by a dead sensor and must be restated. But the *ratio*
claim — the one the thesis actually rests on — gets **stronger**, because facility 8 inflates ACI's
dispersion proportionally more (-68%) than EnbPI's (-46%). This is the third time in this revision that
a correction has moved a number in a direction nobody predicted (cf. B12, and this session's own failed
prediction about F2).

**The thesis is NOT threatened.** The per-facility reliability gap rests on 22 facilities, the core-method
dispersion is essentially unchanged, and EXP-021's worst cell (0.516) is facility 9, a genuine method
failure on a healthy series.

**Status: DECISION REQUIRED — not taken unilaterally.** Adopting the rule alters already-logged numbers
in EXP-017, EXP-019, EXP-020, EXP-021, EXP-022, EXP-024 and EXP-025 and changes Table 2 of the
manuscript. Per the standing rule, a change that would alter a logged number is reported rather than
silently regenerated. Nothing has been regenerated.

**RESOLVED SAME DAY — the author ADOPTED the exclusion (D-018).** The rule is now a single tested
definition in `core.py`: `core.MIN_DISTINCT_READINGS`, `core.is_low_information`,
`core.low_information_facilities`, under property checks **P22-P24** (gate 39 -> 48). P23 is a negative
control proving the filter can decline to fire; **P24 asserts on the real Belgrade test split that the
selection is identical for every threshold in [3, 60]**, which is what makes this a data-quality rule
rather than a tuned one. Applying it through `core.py` is deliberate: seven experiments must apply ONE
definition, not seven (B9, and the same reasoning as `matured_release_end`).

- **Next:** the X08 batch rerun — EXP-017, 019, 020, 021, 022, 024, 025 in ONE batch with a single
  re-freeze and a published before/after table of every changed number. **A half-applied exclusion is
  the one genuinely dangerous state** (some numbers computed with facility 8, some without, none
  comparable), which is why revision 38 stopped rather than starting it. Then the deferred EXP-022
  orthogonal re-run on the folds and on Birmingham; then task 6, the allocation vignette.

### EXP-027 — 2026-09-04 — the X08 batch: D-018 exclusion applied to all seven experiments as ONE unit
- **Authority:** D-018 decision 1. The decision was not reopened. **Prespecified in writing before any
  number was regenerated:** `04_experiments/2026-09-04-x08-batch-PRESPECIFICATION.md`.
- **Scripts:** `03_code/src/conformal/2026-09-04-x08-reaggregate.py` (the batch),
  `2026-09-04-x08-before-after.py` (the deliverable table), `2026-09-04-x08-orthogonal-excess.py`
  (EXP-022's derived dose-response), `03_code/tests/2026-09-04-x08-control-check.py` (the gate).
- **Outputs:** `05_results/tables/2026-09-04-x08-{core-headline,e3-summary,base-learner,tod-summary,
  orthogonal-summary,trust-abstain}-{control,excl}.csv`, `2026-09-04-x08-before-after.csv`
  (688 statistics, **505 changed**), `2026-09-04-x08-orthogonal-excess.csv`.
  **Nothing logged was overwritten**; gate re-verified after the batch at **36 / 48 / 130, zero drift**.

**METHOD — re-aggregation, and why it is exact rather than a shortcut.** Every script in scope fits each
facility independently, and reading each one's own `write_summary` established that **no summary statistic
in any of the seven pools rows across facilities** — Cramer's V in EXP-022 is computed per facility and
then averaged; EXP-024's summary is an unweighted facility mean. Excluding a facility therefore changes
only which rows enter the aggregate, so re-aggregating the logged per-facility CSVs is exactly equivalent
to refitting with the exclusion applied, and strictly better: it carries no RF thread drift (A8) and no
MAPIE between-fit variation (A13), so the exclusion is the *only* difference between the two arms. Four of
the six summaries are produced by importing the original script and calling **its own** `write_summary`
with the output path redirected, so no second aggregation was written (B9).

**THE GATE — a negative control on the whole batch (B11).** Run with the filter OFF, the re-aggregator
reproduced **every logged summary number to 4 dp: 688 checks, 0 failures**, across all six experiments.
Only then was the filtered arm read. Two summaries (core headline, E3) have **no writer anywhere in the
tree** — they were produced ad hoc in an earlier stage, a provenance gap worth closing in R-Phase 6 —
so for those the control is the only thing establishing that the aggregation matches.

**Exclusion set, computed from the data and never hardcoded:** Belgrade **{1, 8}** at every horizon;
**Birmingham {} — empty at every horizon**, so *no Birmingham number in the project changes at all*.
Threshold gap republished on the scored window: facility 1 -> 1 distinct reading, facility 8 -> 2, next
lowest (facility 10) -> **64**. The published base goes **22 -> 21** facilities.

---

## THE BASE ERROR IN THE REVISION-38 IMPACT TABLE — found before the batch was run

`2026-09-03-stuck-sensor-impact.csv` computes its EXP-025 rows on the **all-24** base. Its "after" column
therefore drops **facilities 1 and 8 together**, because the rule catches the degenerate facility 1 as
well — and facility 1 appears in **no published number** (B5: its PICP is vacuously 1.0). Every logged
EXP-025 figure uses the `dynamic & !degenerate` base of 22.

| quantity | impact-table base (24 -> 22) | **published base (22 -> 21)** |
|---|---|---|
| ACI-crosscheck across-facility sd | 0.0239 -> 0.0076 (-68%) | **0.0109 -> 0.0077 (-29%)** |
| EnbPI across-facility sd | 0.0609 -> 0.0326 (-46%) | **0.0607 -> 0.0340 (-44%)** |
| **EnbPI / ACI dispersion ratio** | 2.55x -> 4.29x (*stronger*) | **5.57x -> 4.42x (WEAKER)** |

The -68% collapse in ACI's dispersion is mostly the removal of facility 1, not of facility 8. **That is
what manufactured the apparent strengthening.** D-018's rationale (iv) is corrected accordingly; the
decision is unaffected. Recorded as LESSONS_LOG **B17**.

## HEADLINE RESULTS — before -> after, on the published base

**EXP-017/019 core methods, Belgrade t+15 @90% (n 22 -> 21). Birmingham: unchanged, all methods.**

| method | PICP | across-facility sd | Winkler | SAFE |
|---|---|---|---|---|
| split-CP | 0.8992 -> 0.9008 | 0.0408 -> 0.0411 | 26.83 -> **23.93** | 0.409 -> 0.429 |
| CQR | 0.8993 -> 0.8995 | 0.0282 -> 0.0289 | 20.10 -> 19.63 | 0.364 -> 0.381 |
| ACI | 0.8929 -> 0.8913 | 0.0109 -> **0.0077** | 24.23 -> 22.45 | 0.045 -> **0.000** |
| ACQR | 0.8931 -> 0.8940 | 0.0066 -> **0.0053** | 19.79 -> 19.34 | 0.000 -> 0.000 |

- **THE PAPER'S SPINE STRENGTHENS.** split-CP / ACQR across-facility dispersion **6.20x -> 7.76x**;
  split-CP / ACI **3.75x -> 5.32x**; CQR / ACQR **4.28x -> 5.45x**. Belgrade means move by <= 0.0016, as
  prespecified. Birmingham is untouched (2.19x / 3.32x / 1.78x), because the rule excludes nothing there.
- **Small honest loss:** ACI's SAFE score on Belgrade falls **0.045 -> 0.000** — facility 8 was the single
  facility whose CI lower bound cleared 0.88. The EXP-019 marginal-vs-safety tension therefore gets
  slightly worse, not better, and must be reported that way.

**EXP-025 E3 baselines, Belgrade (n 22 -> 21). Birmingham: unchanged on every row.**

| method | mean PICP | sd | worst facility |
|---|---|---|---|
| EnbPI | 0.8916 -> 0.9024 | 0.0607 -> 0.0340 | 0.6640 -> **0.8010** |
| NGBoost | 0.7602 -> 0.7733 | 0.0825 -> 0.0568 | 0.4867 -> **0.6621** |
| NGBoost-conformal | 0.8909 -> 0.8921 | 0.0367 -> 0.0371 | 0.8079 -> 0.8079 |
| AgACI-style | 0.9129 -> 0.9113 | 0.0103 -> 0.0069 | 0.8985 -> 0.8985 |
| ACI-crosscheck | 0.8929 -> 0.8913 | 0.0109 -> 0.0077 | 0.8690 -> 0.8690 |

- Both prespecified worst-facility restatements land **exactly** on the predicted values.
- **EnbPI / ACI dispersion ratio 5.57x -> 4.42x (Belgrade), 5.17x -> 5.17x (Birmingham).** The Belgrade
  figure weakens; the claim "EnbPI carries 4-5x the across-facility dispersion of the adaptive family"
  survives in both cities and is now the honest phrasing.
- **M02 weakens on Belgrade and is untouched on Birmingham.** Conformalizing the same fitted NGBoost:
  coverage 0.7733 -> 0.8921 (+0.119, was +0.131); dispersion **1.53x lower, was 2.25x**; Winkler
  **9.9% better, was 11.2%**. Birmingham stands at +0.528, 2.94x and 57.1%. The claim is unarguable in
  both cities; only the Belgrade magnitudes move, and the paper should lead with Birmingham.

**EXP-021 Table 4 — the strongest result in the paper is UNTOUCHED where it matters (110 -> 105 cells).**

| method | worst cell | worst facility | cells < 0.80 | facility x bucket sd |
|---|---|---|---|---|
| split-CP | **0.5160** (unchanged) | 9 (unchanged) | 14 -> 12 | 0.0993 -> 0.0968 |
| Mondrian-split-CP | 0.6200 (unchanged) | 9 | 15 -> 15 | 0.0772 -> 0.0760 |
| ACI | 0.6720 (unchanged) | 15 | 12 -> 12 | 0.0753 -> 0.0756 |
| **ToD-ACI** | **0.8421** (unchanged) | 9 | **0 -> 0** | 0.0280 -> **0.0214** |

Every headline number in Table 4 survives the exclusion identically, exactly as EXP-026 predicted: the
worst cell is facility **9**, on a healthy series. Two of split-CP's fourteen sub-0.80 cells were
facility 8's, and ToD-ACI's spread tightens further. **This table needs no restatement.**

**EXP-022 orthogonal partitions — the dose-response survives and stays monotone in Cramer's V.**

| axis | V | split-CP excess sd | ToD-ACI excess sd | structure removed |
|---|---|---|---|---|
| time_of_day | 1.000 | 0.0889 -> 0.0863 | 0.0087 -> **0.0000** | 99% -> **at the noise floor** |
| occupancy_tercile | 0.558 -> 0.569 | 0.0961 -> 0.0943 | 0.0423 -> 0.0438 | 81% -> 78% |
| day_of_week | 0.153 | 0.0522 -> 0.0460 | 0.0386 -> 0.0386 | 45% -> 30% |

- **Report the time-of-day cell as "indistinguishable from the matched noise floor", NOT as "100%".**
  ToD-ACI's on-axis sd (0.0214) now sits *below* its own random-label floor (0.0218), so the
  `max(., 0)` clip returns exactly zero. That is a statement about resolution, not a perfect result.
- **The honest finding against us survives and strengthens:** global ACI still beats ToD-ACI off-axis on
  day-of-week (excess 0.0283 vs 0.0386; 62% vs 30% of structure removed). The practitioner rule stands.
- Day-of-week remains the confounded leg (4 dates, each weekday once) and is still indicative only;
  task 5b re-runs it on the rolling-origin folds and on Birmingham.

**EXP-024 trust/abstain — improves slightly on every axis (n 22 -> 21).**
Committed coverage **0.8907-0.9070** (was 0.8902-0.9076), at or above 0.90 at **4 of 10** commit rates,
unchanged. The headline becomes: committing the most-confident **73%** cuts MAE from **3.13 to 2.10
vehicles (33%)**, was 74% / 3.40 -> 2.38 / 30%. The matched random arm still shows no accuracy benefit at
any rate. The falsified abstention-location claim stays falsified and more sharply: lift at the 70%
target is night 0.12, am_rush 0.79, **midday 1.77, pm_rush 1.83**, evening 0.65.

---

## THE ONE GENUINE SURPRISE — `split-CP Ridge std 0.103` is also facility 8, and it is DEAD

**Not prespecified** (section 5 deliberately recorded no expectation for EXP-020), and it is the batch's
only real surprise.

| base learner | split-CP sd | ACI sd | split-CP / ACI |
|---|---|---|---|
| RandomForest | 0.0399 -> 0.0401 | 0.0106 -> 0.0075 | 3.8x -> **5.3x** |
| GradBoost | 0.0410 -> 0.0408 | 0.0049 -> 0.0050 | 8.4x -> 8.2x |
| **Ridge(linear)** | **0.1030 -> 0.0338** | 0.0126 -> 0.0079 | 8.2x -> **4.3x** |

**Mechanism, checked on the unit before the sentence was written (B14).** Ridge split-CP at facility 8
scores **PICP 0.4365**; the next-lowest facility is 0.798. One facility produces the entire 0.103. Ridge
split-CP's mean coverage also jumps 0.8835 -> 0.9048 once it is removed.

**What dies.** EXP-020's recommended manuscript sentence — *"split-CP's reliability collapses to std
0.103 under a weak learner while the adaptive family holds at 0.013"* — **must not be used.** After the
exclusion it is 0.034 vs 0.008. The reframed range "3.8-8.4x lower dispersion at every base learner"
becomes **"4.3-8.2x"**, and the ordering changes: RandomForest strengthens, Ridge weakens, GradBoost is
flat. The qualitative claim — the adaptive family is several times less dispersed at every base learner —
survives at every learner and is what should be written.

**What this does NOT invalidate.** EXP-020 used `split-CP Ridge std 0.1027 -> 0.1030` as a negative
control for the C01/C06 correction. As a *control* it remains valid: it tested whether the correction
moved split-CP, and it did not. But the number it reproduced was an artifact. **Reproducing an archived
number validates the pipeline, not the number** — recorded as LESSONS_LOG **B18**. This is the second
time in two sessions that a dramatic dispersion figure has turned out to be facility 8 (the first was
EXP-013's F2 collapse), and both were found only by opening the facility.

## THE MECHANISM BEHIND EVERY DIRECTION IN THIS BATCH — one sentence

Facility 8 is a **discriminating** unit: catastrophic for the weak and parametric methods (Ridge split-CP
0.437, NGBoost 0.487, EnbPI 0.664) and handled comfortably by the adaptive ones (ACI 0.928, AgACI 0.948).
It was therefore *flattering every comparison we make*. Removing it necessarily weakens comparisons whose
denominator is a baseline's failure (EnbPI/ACI, M02's Belgrade dispersion, the Ridge case) and strengthens
those resting on the adaptive family's own tightness (split-CP/ACQR 6.20x -> 7.76x, ToD-ACI's spread
0.0280 -> 0.0214), because ACI's dispersion falls proportionally more than split-CP's. Both directions
follow from one fact and should be explained that way in the manuscript rather than reported as a list.

- **Read.** The exclusion is right, and it costs us less than it gains: three absolute worst-case claims
  and one Ridge illustration are restated downward, one manuscript sentence dies, Table 4 and the whole
  of Birmingham are untouched, and the paper's central dispersion claim improves by 25%.
- **Next:** task 5b — the deferred EXP-022 orthogonal re-run on the three rolling-origin fold test
  windows and on Birmingham (D-016 #5), now unblocked. Then task 6, the allocation vignette.

### EXP-028 — 2026-09-04 — R-Phase 3b task 5b: the orthogonal check on the folds and on Birmingham
- **Prespecified before the run:** `04_experiments/2026-09-04-task5b-orthogonal-PRESPECIFICATION.md`,
  including the two arms' definitions, the population, and the prediction that Birmingham's ToD-ACI would
  be bit-identical to ACI.
- **Scripts:** `03_code/src/conformal/2026-09-04-orthogonal-folds-birmingham.py` (run, resumable, flushed
  per unit), `2026-09-04-orthogonal-5b-summary.py` (analysis), `2026-09-04-daily-coverage-diagnostic.py`
  (X09). **Outputs:** `2026-09-04-orthogonal-5b-{cells,summary}.csv` (8,808 cell rows, 128 units),
  `2026-09-04-daily-coverage-belgrade.csv`, `2026-09-04-window-confound.csv`.
- **Population:** dynamic on each unit's OWN training window (I05), non-degenerate, and **not
  low-information on the scored window** (D-018). Exclusions came out **fold-dependent, as the rule
  requires and as D-018 anticipated: F1 -> {1}, F2 -> {1, 8}, F3 -> {1, 8}, Birmingham -> {}.**
  Facility 8 is still healthy through 14 March and dies inside F2's window. This is the first direct
  demonstration that applying the rule to the whole frame rather than the scored window would be wrong.

**WHAT REPLICATES — the EXP-022 transfer rule, on three independent train/test windows.**

| axis | fold | Cramer's V | ToD-ACI structure removed | global ACI |
|---|---|---|---|---|
| time_of_day | F1 / F2 / F3 | 1.000 | **94.2% / 95.8% / 100% (at floor)** | 38.6% / 22.7% / **-6.3%** |
| occupancy_tercile | F1 / F2 / F3 | 0.702 / 0.641 / 0.597 | **94.9% / 86.7% / 83.0%** | 67.6% / 64.3% / 58.0% |

Against EXP-022's main-split values (post-X08: on-axis at the noise floor, tercile 78%), the two
interpretable legs reproduce in every fold. Worst-cell protection holds throughout: ToD-ACI's worst
facility-bucket cell is **0.771 / 0.792 / 0.813** against split-CP's **0.563 / 0.525 / 0.634**, with
**4 / 1 / 0** cells below 0.80 against split-CP's **21 / 17 / 11**. Global ACI's negative figure in F3 is
the same honest finding EXP-021 and EXP-022 both recorded — on a *conditional* criterion global ACI is
not better than split-CP, and it is the *conditional* variant the paper should recommend.

**THE PREDICTED POSITIVE CONTROL FIRED. Birmingham lies entirely inside hours 10-15 in every split**, so
under EXP-021's bucket definition it has **one** ToD level and ToD-ACI reduces to global ACI. The run
asserted this on every unit: **28 of 28 bit-identical bounds.** That is property **P14** demonstrated on
real data rather than on a synthetic fixture, and it was prespecified as an expectation, not read off
afterwards. EXP-021's note that "the night bucket will be empty on Birmingham" understated it: four of
the five buckets are empty.

**BIRMINGHAM SHOWS NO MEASURABLE WITHIN-DAY CONDITIONAL STRUCTURE.** On the prespecified secondary arm
that conditions on hour-of-day (6 levels, the only axis this city admits), split-CP's excess dispersion
on hour_of_day is **0.0084** — essentially the matched noise floor. There is almost nothing to remove, so
the conditioning question cannot be tested on this city at all. **Honest finding against conditioning:**
on the occupancy-tercile axis the hour-conditioned method is *worse* than global ACI (excess 0.0796 vs
0.0311), consistent with EXP-022's "conditioning on the wrong axis costs you off-axis".

---

## D-016 #5 CANNOT BE CLOSED. The day-of-week leg is permanently indicative only.

This was the point of task 5b, and the answer is negative on **both** cities, for two different and
independently sufficient reasons. Neither is fixable with existing data.

**(1) Birmingham's cells are too small.** Facility x weekday cells hold a median of **19** observations
(min 6, max 26): **0 of 191 cells reach the prespecified `MIN_CELL = 30`.** Lowering that threshold after
seeing this would be changing the criterion after seeing the result, which the prespecification forbids.

**(2) The Belgrade folds make the confound WORSE, not better — because of a new data defect (X09).**

## X09 — NEW DATA DEFECT: the Belgrade export covers calendar days very unevenly

Found while diagnosing why fold F1's day-of-week partition showed Cramer's V = **0.476** against
time-of-day, where a regular grid should give ~0.

**What it is.** Of the 18 days in the Belgrade record, **eight are below 90% coverage** and the spread is
extreme: **15 March carries 864 of a possible 6,912 rows (12.5%), spanning only 3 distinct hours of 24.**
4 March is 33.3%, 12 March 33.7%, 13 March 50.3%, 16 March 53.5%. **The pattern is present in
`01_data/raw/belgrade_RAW.csv`** (15 March: 96 timestamps against 704 on a full day), so it is a source
property, not a pipeline artifact — the `use_15` filter removes 0-2% of rows on any day. Same class as
X08 and S02/X01, and invisible to every structural integrity check for the same reason (B15).

**What it does — measured, not argued:**

| window | equivalent full days | worst day's coverage | **V(weekday, time-of-day)** |
|---|---|---|---|
| F1 fold test (Mar 13-15) | **1.61** | 12.5% | **0.476** |
| F2 fold test (Mar 16-18) | 2.39 | 53.5% | 0.292 |
| F3 fold test (Mar 19-21) | 2.66 | 78.8% | 0.203 |
| main test split (Mar 18-21) | 3.52 | 78.8% | **0.153** |

A partially covered day contributes only some hours, so weekday and time-of-day stop being separable —
and time-of-day is precisely the axis ToD-ACI conditions on. **The association is worst in exactly the
folds D-016 #5 proposed to use to fix it.** Any day-of-week "transfer" measured on the folds is partly
the conditioning axis reappearing under another name, which is why the fold day-of-week figures are
excluded from the table above rather than reported.

**Consequences.**
1. **The EXP-022 day-of-week leg (45% pre-X08, 30% post-X08) stays INDICATIVE ONLY, permanently.** It
   must be labelled as such wherever it appears, and the dose-response should be presented on its two
   sound legs with day-of-week as a caveated third point.
2. **The rolling-origin folds are not three equal windows.** EXP-026's conclusions are unaffected —
   coverage is a per-row mean and its inference is facility-clustered at n=22 — but describing the design
   as "three three-day test windows" is inaccurate: they hold **1.61, 2.39 and 2.66 equivalent full days**.
   The manuscript and the ESM must say so.
3. **A hypothesis, labelled as one and NOT asserted:** 15 March is both the least-covered day in the
   export and the day facility 8 stops varying (X08: exactly 0.0 from 15 March). A partial collection
   outage on that date is a plausible common cause. We have no evidence for it beyond the coincidence and
   should not claim it; the statutory request to Parking Servis is the right place to ask.
4. **Nothing in the thesis is threatened.** No coverage, dispersion or worst-cell result depends on equal
   daily coverage; only the day-of-week analysis does, and that analysis is now honestly retired.

- **Read.** Task 5b delivered the replication it could and a clean negative on the question it was set.
  The transfer rule now rests on three independent folds instead of one split, the P14 reduction property
  is demonstrated on real data, and the day-of-week leg is retired with a measured reason rather than
  left as a claim a referee would have broken.
- **Next:** R-Phase 3b task 6 — the allocation vignette (D01, D02, D03), the last item before R-Phase 4.

### EXP-029 — 2026-09-04 — R-Phase 3b task 6: the allocation vignette. **The archived effect was one dead sensor.**

- **Prespecified before the run:** `04_experiments/2026-09-04-task6-allocation-vignette-PRESPECIFICATION.md`
  — arms, seed count, capacity definition, anchor rule, the numeric demotion rule, and the honesty guard.
- **Scripts:** `03_code/src/conformal/2026-09-04-vignette-repro-gate.py` (the archived script with **only
  its three output paths changed**, diffed to prove it), `2026-09-04-allocation-vignette.py` (the run,
  resumable, flushed per window x seed), `2026-09-04-vignette-summary.py` (analysis + diagnostics).
- **Outputs:** `05_results/tables/2026-09-04-vignette-{seeds,summary,contrasts,anchors,capacity-proxy,
  x08-attribution,overflow-capability}.csv`, `2026-09-04-vignette-repro-control{,-requests}.csv`,
  `05_results/figures/2026-09-04-vignette-overflow-capability.png`.
  **Nothing logged was overwritten.** Gate re-verified after the run: **50 / 48 / 130, zero drift.**

**THE GATE PASSED FIRST (the EXP-027 pattern, B17).** The archived script, unchanged but for its output
paths, reproduced the logged EXP-015 summary exactly — **8 checks, 0 failures**: POINT 1.0000 / 0.1483 /
1.1342 / 3.2228, INTERVAL 1.0000 / 0.0000 / 1.1834 / 3.2228. So the "before" column of every delta below
is the number the paper actually published, and the v1 pipeline is sound end to end. Per **B18**, that
validates the pipeline and says nothing about whether 0.1483 was ever meaningful. It was not.

## THE RESULT: the outcome event does not occur on the healthy base, in either window

Base **20 facilities** (`core.low_information_facilities` returns **{8}** on both scored windows, computed
never hardcoded; distinct-reading gap republished on this window: facility 8 -> 2, next lowest -> 33
weekday / 43 weekend, so B16's [3, 60] insensitivity band holds here too). Weekday Mar 20-21 = **167**
scored slots, weekend Mar 18-19 = **147**. Anchors, recomputed from training data of the matching day
type: weekday **{9, 12, 7, 13}**, weekend **{9, 23, 18, 5}**. Matched constant margin `m` = **9.78** /
**9.01** spaces.

| window | contrast | mean | 95% CI | seeds positive | seed sd |
|---|---|---|---|---|---|
| weekday | overflow reduction POINT - INTERVAL (pp) | **0.0000** | [0.0000, 0.0000] | **0 / 20** | 0.0000 |
| weekday | additional straight-line distance, INTERVAL - POINT (m) | **0.0** | [0.0, 0.0] | 0 / 20 | 0.0 |
| weekend | overflow reduction POINT - INTERVAL (pp) | **0.0000** | [0.0000, 0.0000] | **0 / 20** | 0.0000 |
| weekend | additional straight-line distance, INTERVAL - POINT (m) | **+57.1** | [+50.4, +64.2] | 20 / 20 | 16.2 |
| weekend | MARGIN - INTERVAL, additional straight-line distance (m) | **+268.4** | [+255.3, +281.9] | 20 / 20 | 30.8 |

**All three policies overflow 0.0% of requests, on all 20 seeds, in both windows, and all three assign
100% of requests.** On the weekday window INTERVAL and POINT make **identical** assignments — the
additional straight-line distance is 0.0 m, not merely small. On the weekend INTERVAL is more
conservative than POINT at a cost of **57 m** and buys nothing, and the matched-margin control is more
conservative still at **268 m** and also buys nothing. The negative control therefore did its job in the
only way it could here: it confirms that conservatism in this setting is a pure cost.

## MECHANISM — 89 of 89 archived overflows were facility 8, and the share is exactly 1.000

`2026-09-04-vignette-x08-attribution.csv`:

| policy | requests sent to facility 8 | overflowed there | total overflows | share of policy's overflows at facility 8 |
|---|---|---|---|---|
| POINT | **105 / 600** | **89** (84.8% of them) | **89** | **1.0000** |
| INTERVAL | 14 / 600 | 0 | 0 | — |

Facility 8's capacity proxy in the archived design was **109 — the constant its dead sensor reports
inside the test window** (X08), while its training maximum is **65**. So the archived vignette read a
capacity off the window it was scoring (D01) and then scored a policy against a series pinned at that
value. The point forecaster, trained on facility 8's *healthy* training window (std 18.1), predicts
occupancy in the 40-65 range, sees ~59 free spaces, and assigns; the driver arrives at a garage reporting
109 of 109. ACQR's score pool absorbs residuals of ~59 within a few steps, the interval widens past the
capacity line, and INTERVAL stops assigning. **That is the entire published effect.**

## THE INPUT-ONLY CAPABILITY CHECK — why nothing replaces it

`2026-09-04-vignette-overflow-capability.csv`, computed on the inputs alone with no policy involved.
Under the archived outcome definition (a facility is full when `capacity - occupancy < 1 space`):

| window | population | slots at or above `cap - 1` | peak occupancy reached |
|---|---|---|---|
| weekday | healthy base (20 facilities, 3,340 facility-slots) | **0** | 98.7% of capacity (facility 9) |
| weekday | facility 8 alone (167 slots) | **140** | **167.7% of capacity** |
| weekend | healthy base (2,940 facility-slots) | **0** | 99.8% of capacity (facility 9) |
| weekend | facility 8 alone (147 slots) | **15** | **167.7% of capacity** |

**No healthy Belgrade facility is ever full under this design's own definition of full.** The reason is
structural, not incidental: "full" is defined as an **absolute** margin of one space, applied to
facilities spanning **53 to 1,549** spaces. A 1,549-space garage at 98.7% occupancy has 20 free spaces
and is not "full"; a 53-space lot would need to be at 98.1% to qualify. The only unit that could ever
clear the bar is one whose reported occupancy **exceeds its own capacity proxy**, which is precisely what
a stuck sensor does and what nothing healthy does.

Reported for decision support and **not used to compute any policy comparison** (that would be changing
the criterion after seeing the result — forbidden, section 6 of the prespecification): on a **relative**
fullness threshold the weekend window does carry content — **20.8%** of healthy facility-slots sit at or
above 90% of capacity, across **12 facilities**, falling to 0.68% at 99%. The weekday window carries
much less: 5.5% at 90%, concentrated in facility 9. **The weekend is the informative window, and the
archived design used weekday afternoons only.**

## WHAT THIS COSTS AND WHAT IT DOES NOT

- **The thesis is untouched.** The per-facility reliability gap, Table 4, the dispersion results, the
  rolling-origin inference and both cities' coverage numbers do not depend on the vignette in any way.
- **A headline claim is dead.** "POINT overflow 14.8% -> INTERVAL 0.0%, at +49 m detour" must not appear
  in the manuscript, the ESM, the cover letter or the response letter in any form. Under the author's
  operational reading this vignette was the paper's payoff, which is why it is recorded here as a
  headline loss rather than a footnote.
- **D02 is closed anyway:** "detour" is replaced by "additional straight-line distance" throughout the
  new script, its CSV columns and its figure. The quantity was always a haversine distance between two
  points and the old name asserted routing that was never performed.
- **D01 is closed and is what exposed this:** capacity now comes from the training window only. The
  correction is 0-9 spaces at five healthy facilities and **44 spaces at facility 8**.
- **D03 is closed procedurally but has nothing to measure:** 20 seeds, distribution and CI reported. The
  prespecified demotion rule (`Delta <= 0` in >= 2 of 20 seeds, or CI includes 0) is **met in both
  windows**, so the vignette demotes on its own written rule — but it demotes because the effect is
  *identically zero*, not because it is unstable, and the log should say which.

**A branch the prespecification did not anticipate, recorded rather than retrofitted.** Section 5 defined
confirms / weakens / seed-sensitive / contradicts. It did not contemplate an outcome event with **zero
occurrences in either arm**, which is neither an effect nor an unstable effect. The demotion rule happens
to fire correctly, but by arithmetic accident. **B20** records the check that would have caught this in
ten seconds before the experiment was designed.

- **Read.** The last unverified experiment in the paper turns out to have been measuring a broken sensor,
  found by applying a data-quality rule that was adopted for entirely unrelated reasons. This is the
  **third** headline figure in three sessions that is facility 8 alone — after EXP-013's "split-CP
  collapses in fold F2" and EXP-020's `split-CP Ridge std 0.103` — and, as in both of those, it was found
  only by opening the unit. D-018 has now paid for itself three times over.
- **Next:** a decision on the vignette's future — **D-019**, four options laid out, recommendation
  recorded, author's call. R-Phase 3b task 6 is **complete as an experiment**; what remains is a
  manuscript decision, not a measurement.

### EXP-030 — 2026-09-04 — R-Phase 4: the two-level inference redesign. **The population level cannot separate the methods; the facility level separates them decisively — and the facility-level SAFE leg turns out to measure over-coverage.**

- **Prespecified before the run:** `04_experiments/2026-09-04-rphase4-inference-PRESPECIFICATION.md`
  (fifth prespecification; estimand, families, Holm, tie-break and all four outcome branches fixed first).
- **Script:** `03_code/src/conformal/2026-09-04-phase4-inference.py`.
- **Outputs:** `05_results/tables/2026-09-04-phase4-{gate,population,facility,contrasts,safe-mechanism}.csv`.
  Nothing logged was overwritten. Gate re-verified after the run: **50 / 48 / 130, zero drift.**
- **No model was re-fitted.** Established on the inputs first: **audit I06's bootstrap leg was already
  closed** — the logged run used `BOOT_B = 10_000` with `core.block_length_for_cadence(cadence, 3.0)`
  (36 rows Belgrade, 6 Birmingham), not the audited 500 / 20-row design. What remained of I06 was
  multiplicity, which no paired test in this project carried. R-Phase 4 is therefore re-aggregation plus
  inference, exactly as the remediation plan's fix-class table predicted.

**THE GATE PASSED FIRST.** With the exclusion filter OFF, every aggregate recomputed from the logged
per-facility CSVs matched `2026-09-02-corrected-headline-gcal.csv` to 4 dp — **56 checks, 0 failures** —
before any filtered number was read. Exclusion sets computed, never hardcoded: Belgrade **{1, 8}** ->
n = 21; Birmingham **{}** -> n = 28.

## POPULATION LEVEL — 7 of 8 EXACT, 8 of 8 SAFE. The predicted branch fired.

Facility-clustered, epsilon = 0.02, TOST at alpha = 0.05 (equivalently the 90% CI inside [0.88, 0.92]),
Holm within city over the four core methods. The t-interval and the B = 10,000 facility bootstrap agree
on **every one of the eight cells**, so the prespecified tie-break was never needed.

| city | method | n | mean PICP | sd | 90% CI | EXACT | SAFE | Holm p |
|---|---|---|---|---|---|---|---|---|
| Belgrade | split-CP | 21 | 0.9008 | 0.0411 | [0.8853, 0.9163] | YES | YES | 0.0226 |
| Belgrade | CQR | 21 | 0.8995 | 0.0289 | [0.8886, 0.9103] | YES | YES | 0.0058 |
| Belgrade | ACI | 21 | 0.8913 | 0.0077 | [0.8883, 0.8942] | YES | YES | <1e-4 |
| Belgrade | ACQR | 21 | 0.8940 | 0.0053 | [0.8920, 0.8960] | YES | YES | <1e-4 |
| Birmingham | split-CP | 28 | 0.9066 | 0.0513 | [0.8901, 0.9231] | **NO** | YES | 0.0890 |
| Birmingham | CQR | 28 | 0.9021 | 0.0417 | [0.8887, 0.9155] | YES | YES | 0.0314 |
| Birmingham | ACI | 28 | 0.8890 | 0.0155 | [0.8840, 0.8940] | YES | YES | 0.0096 |
| Birmingham | ACQR | 28 | 0.8928 | 0.0234 | [0.8853, 0.9003] | YES | YES | 0.0113 |

**This is the NON-DISCRIMINATING branch, written into the prespecification in advance and now observed.**
Population-level equivalence testing declares three of the four methods equivalent to nominal in both
cities, and the fourth (Birmingham split-CP) fails **on the upper side** — for **over-covering**, its CI
reaching 0.9231. The instrument the field routinely uses cannot tell these methods apart, and where it
does speak it flags the conservative method rather than the unreliable one.

## FACILITY LEVEL — equivalence NOT claimed. This is where the methods separate.

| city | method | sd | worst facility | worst PICP | frac below nominal | *retired* "CI contains 0.90" |
|---|---|---|---|---|---|---|
| Belgrade | split-CP | 0.0411 | 9 | **0.7872** | 0.381 | 0.619 |
| Belgrade | CQR | 0.0289 | 9 | 0.8266 | 0.429 | 0.762 |
| Belgrade | ACI | 0.0077 | 13 | 0.8690 | 0.952 | 0.952 |
| Belgrade | ACQR | **0.0053** | 13 | **0.8788** | 0.952 | 0.952 |
| Birmingham | split-CP | 0.0513 | 7 | **0.7868** | 0.464 | 0.714 |
| Birmingham | CQR | 0.0417 | 7 | 0.7794 | 0.393 | 0.750 |
| Birmingham | ACI | 0.0155 | 20 | 0.8659 | 0.857 | **1.000** |
| Birmingham | ACQR | 0.0234 | 22 | 0.8537 | 0.786 | 0.893 |

Belgrade split-CP / ACQR dispersion **7.76x**, matching EXP-027 exactly (B17 base check). The worst
*facility* is 0.787 / 0.787; the worst *facility x time-of-day cell* is **0.516** (EXP-021) — two
different granularities that must never be conflated in the prose.

**The retired criterion is why the archived manuscript said "100% of facilities statistically at
target":** under "the CI contains 0.90", Birmingham ACI scores **1.000** and Belgrade ACI/ACQR **0.952**,
while split-CP scores 0.619 / 0.714. A criterion that rewards a wide interval flattered our own methods,
which is exactly what **I01** said and is now measured rather than asserted.

## THE FINDING THAT WAS NOT PREDICTED: the facility-level SAFE leg is a test for OVER-COVERAGE

`2026-09-04-phase4-safe-mechanism.csv`. The prespecified facility-level safety leg (one-sided lower bound
>= 0.88) is passed by **0 of 21** Belgrade facilities for both ACI and ACQR, against **9 of 21** for
split-CP and 8 of 21 for CQR — apparently a result against the adaptive family. Opening the unit (protocol
step 2) shows what it actually measures:

| city | method | median point-to-lower-bound gap | PICP a facility NEEDS to pass SAFE | passers | of those, PICP >= 0.92 |
|---|---|---|---|---|---|
| Belgrade | split-CP | 0.0382 | **0.918** | 9 | 7 |
| Belgrade | ACQR | 0.0295 | **0.910** | 0 | — |
| Birmingham | split-CP | 0.0582 | **0.938** | 7 | **7 of 7** |
| Birmingham | ACI | 0.0631 | **0.943** | 1 | 1 |

At n ~ 1,015 rows (Belgrade) and ~135 (Birmingham) the one-sided lower bound sits **3 to 6 coverage
points** below the point estimate. **A facility must therefore over-cover by 1 to 4 points to be called
"safe".** The lowest-covering Belgrade facility that passes has PICP 0.914; in Birmingham every single
passer has PICP >= 0.940. A method sitting exactly at nominal at every facility fails at every facility,
by construction. **This is the same error I01 identified, reappearing in the safety leg rather than the
exactness leg, and it is a property of n, not of any method.** The criterion is reported as prespecified
and is NOT changed after the fact (that would be the forbidden repair); what changes is the
interpretation, which is stated with these numbers.

## CONTRASTS — dispersion is decisive, efficiency is mixed and partly against us

Holm within family within city; facility-paired Wilcoxon; paired facility bootstrap B = 10,000.

- **Dispersion (family D), all 8 contrasts survive Holm.** Belgrade ACQR vs split-CP mean |PICP - 0.90|
  0.0060 vs 0.0295 (diff **-0.0235**, CI [-0.0356, -0.0128], 81% of facilities favour ACQR, Holm
  p = 0.0024); Birmingham ACI vs split-CP -0.0227, CI [-0.0349, -0.0112], 79%, Holm p = 0.0032. Every
  bootstrap CI excludes zero.
- **Efficiency (family E), Belgrade: two wins, one null, one loss.** ACQR vs split-CP **-4.59 Winkler**,
  CI [-6.58, -3.03], **100% of facilities**, Holm p < 1e-4. ACQR vs CQR **-0.29, CI [-0.76, +0.08],
  p = 0.585 — not significant**, i.e. ACQR's adaptivity is bought at **no measurable efficiency cost
  relative to its own base method**, which is the cleanest way to state the trade. ACI vs CQR is
  **+2.82 Winkler against us** (Holm p = 0.0002, only 9.5% of facilities favour ACI) — reported, not hidden.
- **Efficiency, Birmingham: NOTHING survives Holm.** All four contrasts have Holm p >= 0.34 and CIs
  spanning zero. On Birmingham the four methods are **indistinguishable on Winkler**, so no efficiency
  claim may be made there in either direction.

## WHAT THIS COSTS AND WHAT IT BUYS

- **Dead:** "100% of facilities statistically at target" and every paraphrase (I01/I02); any claim that
  the adaptive methods are *safe at every facility* — at facility level they are safe at none, for the
  reason above; and any Birmingham efficiency claim.
- **Strengthened, and this is the paper's central argument now demonstrated with its own numbers:**
  population-level equivalence testing passes 7 of 8 configurations and cannot separate methods whose
  facility-level worst case differs by **11 coverage points** (0.787 vs 0.879) and whose dispersion
  differs by **7.76x** — while the worst facility x bucket cell differs by 33 points (0.516 vs 0.842).
- **Unchanged:** every EXP-026 fold-level conclusion; Table 4; both cities' means.
- **I01, I02, I03, I04, I06 and D04 are closed.** R-Phase 4's display item T3' is built from
  `-population` and `-facility`.
- **Next:** T3' assembly and the T6 protocol-sensitivity table (D-020), then R-Phase 5.

### DISPLAY ITEMS — 2026-09-04 — T3' and T6 built under D-020 (no experiment; assembly from logged CSVs)

- **Script:** `03_code/src/conformal/2026-09-04-display-items.py`. **No model was re-fitted**; every cell
  traces to a CSV in `05_results/tables/`. Gate re-verified after the build: **50 / 48 / 130, zero drift.**
- **Outputs:** `2026-09-04-T3prime-two-level-inference.csv` (10 rows), `2026-09-04-T6-protocol-sensitivity.csv`
  (29 rows over **8 distinct protocol choices**).

**T3' — the two-level table.** Four core methods x two cities, carrying population level (mean PICP,
t and bootstrap 90% CIs, EXACT, SAFE, Holm p, mean Winkler) beside facility level (across-facility sd,
worst facility and its PICP, fraction below nominal) with `facility_equivalence_claimed = False` on every
row. Cell-level reference rows for **ToD-ACI (worst cell 0.8421, 0 cells below 0.80)** and
**Mondrian-split-CP (0.6200, 15 cells below 0.80)** are carried with `scope` marking them as T4 material,
so no row is ambiguous about which level it speaks to.
**Recomputed on the excluded base, and it differs from the pre-exclusion figure that is in the trackers:**
split-CP has **12** facility x bucket cells below 0.80 out of **105** (MIN_CELL = 30, n = 21 facilities),
not the 14 of 110 recorded from EXP-021's pre-exclusion run. Both are correct on their own base; **the
manuscript must quote 12 of 105** and the pre-exclusion figure must not appear beside it (B17).
**Mondrian is worse than split-CP on the count** (15 cells below 0.80 against 12) while better on the
worst cell (0.620 against 0.516) — reported as found, not smoothed.

**T6 — the evaluation-protocol sensitivity table.** Eight protocol choices, each as
choice -> mechanism -> measured effect, with a `direction_vs_our_claim` column and a `provenance` column
naming the source CSV for every row:
1. **EnbPI outcome release** (C07), paired inside one fit: Belgrade 0.8999 -> 0.9032, Birmingham
   0.8448 -> 0.8471. **Against us.**
2. **Step-size gamma**, fixed 0.05 vs calibration-selected: Belgrade ACI 0.8852 -> 0.8913 (sd 0.0060 ->
   0.0077), ACQR 0.8863 -> 0.8940 (sd 0.0050 -> 0.0053); **Birmingham is the larger effect** — ACI sd
   0.0094 -> 0.0155, ACQR 0.0136 -> 0.0234. **We report the LESS flattering configuration**, which is worth
   one sentence. **Built-in negative control: split-CP is bit-identical across the two arms**, as it must
   be, since gamma does not touch it.
3. **Low-information exclusion** (X08/D-018): the spine **6.20x -> 7.76x**, reproducing EXP-027 exactly
   (B17 base check passes), with the components published and the honest counterweight in the same row.
4. **Unit of inference** (I04), pooled rows vs facility-clustered: p-values weaken by **1.8x to 411x** on
   the published base; all four contrasts still survive Holm. **Against us, and it is the strongest row in
   the table** because it indicts a routine practice rather than anything specific to this paper.
5. **Certification criterion** (I01): the retired "CI contains 0.90" rule certified **our own ACI at
   0.952-1.000** against split-CP's 0.619-0.714. **Against us.**
6. **Capacity proxy** read off the scored window (D01): an entire published headline effect,
   **14.83 pp -> 0.0000 pp**. **Against us.**
7. **Safety bound applied at facility level** (I01, second-order): a facility needs PICP **0.910-0.943**
   to pass, so a method at nominal fails everywhere (B22).
8. **Interpolation across a night boundary** (S02/X01): exposure removed and quantified, but the **effect
   is NOT separately attributable** — the data fix and the C01 fix landed in the same rerun. Emitted with
   that stated in the row rather than dropped or quietly included.

**A provenance gap found while building it, and NOT papered over.** The **C01 order-statistic attribution**
(PICP 0.8988 -> 0.8858, MPIW -15.4%, Winkler -7.8%, controlled test on 8 Belgrade facilities) is recorded
in EXP-019's prose but has **no CSV anywhere in the tree** — the same class of gap EXP-027 found for the
core-headline and E3 summaries. Under the project's own rule (every manuscript number traces to a CSV) it
**cannot be printed in T6 as it stands.** It is therefore absent from the table and flagged here. Closing
it would mean running the retired pre-C01 path from `_retired/`; that is an R-Phase 6 decision, not a
silent inclusion.

**Wording check for the presubmission enquiry:** T6 has 8 protocol choices, of which **6 are errors**
(C07, X08 omission, pooled inference, the certification criterion, the capacity proxy, night
interpolation) and 2 are choices rather than errors (gamma selection, the facility-level safety bound).
The enquiry's phrase "six evaluation-protocol errors" is therefore **correct as written** and should not
be changed to eight.

### EXP-031 — 2026-09-04 — R-Phase 5: (A) the ESM null, (D') the corrected failure-case arm, D05 and M02. **(D') is DEAD, and it dies on arithmetic rather than on data: the point policy withdraws at the same step.**

- **Prespecified before the run:** `04_experiments/2026-09-04-rphase5-PRESPECIFICATION.md` (sixth
  prespecification), with **amendment 1** (section 8, written before any (D') outcome was computed) and
  **amendment 2** (section 9, written after legs 1–2 returned and before its two checks were run; it says
  so, and it changes no criterion and no claim).
- **Scripts:** `2026-09-04-rphase5-esm-capability.py`, `-failure-case.py`, `-level-sweep.py`,
  `-failure-case-summary.py`, `-d05-sweep.py`.
- **Outputs:** `05_results/tables/2026-09-04-esm-overflow-capability.csv`,
  `2026-09-04-failure-case-{leg1-facility8,leg2-injection,level-sweep,mask-identity,feature-fidelity,esm-summary}.csv`,
  `2026-09-04-d05-threshold-sweep.csv`. **Nothing logged was overwritten**; every script refuses to
  overwrite its own output. Gate re-verified after every result-generating run: **50 / 48 / 130, zero drift.**

## SECTION 0 KILLED OR RESHAPED THREE OF THE FOUR ITEMS BEFORE ANY OUTCOME WAS COMPUTED

**(a) Facility 8's feed was already dead during CALIBRATION.** It goes flat at **0.0 on 2017-03-14 23:00**
— inside the calibration split — and runs constant for **921 rows**; the event inside the test window is a
**regime change 0 → 109 at 2017-03-19 18:00**, not an onset. **487 of its 760 calibration rows (64.1%)**
lie inside that dead run, so its score pool and its selected gamma were calibrated largely **on** the
anomaly. And the archived weekday window contains **no transition at all** — all 167 of its facility-8
slots are post-onset, the window opening ~42 h after the change — so the archived "POINT sent 105,
INTERVAL sent 14" was a **steady-state** contrast that could never have demonstrated withdrawal *within a
few steps*, independently of B21's configuration objection. **D-019 (D) was even less deliverable than the
resolution recorded.** The claim was narrowed accordingly before anything ran.

**(b) The (A) numbers reproduce exactly; the gap was provenance.** 98.74% / 99.83% peak healthy occupancy
and 0 events on both windows all reproduce. But `2026-09-04-vignette-overflow-capability.csv` carries
neither the peak nor the count under the design's **own** rule (`cap - y < 1`) — only `ratio >= 1.0`.

**(c) D05 needed no refit and is nearly vacuous.** `2026-09-02-run-core-methods.py` **tags** `dynamic`
rather than filtering, so facilities 1 (sigma 0.00) and 10 (sigma 3.34) are already in the logged
per-facility CSV. Belgrade's sigma values jump **0.00 → 3.34 → 11.51**, so every threshold in
**(3.34, 11.51]** selects the same 22 facilities; Birmingham's lowest sigma is **33.18**, so every
threshold in [0, 33] selects all 28.

**(d) M02 needed no run**, only a base correction (see below).

## (A) — THE ESM CAPABILITY TABLE. Gate 112 checks, 0 failures.

Every cell of the 2026-09-04 table reproduced to 4 dp before the two new columns were read. The (A)
sentence's numbers now trace to a CSV: peak healthy occupancy **98.741%** (weekday, facility 9) and
**99.828%** (weekend, facility 9); **0 of 3,340** weekday and **0 of 2,940** weekend healthy
facility-slots meet the design's own definition of full; facility 8 alone meets it at **140 of 167** and
**15 of 147**, peaking at **167.69%** of its training capacity.

## (D') LEG 1 — THE REAL CASE. Both policies withdraw at step 0. Lead time ZERO.

`2026-09-04-failure-case-leg1-facility8.csv`. Corrected pipeline; `cap_train = 65.0` and
`cap_fullrecord = 109.0` reproduce the capacity-proxy CSV exactly; gamma 0.100; 1,015 test rows,
onset at index 428.

| quantity | INTERVAL | POINT |
|---|---|---|
| fraction of the 428 **pre-onset** slots withdrawn | **0.0000** | **0.0000** |
| withdrawal step after the regime change | **0** | **0** |
| **lead time** | **0 steps** | — |
| fraction of the 587 post-onset slots withdrawn | 0.9591 | 0.9591 |

**Branch B' fired** (amendment 8.2). Withdrawal is exactly coextensive with the 563-row 109 run and
**reverses** when the feed returns to 0 at 2017-03-21 16:55 — it tracks the feed in both directions.
**The prediction recorded in section 5 (branch B, already withdrawn pre-onset) was WRONG**: facility 8 is
withdrawn on 0.0% of pre-onset slots. That does not rescue the claim.

**Mask identity (9.3).** Over all **587** post-onset slots the two policies' availability masks are
**identical** — 563 withdrawn by both, **0 interval-only, 0 point-only**. Request counts are therefore
identical for **every** demand seed **by construction**, so the >= 20-seed simulation was **not run** and
the reason is recorded rather than the run being quietly skipped.

## (D') LEG 2 — THE SYNTHETIC PROBE, n = 20 healthy facilities. Unanimous zero.

At the prespecified primary level (**167.69% of each facility's own `cap_train`** — facility 8's observed
overshoot, applied relatively, never absolutely, per B20): **all 20 facilities give
`step_interval = step_point = 0`, lead time 0, maximum lead 0**, with both policies withdrawn on 100% of
post-onset slots. The **plausible control** (feed pinned at the facility's own training median) leaves
**17 of 20** facilities never withdrawing under either policy, so the probe is not merely detecting
constancy. *(A first write-up of this line said 18; the consistency sweep caught it against
`2026-09-04-failure-case-leg2-injection.csv` and it is corrected here rather than silently. The three
exceptions are facilities **9, 12 and 13**, whose training medians sit at **99.77%, 92.62% and 98.23%**
of their own capacity — i.e. precisely inside the 0.90-0.98x band the level sweep identifies below, which
is a coherence check on the sweep rather than a defect in the control.)* Feature rebuild fidelity on the un-injected arm: **98.64–99.09%** agreement with the parquet
features, reported rather than hidden.

## THE MECHANISM, AND IT IS A PROPERTY OF THE FORECASTER

The pipeline is **delta-modelled** — `yhat = occupancy_t + RF(features)` — so the point forecast is
**anchored on the currently reported occupancy**. A reported level above the training capacity proxy is
visible to the **point** forecast at the same step it is visible to the interval, and `cap - yhat` goes
negative at that step. **There is no learning lag for abstention to beat.** The lead time is zero not
because abstention is weak but because the comparator cannot be beaten **by construction** in this regime.

## THE LEVEL SWEEP (9.2) — there IS a regime with a lead, and the record never exhibits it

`2026-09-04-failure-case-{level-sweep,esm-summary}.csv`. Every level reported; each arm **paired against
the same facility's own no-injection baseline**, so no withdrawal is attributed to the injection that
would have happened anyway (B3, B7).

| injected level | withdrawal CAUSED by injection, INT / PT | facilities where POINT never withdraws | median lead | max lead | excess abstention INT / PT |
|---|---|---|---|---|---|
| 0.80 x cap | 1 / 0 | 1 | — | — | -9.8 / -4.3 pp |
| 0.90 x cap | 4 / 0 | **5** | — (unbounded) | — | -8.4 / -4.3 pp |
| 0.95 x cap | 7 / 5 | 6 | 0 | 157 | -3.6 / -4.0 pp |
| **0.98 x cap** | **17 / 11** | **6** | **7 steps (35 min)** | 248 | **+25.2 / +2.0 pp** |
| 1.00 x cap | 18 / 20 | 0 | 0 | 19 | +89.8 / +41.3 pp |
| 1.05 x cap | 18 / 20 | 0 | 0 | 6 | +89.9 / +85.6 pp |
| 1.20 x cap | 18 / 20 | 0 | **0** | **0** | +89.9 / +91.8 pp |
| **1.6769 x cap** (primary) | 18 / 20 | 0 | **0** | **0** | +89.9 / +95.7 pp |

**Sensitivity control (9.1): the instrument is not blind.** The un-injected arm and the plausible control
produced lead times spanning **0 to 304 steps** on the same code path, so the zero at and above capacity
is a real zero rather than an insensitive test (B11, B13).

**The reading, fixed by 9.2 in advance.** A lead time exists **only when the anomalous constant sits just
below capacity** — at 0.98 x cap the interval policy withdraws 17 facilities against the point policy's
11, with 6 facilities the point policy never withdraws at all, at a cost of **+25.2 percentage points** of
abstention against **+2.0**. **The one anomaly this record actually contains sat at 167.69% of capacity,
where the lead is identically zero.** A lead time confined to a regime the data never exhibits is not an
operational finding, and section 9.4 fixed that judgement before the sweep was run.

**The cost that belongs in the same paragraph.** On **un-injected** data the interval policy already
abstains on **10.09%** of post-onset facility-slots against the point policy's **4.30%** — conservatism
with no measured benefit, consistent with EXP-029's +57 m of additional straight-line distance for zero
overflow reduction.

**Therefore: D-019 (D') is NOT DELIVERABLE**, alongside (D) — section 5 branch **G**, reached through
branch **B'**. **(A) stands alone**, and the ESM says so.

**What this buys, and it needs no new display item (D-020 is not reopened).** T6's existing capacity-proxy
row records that the effect went 14.83 pp -> 0.0000 pp. The sweep adds the mechanism: the archived proxy
of **109** placed facility 8 at **exactly 1.00 x its own proxy** instead of 1.68 x the training proxy —
the narrow band where a lead is possible at all — while the corrected proxy puts it far above capacity,
where the lead is identically zero. **Stated with its limit:** the archived run also differed in features,
ACQR implementation and gamma (B21), so this is *a* mechanism for that row, **not** a full accounting of
105 vs 14, and it must not be written as one.

## D05 — CLOSED. Gate 56 checks, 0 failures. Branch H (insensitive), as predicted.

`2026-09-04-d05-threshold-sweep.csv`. Re-aggregation only; the sigma >= 5 arm reproduced
`2026-09-04-x08-core-headline-excl.csv` to 4 dp before any other arm was read. The low-information
exclusion is applied at **every** threshold, so facility 1 can never enter a reported number at any of
them.

- **Birmingham: bit-identical at sigma = 0, 2, 5 and 10** — max |dPICP| and |dSD| are **0.0000**. No
  facility enters or leaves anywhere in [0, 33]. The threshold does no work on Birmingham at all.
- **Belgrade: adding facility 10 (sigma 3.34) moves the headline by at most 0.0036 PICP and 0.0024 sd.**
  Direction, stated because it runs **in our favour**: split-CP PICP 0.9008 -> 0.9044 and sd
  0.0411 -> 0.0435 while ACQR is flat (0.8940 -> 0.8941, sd 0.0053 -> 0.0052), so the **spine strengthens
  from 7.76x to 8.39x** when the rule is relaxed. **`sigma > 5` is therefore conservative**, it is kept as
  the prespecified primary population, and **8.39x is not quoted anywhere** — the published figure stays
  **7.76x** on the prespecified rule (B16).

## M02 — CLOSED with a base correction, no run. (B17)

The published X08-excluded figures already exist in `2026-09-04-x08-e3-summary-excl.csv`: Belgrade
**0.7733 -> 0.8921** (n = 21) with Winkler improving **9.93%**; Birmingham **0.3727 -> 0.9011** (n = 28)
with Winkler improving **57.05%**, unchanged because Birmingham excludes nothing. The widely quoted
Belgrade pair **0.7602 -> 0.8909** and **"11.2%"** are **pre-exclusion**. A base note was added to the
live R-Phase 3b checklist entry in `PROJECT_STATUS.md`; the historical revision-37 log entry is left as
written (A9 convention). **The manuscript, ESM, cover letter and T2 quote 0.7733 -> 0.8921 and 9.9%.**
  *(SUPERSEDED 2026-09-05 by **EXP-033**: the NGBoost reseed moves the published pair to*
  ***0.7736 -> 0.8917*** *with Winkler improving* ***9.76%***, *and Birmingham to* ***0.3722 -> 0.9014***
  */* ***57.00%***. *This entry is left as written; quote EXP-033's figures.)*

- **Read.** R-Phase 5 was budgeted as four experiments and needed **one** new fit-based run: (A), D05 and
  M02 were all answered from logged artifacts once the inputs were measured. The one arm that did run
  killed its own deliverable, and it killed it on arithmetic — the comparator withdraws at the same step,
  by construction — which is a failure mode no amount of extra seeds, facilities or horizons would have
  surfaced. New lessons **B23**, **B24** and **C10**.
- **Next:** R-Phase 6 (lock file, safe runner, manifest, verify.py, licence plan B, and the C01
  provenance gap), then the R-Phase 7 rewrite.

### EXP-032 — 2026-09-04 — R-Phase 6: packaging and the clean room. **Section 0 finds the shipped package is pre-audit in its DATA as well as its code, and that the C01 population is unrecoverable.**

- **Prespecified before anything was built:** `04_experiments/2026-09-04-rphase6-PRESPECIFICATION.md`
  (seventh prespecification). Its section 4 fixes the tolerance table **before** any clean-room output
  exists, on the floor measured in section 0(h).
- **Probe:** `03_code/tests/2026-09-04-determinism-probe.py` → `05_results/tables/2026-09-04-determinism-probe.csv`.
  Contributes to no reported number. Gate re-verified after it ran: **130 frozen files, zero drift.**

## SECTION 0 — SIX FINDINGS THAT CHANGE THE PLAN, ALL ON ARTIFACTS THAT ALREADY EXIST

**(a) The package is rebuilt, not repaired.** The shipped zip carries `belgrade_features.parquet` and
`birmingham_features.parquet` — the **v1** tables with the S01/S02/X01 leakage — and the August code tree
(`run_corrected.py`, the `2026-08-04-*` scripts, plus `conditional_cp.py`, `trust_abstain.py` and
`model_agnostic.py`, all three **retired** in EXP-017). **`core.py` is absent entirely.** Every number the
package could produce is therefore a dead number, which is a stronger statement than R03's
"packaging defect". R02/R03/X02 are confirmed exactly: `05_results/tables` and `figures` are empty
directories, `EXPERIMENTS_LOG.md` is 60 bytes, `run_all.sh` uses `set -e` with **no `pipefail`** and eight
unbounded `until … | grep -q; do :; done` loops, wires in neither `model_agnostic.py` nor `src/figures/*`
while the README claims "every table and figure", and runs the **dead vignette** as its last step.
**`run_all.sh` exists nowhere in the repository** — only inside the zip.

**(b) The package pins the WRONG version, which is worse than not pinning.** `README.md` instructs
`mapie==1.4.1`; every published EnbPI number was computed under **mapie 1.5.0** (EXP-025 lock), and A13
measured that this exact difference already moved 5 of 22 Belgrade facilities. `requirements.txt` also
lists **`statsmodels`, which no live script imports** (`2026-09-03-rolling-origin-inference.py` declines it
in a comment and implements Holm in six lines) and omits `ngboost` entirely.

**(c) A LIVE file carries the retired C01 rule.** `03_code/src/verify_results.py` holds its own local
`split_cp`/`aci` and computes `np.quantile(pool, lv, method="higher")` — the exact call
`core.conformal_quantile`'s docstring warns against, i.e. **C01 itself** — a second definition of the
conformal quantile sitting in the shipped code path. Retired or rewritten on `core.py` before anything
ships (B9).

**(d) The C01 provenance gap is both worse and better than recorded.** **Worse:** the attribution is in
**EXP-017**'s prose, not EXP-019 as three trackers state, and it names *"8 Belgrade facilities"*
**without naming which 8** — so the population is unrecoverable and **the retired pre-C01 path cannot
reproduce 0.8988 → 0.8858 even in principle.** The option the record describes does not do what it was
expected to do. **Better:** C01 is a one-index difference into the same sorted score pool with shared base
learners, so the delta can be measured **paired inside one fit** on the published base — D-017's own
pattern — for a traceable current number, with no retired path. Four options are in prespecification
section 7; the author decides.

**(e) `REPLICATION.md`'s verification targets are all dead, and this is the most damaging thing in the
package.** Its section 5 tells a replicator to expect *"100% of facilities' bootstrap CIs contain 0.90"*
(dead, I01/EXP-030), ACQR std **0.002**/**0.010** (published **0.0053**/**0.0234**), NGBoost **0.760**
and **0.384** (published **0.7733** and **0.3727**, and the pre-exclusion pair is on the never-quote list),
and *"overflow 14.8% → 0.0%, mean **detour** +49 m"* — the dead vignette headline **and** the retired word.
Section 6 states the bootstrap as *"length 20, 500 resamples"* when the logged design is **B = 10,000**
with a cadence-derived 3-hour block. **A replicator following this file today fails every target.** The
fix is structural: R-Phase 6 generates the targets from the current CSVs via `verify.py` rather than
letting anyone type them.

**(f) The licence conflict is a two-file text fix; plan B is already in the package.** The zip's `LICENSE`
**and** `README.md` already state Belgrade CC0 / Birmingham-derived CC BY 4.0 with attribution. The
conflict (R05/X03) is exactly `USER_ACTIONS.md` step 2 ("License: CC0, the platform default") and the
manuscript's Replication section; `REPLICATION.md` §1 additionally asserts the package **is** deposited on
ETS-Data, which it is not and must not be (D-015 #2).

## THE DETERMINISM FLOOR — MEASURED, so the gate's tolerance is not invented

Belgrade facilities 2, 3, 4 (the first three dynamic facilities after `core.low_information_facilities`
removes 1 and 8), t+15, level 0.90, four methods, canonical configuration held fixed (B6). Three arms:
`n_jobs=-1` twice, then `n_jobs=1` — varying the thread count is a direct handle on A8's reduction-order
mechanism, which is the component that differs across machines.

| quantity | max abs, repeat | max abs, all-threads vs 1 thread | max relative |
|---|---|---|---|
| **PICP** | **0.0** | **0.0** | **0.0** |
| MPIW | 0.0 | 3.6e-15 | 2.1e-16 |
| Winkler | 7.1e-15 | 7.1e-15 | 2.2e-16 |

Selected gamma is **identical in every arm**, and **only ACI moves at all** — split-CP, CQR and ACQR are
bit-identical across all three arms, consistent with the sequential stream accumulating what the one-shot
methods do not. **Stated with its limit:** this bounds the thread-reduction term only, and **A13's
cross-version term is ~1e-3 in PICP, six orders larger** — so the exact `==` lock is what makes the clean
room reproduce, and the tolerance covers only the residual. Tolerances fixed in advance: PICP and every
count **exact**; MPIW/Winkler **relative 1e-12**; bootstrap bounds **1e-9**; figures regenerated and never
hashed.

**A decision taken inside the phase (manifest sequencing).** D-020 requires F1'/F2' regenerated on the
X08-excluded base and that is R-Phase 7 work; `05_results/figures/` holds no post-audit figure. The
manifest is therefore cut now over what exists, every entry carries a `phase` column, **`verify.py` fails
closed on any artifact present in the tree but absent from the manifest**, and the manifest is **re-cut at
the end of R-Phase 7** — written into R-Phase 7's task list in the same session that cuts the first one.
Pulling figure regeneration forward is rejected: F1'/F2' depend on typesetting decisions R-Phase 7 owns,
and building them twice is the waste C1 exists to prevent.

- **Status:** section 0 complete; build in progress.

## THE C01 ATTRIBUTION, RE-MEASURED — branch **W** with a partial **W1**. The gap it closes is a provenance gap; the gap it OPENS is in EXP-017's prose.

Author chose option (2) (section 7 of the prespecification). Design fixed in **amendment 2** before the
script was written; the mechanism arm fixed in **amendment 3** before it ran.

**Script:** `03_code/src/conformal/2026-09-04-c01-attribution.py`. **Outputs:**
`05_results/tables/2026-09-04-c01-attribution.csv` (primary) and `-gfixed.csv` (mechanism check).

**Design, and why it is stronger than re-running the retired path.** One fact measured on the archived
code first: **C01 never touched split-CP or CQR** — `run_corrected.py` takes the order statistic directly
for both (`np.sort(resid)[cq_idx(n,a)-1]`) and only the adaptive stream converts the rank to a fraction
and calls `np.quantile(pool, lv, method="higher")`, which returns the **(k+1)-th** for k < m. So C01 is an
**ACI/ACQR-only** effect, and split-CP and CQR are a negative control the design gets for free (B7).
The two arms are produced by **scoping the archived rule over `core.conformal_quantile` for the duration
of the adaptive call only** — so they share the stream, the release queue, the projection, the score
function and the metrics, and differ in exactly one line. A reimplemented legacy stream could drift from
the real one and would make the delta unattributable. One RandomForest and one HistGBR pair per facility,
**shared by both arms**; gamma held at the corrected arm's value in both (B6), with the gamma the legacy
rule would have selected recorded and used for nothing.

**The gate passed on all 21 facilities before any legacy number was read**, and the **negative control is
exact**: split-CP and CQR differ across arms by **0.0** on PICP, MPIW and Winkler. The scope did not leak.

**The result, on the published base (Belgrade, v2, t+15, 0.90, n = 21):**

| arm | method | PICP corrected | PICP legacy | mean ΔPICP | MPIW | Winkler | legacy ≥ corrected |
|---|---|---|---|---|---|---|---|
| **calibrated gamma (PRIMARY)** | ACI | 0.89125 | 0.89167 | **+0.00042** | **+0.34%** | +0.09% | **21 of 21** |
| **calibrated gamma (PRIMARY)** | ACQR | 0.89402 | 0.89430 | **+0.00028** | **+0.42%** | +0.11% | **21 of 21** |
| fixed gamma = 0.05 (mechanism) | ACI | 0.88525 | 0.88581 | +0.00056 | +0.72% | +0.16% | 21 of 21 |
| fixed gamma = 0.05 (mechanism) | ACQR | 0.88632 | 0.88661 | +0.00028 | +0.81% | +0.42% | 20 of 21 |

The retired rule **over-covers with wider intervals**, unanimously — the same **direction** the archived
prose reports. The **magnitude is another matter**: the archived attribution says ΔPICP **−0.0129** and
MPIW **−15.4%**; measured here it is ΔPICP **−0.0004** and MPIW **−0.34%**, a factor of roughly **40**.

**An unplanned coherence check that validates the harness (B8).** The mechanism arm's *corrected* values
reproduce **T6's existing gamma row to 4 dp** — Belgrade ACI **0.8852 → 0.8913** and ACQR
**0.8863 → 0.8940** — from a completely separate script and code path. Two independently written scripts
agreeing is stronger evidence than either alone, and it means the scoped-patch harness reproduces the
published protocol exactly.

**Branch W1 fires partially, and it does not rescue the archived magnitude.** Amendment 3 predicted the
retired fixed step size as the obvious candidate: a larger gamma drives wider alpha excursions, so the
cost of the ±1 rank should grow. It does — the effect **roughly doubles**, +0.34% → +0.72% (ACI) and
+0.42% → +0.81% (ACQR), in the predicted direction. **A doubling does not explain a factor of 40.**

**Therefore, and this is recorded rather than left implied: EXP-017's prose claim that "the entire shift
is the C01 fix" is not supported by anything now measurable.** EXP-017's headline Belgrade t+15 ACI shift
was MPIW **17.6 → 14.7 (−16.5%)**; C01 alone moves MPIW by **under 1% in either gamma regime**. The
remainder must lie in the other changes that landed in the same rerun (the v1→v2 features, C02's
projection, C06/C07's feedback path, and the gamma regime itself). This moves **no published number** —
the archived triple was already unprintable and is on the never-quote list — but it retires a sentence in
the experiment log, and it is the third time in this project that a striking archived figure has not
survived being opened (B14, B18, and now this).

**What T6 gets.** The C01 row can now be printed, with **traceable current figures on the published base**
and a provenance column naming this CSV: *taking the (k+1)-th order statistic instead of the k-th widens
adaptive intervals by 0.3–0.4% and lifts coverage by 0.0004, unanimously across 21 facilities, under the
published protocol; roughly double that at the retired fixed step size.* It is a **small** row, and it is
honest that it is small. The archived −15.4% is not quoted, beside it or anywhere (B17).

- **Lesson recorded: A17** (the freeze gate cannot see a file that moved) and **B25** (an attribution
  recorded only in prose, on an unrecorded population, is not a finding — it is a claim).
- **Status:** C01 closed. Next in R-Phase 6: the safe runner, then the manifest and `verify.py`.

## THE PACKAGE REBUILD — R01–R05, X02, X03. Every artifact built, both manifests verifying.

**Lock file (R01).** `03_code/2026-09-04-requirements.lock.txt`, generated by
`03_code/2026-09-04-build-lockfile.py` **from the running interpreter that produced the numbers**, not
retyped from `requirements.txt`. 13 exact `==` pins, each with a sha256 — taken from the wheel cache the
restore script already verified, or from the PyPI JSON API for the base-image packages, with every row
saying which. `statsmodels` is **out** (no live script imports it); `ngboost` is **in** (it was missing
entirely); `mapie` is pinned at **1.5.0**, correcting the shipped README's `1.4.1`. The recorded host
(`05_results/tables/2026-09-04-environment-recorded.csv`) also captures a fact the Dockerfile has to
respect: **two different bundled OpenBLAS builds load at once** (numpy's 0.3.29, scipy's 0.3.28, plus
libgomp for scikit-learn), so the image installs from the lock's wheels and pins **no system BLAS** —
forcing a single one would be a different numerical environment from the one the numbers come from.

**Runner (R02, X02).** `run_all.sh`: `set -euo pipefail`, **bounded** retries (`MAX_ITERS`, default 200)
in place of the old unbounded `until … | grep -q; do :; done`, per-step logs that **stream as the step
runs**, `--list` / `--from` / `--only` / `--smoke`, and 19 steps with **every** one wired in — including
the base-learner robustness step the old runner never called while its README claimed "every table and
figure". Four negative controls, all passing: a single-shot step whose command fails **exits 1**; a
resumable step whose command fails **stops on iteration 1, not after 200**; a resumable step that exits 0
but prints neither `ALL DONE` nor `REMAINING` **fails rather than looping**; and a step whose outputs
already exist **completes in one iteration**. *(The streaming-log fix came from running it: an external
timeout during a long step left the log EMPTY, because the first version captured output in a command
substitution and wrote it only on completion. A log you cannot read while the step runs is not a log.)*

**Manifest and `verify.py` (R03).** `00_admin/2026-09-04-shipped-outputs/MANIFEST-outputs.csv`, **225
entries**, and `03_code/verify.py`, which checks in three phases: **A** every input, script, reference
output and packaging document still hashes to the manifest; **B** every freshly generated table is
compared **cell by cell** against the shipped reference under the prespecified tolerance table
(PICP and counts exact, widths 1e-12, CI bounds and p-values 1e-9, figures never hashed); **C** it
**fails closed** — an artifact present in the tree but absent from the manifest is a failure. Four
negative controls, all passing: a Winkler cell perturbed by **1e-9** (tight tolerance 1e-12) is caught; a
PICP cell perturbed by 1e-9 is caught by the *exact* class; an unlisted file is caught by phase C; an
edited `core.py` is caught by phase A. The lock file, the runner and `verify.py` itself are all hashed.

**The package (R04, R05, X03).** `06_manuscript/CTR/replication/2026-09-04-parking-conformal-reliability.zip`,
9.4 MB, built by `03_code/2026-09-04-build-package.py`. It ships `core.py` and the corrected tree, the
**v2** tables only (the v1 leaky tables are deliberately not shipped), a **populated** `EXPERIMENTS_LOG.md`
and all seven prespecifications, `05_results/reference/` (114 tables — the outputs we obtained) with an
empty `05_results/tables/` for the replicator's run, `CITATION.cff`, a generated data dictionary, the
lock/env/Dockerfile, and `BUILD-INFO.txt`. **The package cuts and verifies its own manifest from the
staged tree** (222 entries) — a manifest carrying repository paths would not match the package layout,
and one that does not match the tree it ships with is worse than none.

**The structural fix, and it is the one that matters most.** `REPLICATION.md`'s verification targets are
**read from the CSVs at build time**; nobody types a number into that file again. The previous version
shipped hand-copied targets that the analysis had superseded months earlier — a replicator following it
today would fail **every one**. The generated file now carries the two-level table, and derived checks
computed from **unrounded** sources: the Belgrade dispersion spine **7.76x** (0.041135 / 0.005302 — note
that T3's 4-dp columns round to 7.75x, so the generator reads
`2026-09-04-x08-core-headline-excl.csv` instead, because a package quoting a different figure from the
manuscript is exactly the defect this rebuild exists to remove), Birmingham **3.32x**, the worst cell
**0.5160 vs 0.8421** with **12 of 105**, M02 **0.7733 -> 0.8921 / -9.93%** and
**0.3727 -> 0.9011 / -57.05%**, the new C01 figures, and the measured determinism floor.

**Licences (R05/X03), and the finding that made it cheap.** The 2026-08-04 package's `LICENSE` and
`README` **already stated plan B correctly** — Belgrade CC0, Birmingham-derived CC BY 4.0 with
attribution. The three-way conflict was only in `USER_ACTIONS.md` step 2 ("License: CC0, the platform
default") and the manuscript's Replication section. The new `USER_ACTIONS.md` says the deposit is
**HELD**, gives the reason in one paragraph (the platform default would relicense files whose source
licence requires attribution and which we cannot waive), and offers the two acceptable forms (file-level
licences, or two components). The manuscript sentence is an **R-Phase 7** edit and is listed there.
`REPLICATION.md` no longer claims the package is deposited. **The deposit stays halted (D-015 #2).**

**State gate after all of it: 50 / 48 / 129-of-130, zero failures**, the 129 being the recorded move of
`verify_results.py` (see `00_admin/2026-09-02-preaudit-freeze/2026-09-04-FREEZE-DELTAS.md`, A17).

## THE CLEAN-ROOM RUN — **BRANCH R FIRED.** NGBoost is not reproducible through its own `random_state`, and M02 is an NGBoost claim.

The from-scratch run is executed inside `~/cleanroom`, which holds the **unzipped shipped package** rather
than a copy of the repository — the package is what a replicator receives, so it is what the gate must
run. Progress at the point this was written: `core` complete, `e3` complete for Belgrade (both arms),
Birmingham in progress.

**What reproduces exactly.** Both cities' core tables — split-CP, CQR, ACI, ACQR at four levels and three
horizons, with the B = 10,000 block-bootstrap CIs — are **identical within tolerance**, as are the
base-model MAE/RMSE tables. On the E3 table, **EnbPI, AgACI-style and ACI-crosscheck reproduce exactly**,
across both arms and all 24 Belgrade facilities.

**What does not.** **Every** differing cell is `NGBoost` or `NGBoost-conformal`: 35 of 164 rows, per-facility
|ΔPICP| typically **0.001-0.005**, worst **0.0788** at facility 8 — the dead sensor, which enters no
reported number. Aggregated over the file's 22 non-degenerate facilities the drift is **0.0001** (NGBoost
mean PICP 0.7758 -> 0.7757) and **0.0006** (NGBoost-conformal 0.8958 -> 0.8952), with mean Winkler moving
by about 0.1%.

**Diagnosed, not guessed.** Two consecutive `NGBRegressor(..., random_state=42)` fits **in one process, on
identical data**, differ by up to **2.63 cars in the predicted mean** and **0.39 in the predicted scale**.
Seeding the **global numpy RNG** immediately before each fit makes two fits **bit-identical**
(max |Δ| = 0.000e+00 on both `loc` and `scale`), and different from an unseeded first fit. So in
**ngboost 0.5.11**, `random_state` does not fully determine the fit: the estimator consumes the global
numpy RNG.

**The consequence, and it is worse than a tolerance question.** Every result-generating script in this
project is **resumable by design** (A1) — it processes to a `--budget` and exits, so which facilities are
fitted in which process is an accident of timing. Combined with an estimator that reads the global RNG,
**the NGBoost numbers depend on where the resume boundaries happened to fall.** The archived values are
one draw; the clean-room values are another. Neither is more correct than the other, which is precisely
why this cannot be waved through.

**M02 is an NGBoost claim**: Belgrade **0.7733 -> 0.8921** with Winkler **-9.93%**, Birmingham
**0.3727 -> 0.9011** with **-57.05%**. The measured drift puts the instability in the **third to fourth
decimal**, so **the claim, its direction and its magnitude are unaffected** — a conformalized NGBoost
still goes from badly under-covering to near-nominal, and the Winkler improvement is still tens of
percent. What is affected is the **exact 4-dp figures**, which the project's own rule requires to trace
to a CSV and which a replicator is told to expect.

**The prespecification's branch R fired, and it is being followed rather than worked around.** Section 6
said: *"a PICP disagreement is not noise: it is a version, data or code difference. Stop, attribute it,
and report it. Do not adjust the tolerance."* It is attributed (the estimator's RNG), it is reported here,
**the tolerance is not touched**, and **no logged number has been regenerated.** Widening the tolerance
for this one estimator would have been the packaging form of changing the criterion after seeing the
result, and it was available and declined.

**The fix is one line and it is the author's to authorise, because it moves published numbers.**
`np.random.seed(SEED)` immediately before each NGBoost fit in `2026-09-03-e3-baselines.py` makes the arm
deterministic forever. Applying it regenerates the NGBoost rows and shifts M02's published figures in the
third or fourth decimal. Options and the recommendation are in the record; nothing is changed until the
author answers.

**A note on what this says about the paper rather than the package.** This is an evaluation-protocol
defect that moves a reported number — the same species as the eight rows already in T6, found by building
a clean room rather than by reading code. If the author authorises the fix, it is a candidate ninth row
(D-020 would have to be reopened, so more likely one sentence in the reproducibility paragraph); if not,
it is a limitation that must be stated. It should not be silent either way.

**Also forced by the run: D-022** — the package ships the v1 feature tables, labelled, because the
`A12_v1_paired` arm reads them and it is row 1 of T6; withholding them made a reported number
unverifiable. And **C11** — a runner is only verified by a from-scratch run, and what it omits is an ARM,
not a script: four reported configurations here are produced by non-default flags, two of them
`required=True`, so the runner would have crashed on reaching them.

- **Lessons recorded: A18** (a resumable runner plus an estimator that reads the global RNG makes results
  depend on where the resume boundaries fell), **C11** (arms, not scripts), **C12** (the clean room's job
  is to fail). **Status: R-Phase 6 artifacts COMPLETE; the clean-room run is partly executed and ONE
  DECISION IS OPEN — the NGBoost seeding question, record section 7.**

## CLOSING NOTE, revision 43 — D-023 promotes (C), and what the next experiment must not do

Recorded here because the next entry in this log will be (C)'s, and the constraint below is the one that
decides whether it is publishable.

**θ MUST NOT COME FROM EXP-031's LEVEL SWEEP.** The sweep located a useful regime at **0.90-0.98x
capacity** — 17 of 20 facilities withdrawing under the interval policy against the point policy's 11, six
the point policy never withdraws, median lead 7 steps. That is corroboration and it is valuable. It is
**not** a source for the threshold: selecting θ because it is where we found the effect is tuning on the
outcome, it is the forbidden repair, and it is the first thing a referee would attack in a paper whose
whole contribution is that evaluation choices move reported numbers. θ comes from the parking-management
literature's occupancy-target conventions, or from a rule stated on the inputs and shown insensitive to
its value (B16). **If no defensible anchor exists, (C) does not run.**

**What is already measured and does not need re-establishing:** the outcome event occurs on **20.8% of
healthy weekend facility-slots across 12 facilities** (B20 satisfied on the population that will be
scored); the two policies **genuinely diverge below capacity** (B23's killer does not apply there); the
record exhibits the band (B24). No new data, no third city, no refit — the panel machinery, the demand
model, the >= 20 seeds and the training-only capacity proxy all exist from EXP-029 and EXP-031.

**The expected outcome is a FRONTIER, not a win** — fewer bad assignments bought with materially more
abstention (+25.2 pp against +2.0 at 0.98x cap on the un-injected comparison). That is still an
operational demonstration, and it is written as a trade. A null is a legitimate outcome. Both branches go
in the prespecification before anything runs, per the pattern that has now worked eight times.

---

### EXP-033 — 2026-09-05 — The NGBoost seeding fix and the E3 regeneration. **The defect is closed, the arm is deterministic across resume boundaries, and M02's published figures move in the third to fourth decimal — except one derived percentage, which moves by 0.17 pp and is reported as such.**

- **Prespecified before the fix was applied:** `04_experiments/2026-09-05-ngboost-seeding-PRESPECIFICATION.md`
  (eighth prespecification). Authority: the author's answer of **option 1** to revision-43 record
  section 7, given 2026-09-05.
- **Scripts:** `03_code/tests/2026-09-05-ngboost-determinism-probe.py`,
  `03_code/tests/2026-09-05-agaci-x08-amplification-probe.py`,
  `03_code/tests/2026-09-05-agaci-x08-bistability-probe.py`,
  `03_code/src/conformal/2026-09-05-ngboost-reseed-before-after.py`, and the one-line edit to
  `03_code/src/conformal/2026-09-03-e3-baselines.py`.
- **State before anything was touched:** gate **50 / 48 / 129-of-130**, zero failures; `verify.py` PASS
  at 225 entries; the five affected tables hashing **exactly** to their manifest entries (the B17 base
  check); and the X08 negative control at **688 checks, 0 failed**, of which the E3 leg was **82**.

## SECTION 0 — A18 RE-MEASURED, AND THE ARM THAT MATTERS IS NEW

Revision 43 measured that two `NGBRegressor(random_state=42)` fits differ. That is not A18's claim.
A18's claim is that **the archived numbers depend on where the resume boundaries fell**, and that was
inferred rather than measured. It is now measured directly, on Belgrade facility 2's real training data
(n_train = 2069, p = 15), predictions compared over 1,015 test rows:

| arm | max abs delta, predicted `loc` | max abs delta, predicted `scale` |
|---|---|---|
| **A** two fits, one process, identical data, no fix | **1.290 cars** | 0.670 |
| **B** the same, `np.random.seed(42)` immediately before each fit | **0.000000** | **0.000000** |
| **C** a fit after a *different amount of global-RNG consumption* — a different resume boundary — no fix | **1.895 cars** | 0.706 |
| **C** the same, with the fix | **0.000000** | **0.000000** |

Changing **only the process history**, with the data, the estimator and `random_state` all identical,
moves the predicted mean by **1.9 cars**. That is the defect, stated as the thing it actually is.

## THE FIX

`np.random.seed(SEED)` as the first statement of `fit_ngboost`, **inside** the function so it cannot be
separated from the fit it protects. Nothing else changed: no hyperparameter, no feature set, no split, no
gamma rule, no exclusion rule, no facility set, and `core.py` and both test suites untouched. A per-unit
seed (`SEED + facility_id`) was considered and rejected in the prespecification, before any output
existed: the facilities carry different data, so a shared stream already produces different fits, and a
new convention would have to be documented and defended for no measured gain.

## THE THREE CONTROLS, AND ONE OF THEM COULD HAVE REVERTED THE FIX

**4.3 — the leak control. 1,092 checks, 0 failed.** Every `EnbPI`, `AgACI-style` and `ACI-crosscheck`
row in both cities, plus `n_test` and `cal_score_max`, reproduces its superseded value within the
R-Phase 6 tolerance table (PICP and counts **exact**, widths **1e-12** relative, CI bounds **1e-9**).
The prediction stated in advance — that nothing else in the path reads the global RNG, because
`core.moving_block_bootstrap_ci` uses `np.random.default_rng(seed)` and every sklearn/MAPIE estimator
takes an integer `random_state` — is therefore confirmed empirically and not merely argued.

**4.4 — the resume-boundary control, on the real pipeline. PASS, bit-identical.** Three Belgrade
facilities (2, 3, 4) were re-run from a wiped state with `--budget 1`, forcing **one facility per
process** — a deliberately different resume boundary from the one that produced the regenerated file.
Every NGBoost and NGBoost-conformal cell matched to **0.000e+00** on PICP, MPIW, Winkler and both CI
bounds. This is the check that actually closes A18, because it tests the resumability contract rather
than simulating it. A second, independent instance of the same control appeared by accident earlier in
the session: facility 8 was re-run in a separate process during the AgACI diagnosis below, and its
NGBoost MPIW came back identical to nine decimals (10.297318683 and 16.340351354) while its **AgACI**
value did not.

**A probe with its own negative control.** The determinism probe's success criterion required arms A and
C to be **non-zero** as well as B and C-seeded to be zero — a probe that could only pass would have shown
nothing (B11).

## AN UNPLANNED FINDING, AND IT QUALIFIES A CLAIM IN EXP-032

One non-NGBoost cell moved on the first regeneration: **AgACI-style's MPIW at Belgrade facility 8**, the
X08 dead sensor, by **6.9e-5** absolute (2.2e-6 relative) — outside the 1e-12 class. It was diagnosed
rather than tolerated, and the reseed is **exonerated by construction and by measurement**:

1. `agaci_ewa` runs **strictly before** `fit_ngboost` in the same facility iteration, so a seed set
   inside the fit cannot reach it.
2. `03_code/tests/2026-09-05-agaci-x08-bistability-probe.py` reproduces the whole
   RF -> residuals -> `agaci_ewa` path with `fit_ngboost` **never called**, so the reseed never executes
   in that process — and **both** values appear across processes. Three consecutive runs returned
   30.905034097; a separately written probe returned 30.905102818; a second production re-run of
   facility 8 returned **30.905034097 again**. The quantity is **bistable across processes and stable
   within one**.
3. The mechanism is measured, not assumed: facility 8's series takes two exact values, and the probe
   counts **78 exact ties** between the outcome and an expert's interval bound across the seven ACI
   experts the EWA aggregates. A coverage indicator sitting exactly *on* a bound flips under a 1e-14
   perturbation of the forecast, which changes the ACI alpha trajectory from that step onward. Smooth
   perturbation tests confirm the aggregate is otherwise well behaved: scaling `yhat` by 1e-14 to 1e-10
   moves MPIW proportionally (7e-14 to 7e-10), so this is a **tie flip**, not general instability.

**What this qualifies.** EXP-032 recorded that "EnbPI, AgACI-style and ACI-crosscheck reproduce exactly"
in the clean room. On the evidence here that is true of **23 of 24** Belgrade facilities and is **not**
guaranteed at facility 8. It changes **no reported number** — facility 8 is excluded from every published
E3 figure by D-018, and the difference is invisible at the 4 dp the summaries carry (6.9e-5 spread over
22 facilities is 3e-6) — but a clean-room run that happens to draw the other value will flag that cell,
and a replicator must not be told it is a defect in their environment. Recorded as lesson **B26**.

## THE RESULT — BRANCH **N1**, as prespecified

`05_results/tables/2026-09-05-ngboost-reseed-before-after.csv`, 104 rows, each naming its facility, its
method and whether it is in the published base (B25).

**M02 on the published (X08-excluded) base:**

| city | n | before | after | Winkler improvement before -> after |
|---|---|---|---|---|
| Belgrade | 21 | 0.7733 -> 0.8921 | **0.7736 -> 0.8917** | 9.93% -> **9.76%** |
| Birmingham | 28 | 0.3727 -> 0.9011 | **0.3722 -> 0.9014** | 57.05% -> **57.00%** |

Every PICP moves by at most **0.0006**, against branch N1's prespecified 0.002. The underlying Winkler
values move by **-0.31%, -0.12%, +0.15%, +0.26%** relative, against N1's 0.5%. **Branch N1 fires.**

**One thing is said plainly rather than filed under "third to fourth decimal".** The Belgrade Winkler
*improvement* is a ratio of two numbers that both moved, so it moves more than either: **9.93% -> 9.76%,
a change of 0.17 percentage points** in a figure the manuscript quotes as "9.9%". At one decimal place it
is unchanged; at two it is not. The manuscript quotes 9.9%, so no rounded manuscript figure changes — but
the ESM, T2 and the replication targets carry the fuller precision and they do change, and calling that
invisible would be false.

**Nothing else moved.** The paper's spine is untouched and was re-read from the regenerated artifacts
rather than assumed: Belgrade split-CP/ACQR dispersion **7.76x** (0.041135 / 0.005302), Birmingham
**3.32x**, the worst cell **0.5160 vs 0.8421** with **12 of 105**, and every population-level TOST/SAFE
verdict in `2026-09-04-phase4-population.csv`. In that file the only rows that changed are the two
**exploratory** NGBoost rows; all eight `P-primary` rows are identical.

## THE STALE-SUMMARY PROBLEM, AND THE TAUTOLOGY IT CREATES

`05_results/tables/2026-09-03-e3-summary.csv` has **no generating script anywhere in the tree**. Measured
before the run: its sha256 is `6ec70341…`, **byte-identical** to `2026-09-04-x08-e3-summary-control.csv`,
which `2026-09-04-x08-reaggregate.py --filter off` produces. So the archived ad-hoc aggregation and the
re-aggregator's local aggregation agree exactly, and the archived file could be regenerated from the
control output without patching anything into agreement. That is what was done (prespecification 3.4).

**Stated rather than buried:** after that substitution, the E3 leg of
`03_code/tests/2026-09-04-x08-control-check.py` compares a file against its own source and is a
**tautology**. Its evidential value is the **pre-fix** run recorded above — 688 checks, 0 failed, E3 leg
82 — which is the proof that the re-aggregator reproduces the original aggregation. The test was **not**
edited, **no tolerance was touched**, and the five non-E3 pairs remain live checks. The two alternatives
were both worse: pointing the test at a new filename hides the tautology, and relaxing its 5e-5 is the
forbidden repair.

## DOWNSTREAM, MANIFEST AND PACKAGE

Regenerated in dependency order: `x08-reaggregate --filter off` then `--filter on` (only the E3 summary
changed; the other five control files are **byte-identical**, which is itself a control),
`phase4-inference --filter off/on`, `x08-before-after`, `x08-orthogonal-excess`, `display-items`.
Seven reference copies were refreshed, each recorded with the sha256 on both sides in
`00_admin/2026-09-05-reseed-reference-refresh.csv`. The manifest was re-cut (**233 entries**, up from
225: four new scripts and four new tables) and `verify.py` **PASSES with zero unlisted artifacts**. The
package was rebuilt as `2026-09-05-parking-conformal-reliability.zip` (13.1 MB, 235 entries, cutting and
verifying its own manifest); the 2026-09-04 zip is **retired** under `replication/_superseded/`, not
repaired in place — a package and its numbers travel together. `REPLICATION.md`'s verification targets
are generated from the CSVs, so they picked up **0.7736 -> 0.8917 / -9.76%** and
**0.3722 -> 0.9014 / -57.00%** with nobody typing a number.

**Gate after all of it: 50 / 48 / 129-of-130, zero failures; `verify.py` 233 entries, PASS.**

- **Lessons recorded: B26** (a coverage indicator sitting exactly on an interval bound makes an adaptive
  stream bistable across processes, and a degenerate series is where that happens) and **C13** (a
  regeneration is only as honest as its reference refresh: `verify.py --build` copies a table into
  `05_results/reference/` **only if it is absent**, so a changed artifact keeps its stale reference and
  the reproduction phase silently compares against the old number).
- **Status:** the NGBoost decision is **CLOSED**. The superseded M02 pair `0.7733 -> 0.8921` and
  **"9.93%"** join the never-quote list. Next: D-019 (C), starting with the literature check for theta.

---

### EXP-034 — 2026-09-05 — D-019 option (C): the relative-threshold allocation demonstration. **Branch F. The paper has an operational demonstration: 96% fewer bad assignments for +313 m of straight-line distance — and the cost is distance, not abstention, which the prespecification got wrong.**

- **Prespecified before any policy was scored:** `04_experiments/2026-09-05-rphase-C-PRESPECIFICATION.md`
  (ninth prespecification), whose section 0 is measured on the inputs only.
- **theta's provenance is EARLIER and separate:** `04_experiments/2026-09-05-theta-LITERATURE-ANCHOR.md`,
  written before the prespecification and before any (C) code existed.
- **Scripts:** `2026-09-05-relative-threshold-allocation.py` (phases `a` / `s0` / `run`),
  `2026-09-05-rel-alloc-summary.py`. **Outputs:** `2026-09-05-rel-alloc-{section0,seeds,summary}.csv`.
- **Authority:** D-023, confirmed by the author 2026-09-05.

## theta CAME FROM THE LITERATURE, AND THE VALUE THE DATA PREFERRED WAS DECLINED

Three sources, 2009-2014, three research traditions, none about our data: **Caicedo (2009, TR-C)** —
deployed PARC systems display "no free spaces" above **90% and 95%** occupancy; **Levy et al. (2013,
Transportmetrica A)** — parking dynamics break down above **92-93%**; **Millard-Ball et al. (2014, TR-A)** —
the probability of finding a space tracks occupancy until **85-90%**, then collapses. Primary
**theta = 0.90**, band **[0.90, 0.95]**, 0.85 as an outside endpoint. **EXP-031's sweep preferred 0.98 and
0.98 was not adopted**; the sweep is recorded as corroboration only. The 85% Shoup / SFpark 60-80% target
was considered and **rejected on construct grounds** — it is a curbside *pricing* target for maintaining
vacancy, and Arnott (2014) and Elíasson et al. (2022) both show the optimum is not a constant. The memo
records the honest weakness too: no purpose-built empirical study of "when is an off-street car park
practically full" was found, so the claim is that theta is anchored in converging practice, not that it is
a measured constant.

## SECTION 0 — ALL THREE KILLERS CHECKED BEFORE THE EXPERIMENT, AND ONE CONSTRAINT IMPOSED

`2026-09-05-rel-alloc-section0.csv`. Base n = 20 (dynamic, coordinate-matched, facility 8 excluded by
`core.low_information_facilities` on both windows).

- **B20 (does the event occur?)** Weekend: **20.75% of facility-slots at theta = 0.90, across 12 of 20
  facilities**; still 10.34% across 6 at 0.95. The dead vignette scored **0 of 3,340**. It independently
  reproduces D-019 #4's recorded 20.8%.
- **B23 (what does the comparator do at the outcome step?)** This is what killed (D'). Here **246
  facility-slots are withdrawn by INTERVAL and offered by POINT** at the primary cell (132-246 across the
  band), so the contrast is **not** zero by construction. `point_only_withdrawn_slots = 0` everywhere,
  which is arithmetic (`U >= yhat`) and is reported as arithmetic.
- **B24 (does the record exhibit the band?)** Yes, on 20.75% of slots — unlike (D'), whose only anomaly
  sat at 167.7% of capacity where the lead is identically zero.
- **The constraint fixed in advance:** the **weekday** window is thin — 3 facilities carry the event at
  0.90 and **1** at 0.95 — so weekend is the primary, weekday is reported with its facility count, and
  **no claim is made from a cell with fewer than 3 facilities carrying the event**. That ruled out weekday
  0.95 before its number existed (B14/B18/B20, the three times an aggregate here turned out to be one
  facility).

**Gates passed before anything was read:** the imported EXP-029 panel reproduces
`2026-09-04-vignette-capacity-proxy.csv` on **21 of 21** facilities for both the capacity proxy and the
selected gamma, so the machinery is the machinery (B9, B8); and POINT-only withdrawals are 0 in all 8
cells.

## THE RESULT — BRANCH **F**, the frontier D-023 predicted

**Primary cell: weekend, theta = 0.90, 20 facilities, 20 paired seeds, identical requests within a seed.**

| policy | bad assignments per 600 requests | mean straight-line distance | extra distance vs POINT |
|---|---|---|---|
| POINT | **27.3** | 1.599 km | — |
| **INTERVAL** | **1.0** | 1.912 km | **+313 m** |
| MARGIN (matched conservatism, the control) | 3.9 | 2.021 km | +422 m |

Paired reduction POINT -> INTERVAL: **0.0438 bad assignments per request**, a **96.2%** relative
reduction, with the sign holding in **20 of 20 seeds** (range 0.0250-0.0600). The distance cost is
positive in **20 of 20 seeds** (range +217 m to +386 m).

**Stable across the whole band, which is what B16 asks for.** On the weekend window the POINT -> INTERVAL
reduction holds at **every** theta and in **20 of 20 seeds** at each: 92.4% at 0.85, 96.2% at 0.90, 78.2%
at 0.925, 72.6% at 0.95. The demonstration does not depend on where in the literature's band theta is put.

**Weekday, reported with its counts and not as a headline:** at theta = 0.90 it is a **null** (0.0002 ->
0.0001 per request, sign holding in 1 of 20 seeds) on a population of **3** facilities; at 0.925 the
reduction is 96.1% and unanimous but still on 3 facilities; at 0.95 **one** facility carries the event and
the prespecification forbids a claim there.

## WHAT THE CONTROL SAYS, AND IT IS NOT THE CONVENIENT ANSWER

At the primary cell **INTERVAL dominates MARGIN**: fewer bad assignments (1.0 vs 3.9) at **less** extra
distance (+313 m vs +422 m), beating it in 18 of 20 seeds. That is the adaptivity claim — the interval
widens where the facility is uncertain, so it withdraws selectively, while a constant margin withdraws
uniformly and pays for it in distance.

**But it is not stable across the band, and that is reported rather than trimmed.** At theta = 0.925 and
0.95 MARGIN makes **fewer** bad assignments than INTERVAL (0.0022 vs 0.0060; 0.0001 vs 0.0036) while
costing far more distance (+575 m and +502 m against INTERVAL's +290 m and +107 m). So against a matched
constant margin the interval policy is **not uniformly better** — the two sit at different points on the
same trade-off, and which is preferable depends on theta and on how a city prices a kilometre against a
driver arriving at a full car park. **Prespecification branch W therefore fires only at the primary cell,
and the sentence the paper may write is the narrower one:** conservatism helps; at the literature's
primary threshold a calibrated interval achieves it more cheaply than a matched constant margin; that
advantage is not stable across [0.90, 0.95].

## THE PRESPECIFICATION WAS WRONG ABOUT THE CURRENCY OF THE COST, AND THIS IS RECORDED, NOT RELABELLED

Section 2 named **abstention** as the cost, following D-023's expectation of "+25.2 pp of abstention
against +2.0". **Measured, the abstention rate is identically 0.0000 for all three policies in all eight
cells.** The mechanism is structural and obvious in hindsight: with 20 candidate facilities and at most a
third of them full, a request that is turned away from its nearest facility is never turned away from the
*system* — it is sent further. **The cost currency is distance, not abstention.** EXP-031's +25.2 pp came
from a design in which a single injected facility was the destination, so withdrawal there meant no
assignment; that number does not transfer to a 20-facility choice set and must not be quoted as this
experiment's cost. Recorded as lesson **B27**.

**The asymmetry that must travel with the headline.** The outcome metric penalises exactly one direction
— sending a driver to a full car park — and never penalises excess caution. The distance column is the
only place the other direction appears. Any sentence quoting the 96% must quote the +313 m beside it, and
the MARGIN control must be in the same table, or the result reads as a victory when it is a **trade**.

## WHAT THIS CHANGES

The paper now **has an operational demonstration**, which D-021 recorded as its largest accepted cost and
D-019's outcome block escalated after (D') died: better-calibrated per-facility intervals produce a
**better decision**, measured on a prespecified outcome, on a threshold taken from the parking-management
literature rather than from our own sweep, with a matched-conservatism control beside it and the cost
stated in the same breath.

**D-020 is NOT reopened here.** Per the prespecification, this goes to the ESM with one main-text
sentence; whether it earns a main-text display item is a separate decision, now that the size is known,
and it requires something to leave. That decision goes to the author with a recommendation in the record.

- **Lesson recorded: B27** (an abstention cost cannot materialise when the choice set is large — check
  what the policy's fallback actually is before naming the currency of the cost).
- **Status:** D-019 (C) **DELIVERED**, branch F. Next: the clean-room run.

---

### EXP-035 — 2026-09-05 — The clean-room run, executed to completion. **It found six defects, none of them visible from reading the code, and it ends at ONE differing cell — at the excluded dead sensor.**

- **Authority:** R-Phase 6, run against the package rebuilt after EXP-033 and EXP-034.
- **What was run:** `~/cleanroom` holds the **unzipped shipped package**, not a copy of the repository.
  Every step of `run_all.sh` was executed from an empty `05_results/tables/`: env, core (both cities), e3
  (both cities, **both arms**), tod, trust, base-learner, orthogonal, folds (three arms), rolling, delay,
  x08 (both filters), inference (both filters), vignette, rphase5, c01 (both gamma modes), relalloc,
  display, spatial, figures, verify.
- **Measured rate:** core ~5 calls, e3 ~40, everything after it ~15. Revision 43's estimate of 2-5
  facility-arms per 172-second call held.

## THE HEADLINE: THE RESEED IS CONFIRMED BY THE ONLY TEST THAT COUNTS

Before the fix, **35 of 164** E3 rows differed and every one was NGBoost. From scratch, in the clean room,
after the fix:

| method | Belgrade (24 facilities) | Birmingham (28 facilities) |
|---|---|---|
| NGBoost | max relative delta **0.000e+00** on PICP, MPIW and Winkler | **0.000e+00** |
| NGBoost-conformal | **0.000e+00** | **0.000e+00** |
| EnbPI / AgACI-style / ACI-crosscheck | PICP exact; widths <= 5.4e-16 relative | PICP exact; widths <= 3.6e-16 |

The arm is now **bit-reproducible from an independent from-scratch run of the shipped package**. That is
the evidence the EXP-033 controls could only approximate.

## SIX DEFECTS, IN THE ORDER THE RUN FOUND THEM

**1. The orthogonal-folds completion check ignored `--arm`.** `2026-09-04-orthogonal-folds-birmingham.py`
honours `--arm` in its work loop but its final REMAINING/ALL DONE check ranged over **all three arms**, so
an invocation with `--arm A_folds` printed `REMAINING: 56` forever once its own arm was complete.
`run_all.sh` resumes a step until it prints ALL DONE, so a replicator's run would have spun this step for
its full `MAX_ITERS` (200 iterations) and then failed. One-line guard added. **Lesson C11's third
instance**, and the first where the omission is inside a script rather than in the runner.

**2 and 3. Two archived inputs that exist in the repository and not in the package.**
`2026-09-04-phase4-inference.py` reads `2026-09-02-corrected-headline-gcal.csv` as its gate and
`2026-09-04-vignette-summary.py` reads `2026-08-04-allocation-vignette-requests.csv`. Both live in
`05_results/tables/` in the **repository**; in the **package** that directory is the replicator's own
empty output directory and our outputs are in `05_results/reference/`. Both steps died with
`FileNotFoundError`. Fixed with a `logged_path()` helper that prefers `tables/` and falls back to
`reference/` -- **never the other way round, and the archived file is never copied INTO `tables/`**,
because pre-seeding a replicator's output directory with our numbers would let a run "reproduce" a file we
handed them. The same helper now routes **all eleven** reads in `2026-09-04-display-items.py`, which has
three more inputs of the same class. **Lesson C14.**

**4. Two single-shot steps refuse to overwrite their own output.**
`2026-09-04-rphase5-esm-capability.py` and `-d05-sweep.py` exit 1 if their output exists. `run_all.sh`
executes single-shot steps on **every** pass, so any interrupted-and-restarted replication -- which the
resumable design positively invites -- fails on a file the replicator's own run wrote. Both now accept
`--overwrite`, which the runner passes; a bare invocation still refuses, which is what protects the
repository's logged artifacts.

**5. The delay-sensitivity step ran ONE city and the WRONG population.** The script takes its city from
the `CITY` **environment variable** (default belgrade), so `2026-09-02-delay-sensitivity-birmingham.csv`
was never produced at all; and it takes `--facilities` (default **10**) while the logged Belgrade table
was cut at **8** facilities and the logged Birmingham table at **10**, so a from-scratch run emitted 210
Belgrade rows against the reference's 168. Both logged populations are now pinned in `run_all.sh`.
Changing the population to the default instead would have moved a logged figure -- EXP-018's headline
becomes **2.68** coverage points at 10 facilities against the logged **2.88** -- for no scientific reason
(**B25**). **C11's fourth instance**, and the second in this session where the omission is an *arm*.

**6. THE ONE THAT REACHED A COMPUTED NUMBER: the facility-clustered bootstrap depended on ROW ORDER.**
`2026-09-04-phase4-inference.py` resamples the per-facility coverage vector **in file order**. A
from-scratch run writes the E3 arms in a different order from the archived file (`A3_v2_daychunk` first
rather than `A12_v1_paired` first), and the four **exploratory** E3 rows' bootstrap bounds moved by up to
**1.1e-3 relative** -- while `mean_PICP`, `sd_PICP` and every t-based bound were **bit-identical**, which
is the signature of an order dependence and not of a numerical one. Both frames are now sorted by
`facility_id` before anything is resampled, and the bounds are a function of the data alone. EXP-032 found
a row order breaking a **comparison**; this one reached a **published quantity class**. **Lesson C15.**

## TWO REPOSITORY-SIDE CONSEQUENCES, BOTH EXECUTED

**The A12 arm was regenerated** in both cities (22 + 28 facilities). The archived A12 rows predate the
`status` column, so they carry `NaN` where a fresh run writes `ok`, and `verify.py` reported **100
differing cells** in a column that is metadata. Regeneration reproduced every numeric column of the
superseded values -- **PICP bit-identical, widths to 6.4e-16 relative** -- so it changed no number and
removed a permanent false failure from the shipped package. Recorded rather than left implied: this is a
schema drift, not a numerical one, and it was only visible because a from-scratch run writes every column.

**`phase4-inference` and the downstream chain were re-run** on the sorted code. The paper's spine is
unmoved and was re-read from the regenerated artifacts rather than assumed: Belgrade split-CP/ACQR
dispersion **7.7589x** (published 7.76x), Birmingham **3.3175x** (3.32x), `mean_PICP` and `sd_PICP`
bit-identical in all sixteen population rows.

## WHERE THE GATE ENDS, AND WHAT IS LEFT OPEN

Re-run inside a **freshly unzipped copy of the rebuilt package** carrying the completed run's outputs:
**303 checks, 58 archived artifacts correctly recognised, and exactly THREE failures -- all of them the
same single cell.**

> `2026-09-02-delay-sensitivity-belgrade.csv`, **facility 8**, ACI, gamma = 0.01, h = 3:
> PICP 0.903448 vs 0.904433 (1.1e-3 relative), with the corresponding MPIW and Winkler.
> Birmingham's 210 rows are **bit-exact**, and so are the other 167 Belgrade rows.

It is the **X08 dead sensor** and the mechanism is the one measured in EXP-033: on a series taking two
exact values there are exact ties between the outcome and an interval bound, so a 1e-14 perturbation flips
an indicator and the adaptive stream diverges from that step. **Third appearance of facility 8 as the only
unstable unit in this project** (B14, B18, B26).

**The tolerance was NOT relaxed**, and the population was NOT changed to make the gate pass. What the fix
would be is a question about a logged number, so it goes to the author with the number measured:

| | logged population (8 facilities, **including** X08) | D-018 applied (7 facilities) |
|---|---|---|
| gamma 0.05 at h = 6 | 0.8718 | 0.8690 |
| gamma 0.005 at h = 6 | **0.9006** | **0.8962** |
| cost of gamma 0.05 | **2.88** coverage points | **2.72** |

So applying D-018 here — which is the standing rule, and this table predates it — costs 0.16 coverage
points **and retires the clause "restores 0.90 at every horizon"**: on the excluded base gamma = 0.005
reaches 0.894-0.896, not 0.900. That is a real weakening of a live sentence in the R-Phase 3 gate
narrative and it is the author's call. **Recorded as D-024, open.**

## BRANCH S, IMPLEMENTED

`05_results/reference/` holds 121 tables and a complete run regenerates 63. The other **58** are archived:
pre-rejection (2026-06-21/25) and pre-audit (2026-08-04/05) artifacts, diagnostics that are deliberately
not runner steps, this machine's recorded environment, and three files produced ad hoc in earlier stages
that have **no writer anywhere in the tree**. `verify.py` reported every one as a failure, so a replicator
saw 58 non-defects. The R-Phase 6 prespecification had already decided this class (branch S: *list it with
provenance = unreproducible and a stated reason*), and it is now implemented:
`00_admin/2026-09-05-archived-artifacts.csv` carries one reason per file and was **generated from the
complete clean-room run**, not typed, so it cannot quietly acquire a file that should have been
regenerated. The guards that keep it honest: an archived artifact that IS regenerated is compared
normally, and a non-archived reference that is missing is still a failure. **The list had to be added to
the package staging as well** — found by running `verify.py` inside a freshly unzipped package rather than
in the repository, which is the same lesson one turn further out.

## A LIMIT STATED PLAINLY

The clean room is "fresh tree, fresh output directory, lock-pinned interpreter", **not** "fresh container":
`docker` and `podman` are both absent from this machine, so **the Dockerfile remains UNTESTED** and this
must not be described as a container-verified clean room. Building the image once is an author action.
Two of the six defects were fixed **in place in both trees** while the run was in progress, with the
sha256 recorded identical on both sides; the next clean-room run starts from the rebuilt package and
exercises them from scratch. That run is the confirmation, and it is the first item of the next session.

- **Lessons recorded: C14** (an archived input that lives in `tables/` in the repository is missing in the
  package, and the fallback must never be inverted) and **C15** (a bootstrap that resamples in file order
  makes a published bound depend on row order).
- **Status:** R-Phase 6's clean-room gate is **executed and down to one documented cell**. Outstanding:
  **D-024**, the Dockerfile, and a confirmation run from the rebuilt package.

---

### EXP-036 — 2026-09-05 — The confirmation clean-room run, and closing the gate. **It found a seventh defect that fails on every replicator's FIRST run, a second unstable cell, and a mechanism that is worse than "bistable" — the cell is nondeterministic run to run and thread pinning does not fix it.**

- **Authority:** revision-44 record section 11 item 1; then the author's three decisions of 2026-09-05 —
  **D-024 option 1**, the **branch-S registry** for the measurably-unstable cell, and **removing the
  append** for defect 7.
- **Prespecified before any file was changed:** `04_experiments/2026-09-05-revision45-gate-closure-PRESPECIFICATION.md`
  (tenth prespecification), section 0 measured on the inputs only.
- **What was run:** `~/cleanroom`, a fresh unzip of `2026-09-05-parking-conformal-reliability.zip`, every
  step of `run_all.sh` from an empty `05_results/tables/`. ~60 calls (core 4, e3 ~30, the rest ~15) —
  revision 44's measured rate held.

## THE HEADLINE: EVERY PUBLISHED NUMBER REPRODUCES FROM THE REBUILT PACKAGE

Read from the run's own artifacts, not assumed:

| claim | published | this run |
|---|---|---|
| M02 Belgrade | 0.7736 -> 0.8917, Winkler 9.76% | **exact, 9.76%** |
| M02 Birmingham | 0.3722 -> 0.9014, 57.00% | **exact, 57.00%** |
| NGBoost / NGBoost-conformal | bit-reproducible after the reseed | **0.000e+00** on PICP, MPIW, Winkler, both cities, all 52 facilities |
| dispersion spine | 7.76x / 3.32x | **7.7589x / 3.3175x** |
| two-level inference | 7 of 8 EXACT, 8 of 8 SAFE | **7 of 8** (Birmingham split-CP, upper side) **/ 8 of 8** |
| worst facility, Belgrade | 0.787 vs 0.879 | **0.787192 vs 0.878818** |
| Table 4 | worst 0.516 vs 0.842; 12 of 105 below 0.80 | **0.5160 vs 0.8421; 12 and 0 of 105** |
| (C) weekend theta=0.90 | 27.3 -> 1.0 vs MARGIN 3.9, +313 m | **27.3 / 1.05 / 3.9, 96.2%, 20/20 seeds, +313 m / +422 m** |
| (C) abstention | identically zero (B27) | **0.0000 in all eight cells** |
| (C) across the band | 92.4 / 96.2 / 78.2 / 72.6% | **exact at all four thetas** |

Core reproduced at **2.0e-15** over 2,340 rows. E3 came out at **164/164** and **196/196** rows — the
reference row counts exactly, which is C11's check — with **PICP exact on every method in both cities**.
All six revision-44 fixes were exercised from scratch, including the Birmingham delay table, which exists
for the first time (210 rows at 10 facilities; Belgrade 168 at 8). 63 of 121 reference tables regenerated
and 58 archived: branch S behaved exactly as designed.

## DEFECT 7 — IT FAILS ON EVERY REPLICATOR'S FIRST RUN, AND THE WAY WE VERIFIED HID IT

`spatial_analysis.py` and `spatial_mantel.py` each do `open(EXPERIMENTS_LOG.md, "a")` and append a
`datetime.now()`-stamped `EXP-006` / `EXP-006b` block. `verify.py` lists that tracker in `SCAN_FILES` as
an **exact_hash** document. So the `spatial` step mutates a manifest-listed document and the `verify`
step then fails on it — **deterministically, on every run, on every machine, and with a different hash
each day**. Caught here as `A CHANGED 04_experiments/EXPERIMENTS_LOG.md`; the shipped copy was 204,362
bytes against the manifest's 203,116.

**Why EXP-035 did not see it, and this is the transferable part.** That run verified inside a *freshly
unzipped* copy of the package carrying the completed run's `05_results` outputs. The fresh unzip restored
the pristine tracker and erased the evidence. C14 says run the verifier inside the unzipped package rather
than the repository; this is one turn further out — **run it inside the package you actually ran**.
Recorded as **C16**.

**Fixed, and the route matters.** Both scripts are in the **R-Phase 0 freeze**. They were edited in place
first and the freeze gate immediately reported CHANGED; the edit was reverted to the frozen bytes (hashes
re-verified against the manifest) and the fix delivered the prescribed way instead: the frozen originals
were **moved byte-identically** into `03_code/src/spatial/_retired/` and registered in
`2026-09-04-FREEZE-DELTAS.md` with the sha256 on both sides, and dated replacements
`2026-09-05-spatial-{analysis,mantel}.py` — differing **only** by the deletion of the append block — took
their place in `run_all.sh`. `build-package.py` already excludes `_retired/`, so the offending scripts no
longer ship. **Freeze count 129 -> 127**, all three absences registered. Lesson **A19**.

## THE GATE DOES NOT END AT ONE CELL, AND THE MECHANISM IS NOT WHAT D-024 SAID

`verify.py` reported **303 checks, 6 failures**, in three classes: defect 7 above; the delay-sensitivity
cell D-024 predicted; and **a second cell EXP-035 never listed** —
`2026-09-03-e3-belgrade-per-facility.csv`, facility 8, `AgACI-style`, MPIW and Winkler. EXP-035 missed it
because that run happened to draw the reference branch.

**Both cells were re-run in fresh processes rather than diagnosed from the failure text (rule 2).**

| probe | result |
|---|---|
| delay cell, nothing pinned, 3 fresh runs | 0.903448 -> **0.904433** -> 0.903448 — **it flips at fixed settings** |
| delay cell, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, 3 runs | 0.904433, 0.904433, **0.903448** — **pinning does not suppress it** |
| AgACI cell, 4 fresh runs this session | ...103, ...103, then ...034, ...034 |
| AgACI bistability probe, 9 accumulated observations | **6 at 78 ties -> 30.905034097; 3 at 77 ties -> 30.905102818** |

So both cells are **run-to-run nondeterministic in an identical environment**, and because BLAS pinning
does not stop it the driver is **joblib's `n_jobs=-1` forest aggregation**, not BLAS. The probe also
sharpens EXP-033: the width branch is a function of the **tie count itself**, which moves by one (78 vs
77), and **PICP is identical across all nine observations** — which is precisely why PICP can stay gated
as exact while the widths cannot.

**This falsifies A8 as recorded.** A8 says the RandomForest thread nondeterminism is "harmless — fifteen
orders below any reported digit, and PICP is exactly reproducible". True on healthy facilities — measured
again here on 357 delay rows and 360 e3 rows. **False at facility 8**, where the same 1e-14 reaches the
**third decimal of a published PICP**. A8 was measured on healthy units; this is the fifth time an
aggregate here turned out to be one unit (B14, B18, B20, B25, B26). Recorded as **A8 addendum / B28**.

## D-024 EXECUTED — option 1, with a gate that came out stronger than prespecified

Belgrade 8 -> 7 facilities, **168 -> 147 rows**; the 147 retained rows reproduce with **PICP EXACT** and
widths <= 3.6e-16 relative; Birmingham, the negative control, is **PICP exact on all 210 rows** and its
reference is therefore **not** refreshed (C13 refreshes what legitimately changed, and Birmingham did not
— only A8 noise in its last bits). Aggregates land exactly on the prespecified column: **0.8718 ->
0.8690**, **0.9006 -> 0.8962**, cost **2.88 -> 2.72**. The retired clause is retired at every horizon:
gamma = 0.005 gives **0.8944 / 0.8949 / 0.8962**.

**A self-correction worth recording.** The prespecification's gate said the retained rows must be
"bit-identical". That contradicts A8, which has been on file since revision 36: a *refit* cannot be
bit-identical on widths, only on PICP. Evaluated against the **standing** R-Phase 6 tolerance table —
fixed before any clean-room output existed — **zero cells exceed tolerance in either city**. The tolerance
was not moved; the prespecified wording was stricter than the project's own standard and wrong to be, and
it is recorded that way rather than quietly rescored.

## BRANCH S FOR A CELL — and it is not a relaxed tolerance, with controls to prove it

`00_admin/2026-09-05-unstable-cells.csv` registers the two facility-8 `AgACI-style` cells with **both
observed values, the counts (6|3), the observation total (9), the mechanism, and the confirmation that
PICP is identical across every observation**. It is **generated** by
`03_code/2026-09-05-build-unstable-cells.py` from the append-only probe, never typed, so it cannot quietly
acquire a cell that should have been reproducible. `verify.py` reports a registered cell as
**known-unstable** instead of as a failure.

**Four negative controls** (`03_code/tests/2026-09-05-unstable-registry-controls.py`), because a mechanism
one edit away from a forbidden repair needs proof it can still fail (B11) — **all four pass**:

| control | asserted | result |
|---|---|---|
| C1 registered cell at a recorded value | excused | PASS |
| C2 registered cell at a **third** value | **FAILURE** | PASS |
| C3 registered cell's **PICP** (an `exact`-class column) | **FAILURE** | PASS |
| C4 an **unregistered** cell, same file and column | **FAILURE** | PASS |

So the registry pins **values**, not cells; it never excuses an `exact` column; and it is cell-scoped.

- **Lessons recorded: A19** (a frozen file is retired by moving it, never edited in place — check the
  freeze manifest *before* editing, not after the gate turns red), **C16** (verify inside the package you
  actually ran, not a fresh unzip of it), and **B28** (an environment nondeterminism recorded as harmless
  was measured on healthy units only — re-measure it on the degenerate one before trusting the word).
- **Gate after the work:** **50 / 48 / 127-of-130**, zero failures, three registered absences.
- **Status:** D-024 CLOSED. The clean-room gate closes on the repository side. Outstanding: the package
  rebuild and manifest re-cut, a **full** confirmation clean-room run from the newly rebuilt package
  (three code changes have been made since the run above), and the untested Dockerfile.

---

### EXP-036 — ADDENDUM 2026-09-06 (revision 46). **Its regeneration count was contingent on process timing, and this is recorded rather than rescored.**

EXP-036 reports *"63 of 121 reference tables regenerated and 58 archived: branch S behaved exactly as
designed"*, and closes at zero failures. **The 63 was true of that run and is not a property of the
package.** Revision 46 ran the same step list from the rebuilt package and regenerated **62**, because
`2026-09-04-failure-case-feature-fidelity.csv` was never written — **defect 8**, EXP-038 below, a
resume-boundary dependence in `2026-09-04-rphase5-failure-case.py` that had been latent in the package
since 2026-09-04.

The arithmetic is the evidence and it is exact: EXP-036 recorded **~306 checks**, revision 46's first pass
recorded **305**, and after the defect-8 fix restored the missing file the count returned to **306**. The
one check is the one file.

**What this does and does not change.** It changes no number: the file's twenty rows, once regenerated,
are **byte-identical** to the shipped reference. It does change the standing of EXP-036's gate — that run
passed this artifact by drawing a favourable set of process boundaries, not by demonstrating the package
produces it. **A clean-room pass whose completeness depends on where the resume boundaries fell is not a
pass, and the failure count alone cannot see that** — which is why the regenerated *count* now joins the
exit code and the failure count in the gate (**C18**). EXP-036 is otherwise left exactly as written (A9);
quote this addendum alongside it.

---

### EXP-038 — 2026-09-06 — The confirmation clean-room run from the NEWLY REBUILT package. **It found an EIGHTH defect: a shipped step that prints ALL DONE while silently discarding one of its three outputs, and whose loss depends on where the resume boundaries fall.**

> **EXP-037 is deliberately not used.** It is reserved by revision-45 record section 12.3 and D-025 for the
> pooled-vs-worst-facility pilot, which was out of this session's scope. The gap is intentional.

- **Authority:** revision-45 record section 11 item 1; PROJECT_STATUS "NEXT ACTIONS" item 0(i).
- **Prespecified before the package was unzipped:**
  `04_experiments/2026-09-06-revision46-cleanroom-confirmation-PRESPECIFICATION.md` (eleventh
  prespecification), section 0 measured on the shipped zip only.
- **What was run:** `~/cleanroom`, a fresh unzip of
  `2026-09-05-parking-conformal-reliability.zip` (sha256 `6d7c413b…daaa`, 269 files, 243 manifest
  entries, built 2026-09-05T20:08:13Z), every step of `run_all.sh` from an empty `05_results/tables/`.
  **~55 calls**, against the ~60 EXP-036 measured — core 4, e3 ~30, the rest ~15. The rate held.

## WHY THIS RUN EXISTED, AND WHAT IT CONFIRMED

Three code changes landed after EXP-036's run — the D-024 edit to the delay script, the unstable-cell
registry in `verify.py`, and the two retired spatial scripts — so the shipped package had never itself
been run end to end. **All three are confirmed exercised from scratch:**

| gate | prespecified | measured |
|---|---|---|
| Belgrade delay rows, facility 8 absent | 147, absent | **147**, facilities `[2,3,4,5,6,7,9]`, **absent** |
| Birmingham delay rows (the negative control) | 210 | **210** |
| `EXPERIMENTS_LOG.md` unmutated (defect 7) | `4fb37242…f0b5` | **`4fb37242…f0b5`, byte-identical** |
| e3 row counts (C11's check) | 164 / 196 | **164 / 196**, exactly |
| archived-artifact note | 58 | **58** |

**Defect 7 is confirmed fixed by the only test that counts.** The tracker the spatial step used to append
to came through a full from-scratch run byte-identical. That is the first time this has been demonstrated
rather than argued, because EXP-035 verified in a fresh unzip that restored the file (C16).

## DEFECT 8 — ALL DONE WITH THE OUTPUT MISSING, AND BOTH VERIFY PASSES AGREED

`verify.py` failed identically in **both** C16 passes — inside the tree actually run, and inside a fresh
unzip carrying only its outputs — at **305 checks, 1 failure**:

> `B NOTRUN 05_results/tables/2026-09-04-failure-case-feature-fidelity.csv — reference exists, generated
> file does not`

**Branch F did not fire** (the two passes agreed), and no published number differed, so this is not
branch B. The prespecification's branches did not anticipate this shape — an output that a *resumed* run
does not produce — and that is recorded rather than reclassified after the fact, exactly as EXP-036
recorded its own prespecification being stricter than the project's standard.

**Diagnosed by measurement, not by reading (rule 2). Two probes, each with a falsifiable prediction:**

| probe | prediction | result |
|---|---|---|
| re-run the step in the completed state | prints `ALL DONE`, writes nothing | **`ALL DONE`, file still absent** |
| remove ONE facility's leg-2 rows, re-run | file appears with **one** row, not twenty | **one row — and byte-identical to the reference's row for that facility** |
| remove TWO, run with a 1 s budget | the early `return` discards the row computed in that process | **`REMAINING`; leg 2 gained the facility's rows, the fidelity row was lost** |

**The mechanism.** `OUT_FID` was accumulated in an in-process list and written **once, after the loop**,
guarded by `if fid_rows:`. Its two siblings `OUT_L1` and `OUT_L2` flush per unit with `mode="a"`. So the
fidelity rows survive exactly one exit path — falling out of the loop — and are discarded by the
`--budget` cutoff's `return`, and by any external interruption of the process. Worse, a facility already
in `OUT_L2` is `continue`d before any computation, so **the terminal iteration always has an empty
accumulator**: the step reports `ALL DONE` while the file it owes does not exist. **Two of this project's
own rules were broken at once** — flush after every unit (**A1**) and make the completion marker respect
the same selection as the work loop (**EXP-035 defect 1 / C11**, now its fifth instance).

**It is a package defect, not an environment one.** It fires on a replicator's machine, deterministically
in the sense that matters — any run whose processes end by budget or interruption rather than by
exhausting the loop — and it is invisible to a run that happens to finish the loop in one process.
**EXP-036 was such a run**, which is why it reported 63 regenerated and this one 62. See the addendum
above.

## THE FIX, AND ITS OWN GATE

**A19 first:** `2026-09-04-rphase5-failure-case.py` was grepped against the freeze manifest **before** any
edit and is **not frozen** (it postdates 2026-09-02), so an in-place edit is the correct route and
`_retired/` would misdescribe it. The pre-fix copy is kept with both hashes in
`00_admin/2026-09-06-defect8/`.

Three changes: `OUT_FID` is read into `done_fid` at start; the fidelity row is appended **per unit**
inside the loop; and the completion check requires the fidelity row as well as the three leg-2 arms, so a
tree already in the broken state heals itself. **A first draft of the fix was discarded before it was
applied**: extending only the outer completion check would have left the inner arm loop `continue`-ing
past the `none` arm, so the facility could never clear and the runner would have spun to `MAX_ITERS` —
C11 one level in, and caught by reading the fix against the loop rather than by running it.

| gate | prediction, fixed before running | result |
|---|---|---|
| self-heal on the broken tree (leg 2 complete, file absent) | `OUT_FID` fills to 20; leg 2 stays at 60 with **no duplicates** | **20 rows; leg 2 exactly 60** |
| the regenerated file vs the shipped reference | identical | **byte-identical** |
| resume boundaries, from empty, 20 s budget | rows survive a cutoff and accumulate across processes | **11 after process 1 (`REMAINING`), 20 after process 2, 20 and idempotent after process 3** |
| `verify.py` after the fix | the `NOTRUN` clears, check count returns to 306 | **306 checks; the `NOTRUN` is gone** |

The eleven rows surviving process 1 are the whole point: under the old code that process wrote nothing.

## WHERE THE GATE ENDS

`verify.py` in both trees now reports **306 checks and one failure**, and that failure is
**`A CHANGED` on the script this session fixed** — an accounting consequence of the fix, cleared by the
manifest re-cut and package rebuild at the end of the session (C13). **No numerical cell differs
anywhere, in either tree.** No registered unstable cell was drawn this run, so the known-unstable note
did not print; both registry branches remain as revision 45 measured them.

**A limit restated:** `docker` and `podman` are still absent from this machine, the **Dockerfile remains
UNTESTED**, and this is not a container-verified clean room.

- **Lesson recorded: C18.**
- **Status:** the shipped package is confirmed end to end for the first time, with one defect found and
  fixed. **Closed out the same session, in C13's order — package rebuilt FIRST, manifest re-cut LAST.**
  Because a **code** file changed, the package is rebuilt rather than repaired: the new artifact is
  `06_manuscript/CTR/replication/2026-09-06-parking-conformal-reliability.zip` (270 files) and the
  2026-09-05 zip is **retired byte-intact** under `replication/_superseded/` — its sha256
  `6d7c413b…daaa` is pinned above as the artifact this run exercised, so it must survive. The repository
  manifest was superseded by date into
  `00_admin/2026-09-04-shipped-outputs/_superseded/2026-09-06-MANIFEST-outputs-PRE-S46.csv` (`verify.py
  --build` refuses to overwrite in place, which is the guard working) and re-cut at 241 entries;
  `verify.py` then **PASSES with zero unlisted**, and the gate closes at **50 / 48 / 127-of-130**.
  **No data file and no result table changed** — the regenerated
  `2026-09-04-failure-case-feature-fidelity.csv` is byte-identical to its reference, so **no reference
  refresh was owed and none was made** (C13 refreshes what legitimately changed, and nothing did).
  Outstanding: the untested Dockerfile, and **R-Phase 7**.

---

### EXP-037 — 2026-09-06 (revision 48) — The pooled-vs-worst-facility pilot, DESCRIPTIVE HALF ONLY. **The revision-45 chat numbers reproduce from a script that names its population; the §5.8 "twelve tests" were six — the other six are undefined, which is the stronger form of the point.**

> Numbered 037 and logged after 038 because the number was reserved (revision-45 record §12.3, D-025) while
> revisions 46–47 ran EXP-038 and the text pass. Run under the author's decision of 2026-09-06: *descriptive
> half only*. No inferential half was run and none is planned.

- **Prespecification (written before the run):** `04_experiments/2026-09-06-exp037-PRESPECIFICATION.md`.
- **Script:** `03_code/src/conformal/2026-09-06-exp037-pooled-vs-worst.py` (resumable, per-unit flush, both
  outputs in the completion check — C18; 0-byte output treated as absent).
- **Population, named in the CSV:** `2026-09-02-core-{belgrade,birmingham}-gcal-per-facility.csv`, `dynamic`,
  X08-excluded via `core.low_information_facilities` on each horizon's test rows (Belgrade facilities 1 and 8 on
  every horizon; Birmingham none), n = 21 / 28 on every populated row. Units: city × horizon × method × nominal
  level, statistics computed **within one level** (the pilot's +0.844 cross-level confound never enters).
- **Outputs:** `05_results/tables/2026-09-06-exp037-pooled-vs-worst.csv` (96 rows: **72 populated + 24 SKIPPED
  marker rows** — the source holds CQR / ACQR at 0.90 and 0.95 only; A2 marker rows, filter `n_facilities > 0`)
  and `2026-09-06-exp037-ncal-picp-correlation.csv` (12 rows).

**Predictions vs. measured:**

| # | prediction | measured | verdict |
|---|---|---|---|
| P1 | 96 populated rows, n = 21 / 28 | **72** populated (CQR/ACQR absent at 0.80/0.85 in the source); n = 21 / 28 on every populated row | count **missed** — a property of the source table, not of the data; recorded, not rescored |
| P2 | 23 of 24 within ±0.02 at 0.90 | **23 of 24** (the miss: Birmingham t+90 ACI, 0.876) | holds |
| P3 | worst facility 0.763–0.888 | **0.763–0.888** (Belgrade t+30 split-CP, facility 9; Belgrade t+5 ACQR, facility 13) | holds |
| P4 | mean-PICP range ≈ 0.031 vs worst-facility range ≈ 0.125 | **0.031 / 0.125** | holds |
| P5 | Belgrade t+15 / Birmingham t+60 rows reproduce T2 / T3' | mean and sd **identical to 6 dp**; worst facility within 5e-5 (T3' rounding) | holds — negative control passes (B7) |
| P6 | Belgrade `n_cal` constant → correlation undefined; Birmingham \|ρ\| ≤ 0.17, p ≥ 0.40 | Belgrade: **764 / 760 / 754, one distinct value per horizon — undefined on all six rows**; Birmingham: ρ ∈ [−0.167, +0.123], p ∈ [0.397, 0.979] | holds |

**What it means for the text.** (i) The descriptive sentence the pilot promised is now quotable, from the CSV:
*at the 0.90 level, 23 of 24 city-horizon-method configurations sit within 0.02 of nominal on mean facility
coverage while their worst facility ranges 0.763–0.888*. At 0.95 all 24 are within tolerance (worst 0.820–0.942);
at 0.80 and 0.85 (split-CP and ACI only) 8 of 12 and 11 of 12, worst facilities down to 0.585 — the gap widens
as the target loosens, which is consistent with the mechanism and is reported as a range, not a claim.
(ii) **§5.8 as written was wrong in form:** "null in every city-method-horizon combination tested (all |ρ| ≤ 0.17,
p ≥ 0.40)" implies twelve computed correlations. Six cannot be computed — Belgrade's calibration count is a
constant within each horizon — and the sentence now says so, which is the stronger statement (there is no
variation for shrinkage to act on), with the six Birmingham values from the CSV. D-025 §1's second bullet
("across twelve tests") is corrected by this entry; the decision it supports is unchanged.
- **Observation-weighted pooled PICP** differs from the unweighted facility mean by ≤ 0.003 on every 0.90 row;
  the paper's "mean facility coverage" is the unweighted mean throughout and the CSV carries both.
- **Status:** CLOSED. Descriptive numbers enter the manuscript through the generator (`typeset.json` keys
  `exp037`, `ncal`). Both CSVs are new artifacts → manifest re-cut and clean-room run this session (C13).
- **Same session, same clean-room run (not experiments, recorded here because they are new artifacts):**
  (i) `05_results/tables/2026-09-06-spatial-statistics.csv` — the two spatial scripts now write the statistics
  they print (Moran's I, Mantel r, naive Spearman, mean pairwise residual and raw-occupancy correlations); each
  rewrites only its own rows, sorted, so the file is byte-stable whichever runs last. Values equal the printed
  ones to 3 dp (Moran's I −0.009, p 0.905; Mantel r −0.129, p 0.151; raw-occupancy corr 0.516 — the EXP-006
  follow-up's "0.52" — on the same 21 facilities and 1,018 common test timestamps). §5.5 now reads from it.
  (ii) `05_results/figures/2026-09-06-f1-per-facility-coverage.{png,pdf}` and
  `2026-09-06-f2-reliability-efficiency.{png,pdf}` from `03_code/src/viz/2026-09-06-figures-f1-f2.py` under
  `04_experiments/2026-09-06-figures-f1-f2-PRESPECIFICATION.md`; byte-identical across two runs; exactly one
  off-scale marker (NGBoost, Birmingham) as prespecified. One presentation deviation from the prespecification,
  recorded: F1's y-axis floor 0.72 instead of 0.55 (nothing lies below 0.76 on this base) and no in-figure title.

---

### EXP-039 — 2026-09-06 (revision 48) — The clean-room run from the revision-48 package. **PASS on both C16 passes, zero failures, 66 of 124 reference tables regenerated, every new artifact byte-identical; the only misses are in the prespecification's own arithmetic.**

- **Prespecification (written after the build, before the unzip):**
  `04_experiments/2026-09-06-revision48-cleanroom-PRESPECIFICATION.md`.
- **Artifact exercised:** `06_manuscript/CTR/replication/2026-09-06-parking-conformal-reliability.zip`, sha256
  `885581665211c17e…`, 281 files, 252 manifest entries, 124 reference tables. Its predecessor (revision-46 build,
  `b0c9379f…`, never run end to end) is retired byte-intact as `replication/_superseded/2026-09-06-…-S46.zip`.
- **What was run:** `~/cleanroom`, fresh unzip, every step of `run_all.sh` from an empty `05_results/tables/`
  (`env core e3 tod trust baselearner orthogonal folds rolling delay x08 inference vignette rphase5 c01 relalloc
  display exp037 spatial figures verify`), **~45 `device_bash` calls**. The `e3` arms were advanced by calling
  the step's own script with the runner's exact arguments (`--dataset … --arm … --budget 100`) and the runner
  was then re-entered at `--from e3`, which re-ran every arm to `ALL DONE` before proceeding — the runner's
  loop, unchanged, is what certified the step.

**Predictions vs. measured:**

| # | prediction | measured | verdict |
|---|---|---|---|
| P1 | completes, exit 0, ~55–60 calls | **exit 0**, ~45 calls | holds |
| P2 | zero failures; regenerated **65**; archived 58; checks **309** | **zero failures**; regenerated **66**; archived **58**; checks **318** | count **missed by one, in the prediction**: 65 was 62 + 3, but 62 was EXP-038's *pre-defect-8* count; the post-fix baseline is EXP-036's 63, so 63 + 3 = 66 is the right number, and 318 = 252 entries + 66 comparisons. Recorded, not rescored (C18: the count is now pinned at **66 / 318** for the next run) |
| P3 | same result in a fresh unzip carrying only the run's tables (C16) | **PASS, 318 checks, zero failures** | holds |
| P4 | Belgrade delay 147 rows, facility 8 absent; Birmingham 210; e3 164 / 196 | **147 / absent / 210 / 164 / 196** | holds |
| P5 | no unstable cell drawn, or named by the registry | none drawn | holds |

**Per-change gates (section 1 of the prespecification):** `2026-09-06-exp037-pooled-vs-worst.csv`,
`2026-09-06-exp037-ncal-picp-correlation.csv` and `2026-09-06-spatial-statistics.csv` regenerated
**byte-identical** to the shipped reference; the F1'/F2' step printed `off-scale markers: 1` and its four files
were written, the two PNGs **byte-identical** to the repository's (not a gate — figures are `not_gated` — but
recorded); `EXPERIMENTS_LOG.md` sha256 `e6368841489748ef…` **before and after** the run (defect 7 stays fixed).

**One operational note, not a defect:** the machine was slower than in EXP-036/038 (core ≈ 16 s per Belgrade
facility; e3 A12 ≈ 48 s), so the runner's default `BUDGET=150` plus one unit's overshoot exceeded a 172-second
call before the step saved. `BUDGET` is an environment variable for exactly this reason; the run used 75–110.
No code changed for it.

- **Limits restated:** `docker`/`podman` absent; the **Dockerfile remains UNTESTED**; the manuscript docx chain
  (A20) is outside the package.
- **Status:** CLOSED — **the revision-48 package is confirmed end to end.** Closed out in C13's order: the
  package was built first (before this run), this entry written, the repository manifest re-cut LAST
  (`_superseded/2026-09-06-MANIFEST-outputs-PRE-S48-FINAL.csv`).

---

### EXP-040 — 2026-09-07 (revision 49) — §5.5's spatial leg recomputed on the paper's evaluation base. **The negative control reproduces all seven published values to 6 dp; the null survives on the correct roster, and the level-vs-residual contrast the section rests on gets stronger.**

- **Prespecification (written before the script existed):**
  `04_experiments/2026-09-07-spatial-exclusion-base-PRESPECIFICATION.md`. Fifteenth prespecification.
- **Decision:** D-030. **Trigger:** locating the ESM figure makers, not a planned audit.
- **Script:** `03_code/src/spatial/2026-09-07-spatial-exclusion-base.py` — read-only re-aggregation, **no model
  is fitted**, writes no tracker (defect-7 class), deterministic (seed 42; 999 Moran / 9,999 Mantel permutations).
- **Population:** `2026-06-21-spatial-corr-distance.csv` (210 pairs), `2026-06-21-spatial-facility-uncertainty.csv`,
  and the `occupancy` column of `belgrade_features_v2.parquet` test rows. Two rosters in one output:
  `published_21` = 2–9, 11–23 (coords ∧ train std ≥ 5 — **retains facility 8**, omits 24) and `exclusion_base`
  = 2–7, 9, 11–23 (**20**; the evaluation base ∩ has-coordinates).
- **Output:** `05_results/tables/2026-09-07-spatial-statistics-exclusion-base.csv` (14 rows, 7 statistics × 2
  rosters, each row naming its `facility_ids`, `n_pairs` and `n_common_test_timestamps`).

**Predictions vs. measured:**

| # | prediction | measured | verdict |
|---|---|---|---|
| P1 | **negative control (the gate):** on the published roster, Mantel r −0.128609 / p 0.151300, naive ρ −0.121024 / p 0.080156, mean resid corr 0.007124, near 0.025100, far −0.004525 | **all five to 6 dp**, and additionally Moran's I **−0.008668 / p 0.905000** and raw-occupancy corr **0.516474**, neither of which had been pre-checked | **holds — 7 of 7** |
| P2 | on 20 facilities: Mantel r −0.128386 / p 0.139300, naive ρ −0.132960 / p 0.067436, mean resid corr 0.012282, near 0.037066, far 0.002155 | identical to 6 dp | holds *(baseline named: computed read-only from the pairwise table earlier the same session, as the sensitivity check that triggered D-030 — C20)* |
| P3 | Moran's I on 20 stays non-significant; sign and magnitude unpredicted | **+0.008912, p 0.888** (was −0.008668, p 0.905) — the **sign flips at magnitude ~0.009**, which is the honest reading: the statistic is indistinguishable from zero on either roster | holds |
| P4 | raw-occupancy co-movement **rises** above 0.516474; magnitude unpredicted | **0.584386** | holds — direction correct |
| P5 | neither Moran's I nor Mantel reaches p ≤ 0.05 on the correct base | Moran p 0.888, Mantel p 0.139 | **holds — the null survives** |
| P6 | two runs give a byte-identical CSV | sha256 equal across two runs | holds |

**What it means for the text.** §5.5 now names its population (20 evaluated facilities carrying coordinates; one
further facility has none) and reads every number from the new CSV. **The section's own contrast strengthens:**
occupancy *levels* co-move at **0.58** while model *residuals* sit at **0.012**. The `mean_aci_halfwidth`
descriptor Moran's I runs on is the **fixed-γ = 0.05** half-width from the pre-audit script, not the paper's
calibration-selected γ; it is named as such in the text rather than regenerated, because it is an uncertainty
*descriptor* and regenerating it is a refit (D-030, recorded as a known limit).

- **A21 discipline held:** the frozen 2026-06-21 tables were read and never written; `verify-state.sh freeze`
  re-run after the script and reported **121 of 130, PASS**.
- **Status:** CLOSED. New table → manifest re-cut and a full clean-room run this session (C13).

- **Same session, same clean-room run (not an experiment — recorded here because they are new artifacts):**
  **ESM figures**, under `04_experiments/2026-09-07-esm-figures-PRESPECIFICATION.md` (sixteenth), maker
  `03_code/src/viz/2026-09-07-figures-esm.py` (reads only manifest-listed tables; byte-identical across two runs).
  The four pre-audit renders become **two figures that both trace to a CSV**, and no artifact in the submission
  carries pre-audit pixels any more.
  (i) **S1 regenerated and strengthened** from `2026-09-06-exp037-pooled-vs-worst.csv`: two panels, mean facility
  coverage *and* **worst facility coverage** against nominal level. Measured: the worst-facility curve lies below
  the diagonal at every level for every method (split-CP 0.694 / 0.744 / 0.787 / 0.834 at 0.80 / 0.85 / 0.90 /
  0.95; ACI 0.765 / 0.819 / 0.869 / 0.919), while the mean curve tracks it. That contrast is the paper's thesis
  and the pre-audit figure drew only the mean.
  (ii) **S3 → S2**, regenerated on EXP-040's 20-facility base, annotated with **both** the Mantel r and the naive
  ρ. The pre-audit render titled itself with the naive Spearman alone — the statistic §5.5 says does not survive
  the correction — so it could be read as showing a borderline trend. That is a presentation defect, corrected.
  (iii) **Old S2 (example facility) CUT.** No CSV supports a per-timestamp trace; reproducing it needs a fit, a
  new artifact and a clean-room run, for a figure supporting no number in the manuscript. Its retired maker also
  carries a second inline implementation of delay-aware ACI, which B9 forbids shipping unverified.
  (iv) **Old S4 (trust/abstain) CUT as redundant** with revision 48's ESM Table S6, which is the same operating
  curve on the exclusion base *with* the matched random control the figure lacked.
  Main text and ESM reference no ESM figure and the ESM has no internal figure cross-reference (checked by grep),
  and figures and tables are separate S-sequences, so the cut and renumber have **no cross-reference consequence**.
