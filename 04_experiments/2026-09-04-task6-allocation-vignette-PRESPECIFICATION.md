# PRESPECIFICATION — R-Phase 3b task 6, the risk-aware allocation vignette (EXP-029)

**Written 2026-09-04, revision 40, BEFORE anything was run.** Fourth prespecification in this project.
Closes audit issues **D01** (capacity proxy computed from data the policy is being evaluated on),
**D02** (the word "detour" claims a road-network computation we never did) and **D03** (a single seed).
The vignette is the **last experiment in the paper still carrying pre-audit numbers**.

**Author's framing, recorded because it changes the standard of proof, not the design:** under the
operational reading this vignette is the paper's payoff. It is therefore held to the same standard as a
headline experiment, and it is demoted to the ESM on a rule fixed here rather than on how the numbers look.

---

## 0. FACTS MEASURED ON THE INPUTS FIRST, BECAUSE THREE OF THEM CHANGE THE DESIGN

Measured before anything was run. None is a result; all are properties of the data (B19).

**(a) The archived design has five defects, not the three D01-D03 names.** `2026-08-04-allocation-vignette.py`
reads **v1** features (not `*_features_v2.parquet`, so it carries the S01/S02/X01 leakage the whole
revision exists to remove and applies no `use_15` filter); it contains **its own local `acqr_delayed`
implementation** rather than `core.py`, written before the C01/C02 fixes; it **fixes gamma = 0.05**
where every other experiment now selects it on calibration (EXP-019); it takes capacity as the max over
the **full record, test window included** (D01); and it applies **no low-information exclusion** (D-018,
which did not exist when it was written).

**(b) D01 is material, and it is worst exactly where X08 is.** Training-only versus full-record capacity
proxy, on the 21 coord-matched dynamic facilities: 15 are identical, five move by 0.5-9 spaces
(facilities 3, 4, 12, 14, 20), and **facility 8 moves 65 -> 109**. 109 is the stuck value the dead sensor
reports inside the test window (X08), so the archived vignette handed facility 8 a capacity **read off
the window it was being scored on**. For the 20 facilities we retain, the correction is small, one-signed
and tightens both policies.

**(c) The archived demand anchor does not survive and must be recomputed.** 65% of requests were
concentrated on facilities **{8, 9, 10, 23}**, described as those running ">=90% of capacity". Facility
**8 is low-information in both candidate windows** and is excluded by D-018; facility **10 is not in the
v2 dynamic set** (training std < 5.0). Leaving the anchor hardcoded would define the paper's stress case
partly by a dead sensor. The replacement rule is in section 3 and is stated on training inputs only.

**(d) Both windows exist and are usable, and X09 is visible but not disqualifying.** In the 12:00-19:00
afternoon window of the test split, with `use_15`: **weekday Mar 20-21 = 167 scored slots**, **weekend
Mar 18-19 = 147** (Mar 19 carries 63 of a possible 84 afternoon slots; the other three days are complete).
Because every policy is scored on **identical** slots and identical requests, uneven coverage cannot bias
the contrast — it costs precision, not validity. Equivalent-full-slots per window is reported (B19).

**(e) The scored base is 20 facilities in both windows.** `core.low_information_facilities` applied to
each scored window returns **{8}** in both. Distinct-reading gap on the weekday window: facility 8 -> 2,
next lowest (16) -> 33, then 61, 67, 69 — the [3, 60] insensitivity band of B16 is republished on this
window rather than assumed from the main split.

## 1. Arms — fixed in advance

| arm | rule at request time | purpose |
|---|---|---|
| **POINT** | assign the nearest facility with `cap - yhat >= s` | the archived baseline policy |
| **INTERVAL** | assign the nearest facility with `cap - U >= s`, `U` = ACQR 90% upper bound | the paper's claim: calibrated upper bounds change the decision |
| **MARGIN (negative control)** | assign the nearest facility with `cap - (yhat + m) >= s`, `m` a **single constant** | separates *"calibrated intervals help"* from *"any conservatism helps"* |

`s = 1` space, unchanged from the archived design.

**Why MARGIN is not optional.** Without it, the vignette shows only that a more conservative policy
overflows less, which is trivially true and which a referee gets to say first. `m` is set to the mean of
`U - yhat` over the scored window rows of the base — matched **by construction** to INTERVAL's average
conservativeness, not chosen to optimise any outcome. It is a width statistic, and both arms see the same
intervals. **If MARGIN reproduces INTERVAL's overflow reduction at the same distance cost, the claim
narrows to conservatism and must be rewritten that way** (section 5).

## 2. Everything held at archived values, so the delta is attributable (B6)

`R = 600` requests per seed; hot fraction 0.65; `sigma = 0.0035` (~350 m); uniform component over the
facility bounding box with a 15% margin; anchor cardinality **4**; `s = 1`; horizon **t+15 (h = 3
steps)**; `alpha = 0.10`; RandomForest `n_estimators=100, min_samples_leaf=2`, HistGBR quantile
`max_iter=100`; **fit seed 42**. Only what D01-D03, D-018 and `core.py` require is changed.

## 3. What changes, each with its reason

1. **Data:** `belgrade_features_v2.parquet`, rows with `use_15` only.
2. **Intervals:** `core.adaptive_conformal_stream` (ACQR via a CQR band), replacing the script's local
   implementation. One definition of the method in this project (B9).
3. **Gamma:** `core.select_gamma_on_calibration` per facility, never read off the test window (EXP-019).
4. **Capacity proxy:** `cap = max(occupancy)` over the **TRAINING split only** (D01). Published per
   facility alongside the full-record value so the size of the correction is visible.
5. **Population:** dynamic on the **training** window (std >= 5.0, I05), coord-matched, minus
   `core.low_information_facilities` applied to **each scored window** (D-018; one definition, B9).
6. **Demand anchor:** the **4 facilities in the scored base with the highest ratio of training-window
   mean occupancy to training capacity proxy**, computed over hours 12:00-19:00 on **training days of the
   same day type** as the window being scored. Stated on training inputs alone, blind to every policy's
   outcome; cardinality 4 fixed to match the archived design so nothing is tuned. The four ratios and the
   next two runners-up are published.
7. **Seeds:** the fit is done **once** (seed 42) and **20 demand seeds, 1..20**, vary the requests only —
   arrival slots, hot/cold assignment, anchor choice and destination coordinates. All three policies are
   scored on **identical requests within a seed** (paired), which is what makes the per-seed difference
   the right unit.
8. **Windows:** weekday **Mar 20-21** and weekend **Mar 18-19**, run and reported **separately**.
9. **Naming:** "detour" is replaced by **"additional straight-line distance"** in the script, the CSV
   column names, the figure and the log (D02). The quantity was always a haversine distance between two
   points; the old name asserted a routing computation that was never performed.

## 4. The gate, run before any new number is read (the EXP-027 pattern, B17)

`2026-09-04-vignette-repro-gate.py` is the archived script with **only its two output paths changed**
(diffed to prove it). It must reproduce the logged EXP-015 summary **to 4 dp**:

```
POINT     assigned 1.0000  overflow 0.1483  mean_dist 1.1342  p90 3.2228
INTERVAL  assigned 1.0000  overflow 0.0000  mean_dist 1.1834  p90 3.2228
```

**If it reproduces:** the "before" column of every delta is the number actually published, and the
pipeline is sound end to end. **If it does not:** STOP, report the discrepancy, and do not quote any
before/after delta. v1 features under an unpinned scikit-learn is precisely the A13 hazard that has
already moved a published number in this project. Either outcome is logged.

**Recorded so it is not claimed afterwards (B18):** reproducing 0.1483 would validate the *pipeline*, not
the *number*. 0.1483 was computed on a base including facility 8 with a capacity read from the test
window. It can be perfectly reproducible and still wrong, and section 5 does not treat it as a target.

## 5. Outcomes — what counts as which, decided before seeing the data

**Primary quantity.** Per seed, per window: `Delta = overflow_rate(POINT) - overflow_rate(INTERVAL)`,
in percentage points, over assigned requests. Reported as a **distribution across the 20 seeds** with a
**95% percentile-bootstrap CI (B = 10,000) on the mean**, never as a point estimate (D03).
**Secondary:** `Delta_dist = mean_additional_straight_line_distance(INTERVAL) - (POINT)`, same treatment.
**Control contrast:** `overflow_rate(MARGIN) - overflow_rate(INTERVAL)` and its distance analogue.

- **CONFIRMS** — main text: in **both** windows, the 95% CI for `Delta` excludes 0 **and** `Delta > 0` in
  **at least 19 of 20 seeds**, **and** INTERVAL beats MARGIN on overflow at equal or lower distance cost,
  or beats it on distance at equal overflow.
- **WEAKENS but survives** — main text, narrower claim: the CI excludes 0 in both windows but **MARGIN
  matches INTERVAL**. Then the demonstrated claim is that *conservatism* reduces failed trips and the
  contribution of *calibration* is that it supplies the margin without a tuning parameter — which is a
  smaller and honest claim, and it is the one that gets written.
- **SEED-SENSITIVE -> demote to ESM:** `Delta <= 0` in **2 or more** of the 20 seeds in either window, or
  the 95% CI for `Delta` includes 0 in either window. This is the D03 demotion rule and it is numeric.
  IQR/median of `Delta` is reported as a stability diagnostic but is **not** a gate — a claim can have a
  variable magnitude and a stable sign, and only the sign is being asserted.
- **CONTRADICTS -> stop and write up:** INTERVAL overflows **more** than POINT in either window, or
  INTERVAL's advantage is an artifact of refusing service (below).

**The honesty guard, fixed now.** INTERVAL can reach 0% overflow by refusing to assign. If **INTERVAL's
assignment rate falls below 99%** in either window, the headline switches to the **combined
unserved-or-overflowed rate** over all requests, and the overflow-only figure is demoted to a supporting
row. Assignment rate is reported for all three arms in every case.

**Predicted in advance so the outcome is logged either way (C4):** the training-only capacity proxy is
smaller at 5 of the 20 retained facilities, so both policies become more conservative; POINT's overflow
rate should fall somewhat from 14.83% and INTERVAL's assignment rate is the number at risk. No prediction
is recorded for MARGIN — that is the point of it.

## 6. Forbidden

Changing the anchor rule, the seed count, the window definitions or the demotion threshold after seeing
any of them; tuning `m`, `s`, the hot fraction or `sigma` on an outcome; dropping a seed, facility, slot
or window without a rule stated on the inputs and shown insensitive to its threshold (B16); reporting the
mean of `Delta` without its CI or its seed-level spread; quoting the archived 14.8% / 0.0% / +49 m
alongside the new numbers as though the two were a controlled decomposition — they are not, because
several changes land together, and the log must say so; and reporting an INTERVAL advantage without the
MARGIN row next to it.
