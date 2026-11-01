# DATA_NOTES — cleaning decisions and the rows they affect

Source: `bigquery-public-data.cms_medicare.part_d_prescriber_2014`, filtered to
Ohio and generic names RIVAROXABAN, APIXABAN, WARFARIN SODIUM, aggregated to one
row per NPI in BigQuery (Query A, in `sql/bigquery_extract.sql`). Dabigatran
was intended to be in scope, but its name was entered from a truncated result
cell ('DABIGATRAN ETEXILATE MESY...') and matched no rows, so the analysis covers
three molecules. Query B's per-drug totals reconcile exactly with Query A for
those three (949,780 claims, $58,655,254); dabigatran (1,500 prescribers,
~$19.9M) is the main documented gap.

| # | Issue | Finding | Decision |
|---|---|---|---|
| 1 | Data year | Public BigQuery table is 2014 | Kept; stated as a limitation (early DOAC era) |
| 2 | Suppression | Min claims = 11 exactly: CMS drops rows < 11 claims; not flagged | Documented as left-censoring; no imputation |
| 3 | Beneficiary count | Missing for 3,366 prescribers (43%); not additive across drugs | Dropped from the model; claims and cost used |
| 4 | NPIs | 7,759 unique, all 10 digits | No action needed (validated in code) |
| 5 | Brand + generic = total | Exact on every row | Validated in code |
| 6 | Specialty | 57 raw labels, 25 with < 5 prescribers; "Family Practice" vs "Family Medicine" | Collapsed into 6 groups (`src/clean.py`) |
| 7 | City | 500 free-text cities; spelling variants (MAYFIELD HTS/HGTS, HILLARD, E LIVERPOOL…) | 65 records normalised; mapped to 5 regions |
| 8 | Cost per claim | $1.90 – $736 (warfarin ~$11, DOACs ~$340) | Kept; value = drug cost, noted as brand-weighted |
| 9 | Long tail | 47% of prescribers < $1,000 (2.3% of value) | Coverage threshold $2,500 → 3,282 targets, 95.6% of value |
| 10 | Outliers | Max $354,566 (cardiologists) | Kept: the skew is the finding |
