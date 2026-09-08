# The v1 feature tables: attribution only. NOT for any reported result.

`belgrade_features.parquet` and `birmingham_features.parquet` are the **v1** tables. They
carry the defects the revision fixed:

* **S01** — training and calibration rows whose outcome is observed in a later split.
* **S02 / X01** — Birmingham lags, anchors and targets that cross a night boundary, which
  contaminated about 10% of the t+90 targets.

**Every reported number in the article is computed on the `*_features_v2.parquet` tables.**
The v1 tables are shipped for one reason: the `A12_v1_paired` arm of
`03_code/src/conformal/2026-09-03-e3-baselines.py` runs both EnbPI chunking schemes on ONE
fitted model per facility to attribute the C07 protocol delta (row 1 of the
protocol-sensitivity table). That comparison is only meaningful on the configuration the
archived result came from, and it is paired inside a single fit, so the leakage is common to
both sides of the delta and cancels.

Do not use these tables for anything else. `run_all.sh` uses them for that one arm and
nowhere else.
