-- bigquery_extract.sql
-- The two queries run in Google BigQuery (sandbox) against the public CMS
-- Medicare Part D Prescriber table for 2014. Both are reproduced exactly as
-- they were run, so they regenerate the files this project uses.

-- ---------------------------------------------------------------------------
-- Query A — prescriber-level extract
-- Output: data/clean/prescribers_raw_query.csv (7,759 rows, one per NPI)
-- BigQuery job: job_q50MQt6QzmtJu0wE0Fgu5_VVvpjE
--
-- NOTE ON SCOPE: the dabigatran literal below was copied from a truncated
-- result cell ('DABIGATRAN ETEXILATE MESY...') and therefore matches no rows.
-- The extract, and every result in this project, covers THREE molecules:
-- rivaroxaban, apixaban and warfarin sodium. Query B quantifies what was left
-- out (dabigatran: 1,500 Ohio prescribers, ~$19.9M). The full generic name is
-- 'DABIGATRAN ETEXILATE MESYLATE'; including it is a documented extension,
-- not part of the current results.
--
-- suppressed_rows counts rows whose 65+ beneficiary breakdown is suppressed
-- (ge65_suppress_flag). It is NOT the <11-claim suppression: those rows are
-- absent from the public file altogether. It is not used in the model.
-- ---------------------------------------------------------------------------
SELECT
  npi,
  ANY_VALUE(specialty_description) AS specialty,
  ANY_VALUE(nppes_provider_city)   AS city,
  SUM(total_claim_count)           AS total_claims,
  SUM(total_drug_cost)             AS total_drug_cost,
  SUM(total_day_supply)            AS total_day_supply,
  MAX(bene_count)                  AS max_bene_count,
  COUNT(DISTINCT drug_name)        AS n_drugs,
  SUM(CASE WHEN UPPER(drug_name) != UPPER(generic_name) THEN total_drug_cost ELSE 0 END) AS brand_cost,
  SUM(CASE WHEN UPPER(drug_name)  = UPPER(generic_name) THEN total_drug_cost ELSE 0 END) AS generic_cost,
  COUNTIF(ge65_suppress_flag IS NOT NULL AND ge65_suppress_flag != '') AS suppressed_rows
FROM `bigquery-public-data.cms_medicare.part_d_prescriber_2014`
WHERE nppes_provider_state = 'OH'
  AND UPPER(generic_name) IN (
    'RIVAROXABAN',
    'DABIGATRAN ETEXILATE MESY...',   -- truncated: matches nothing (see note above)
    'APIXABAN',
    'WARFARIN SODIUM'
  )
GROUP BY npi
ORDER BY total_drug_cost DESC;


-- ---------------------------------------------------------------------------
-- Query B — per-drug totals, used as a reconciliation check
-- BigQuery job: job_NWQ3DgDckClGpQ9k_HcvPrOMZgK4
--
-- Result (Ohio, 2014):
--   RIVAROXABAN                    2,937 prescribers   114,095 claims   $38,841,610
--   DABIGATRAN ETEXILATE MESYLATE  1,500 prescribers    50,094 claims   $19,927,343
--   APIXABAN                         794 prescribers    29,090 claims   $10,605,294
--   WARFARIN SODIUM                7,395 prescribers   806,595 claims    $9,208,351
--
-- Check: rivaroxaban + apixaban + warfarin = 949,780 claims and $58,655,255,
-- which equals Query A's totals (949,780 claims, $58,655,254 before rounding).
-- So Query A dropped nothing within its three-molecule scope.
-- ---------------------------------------------------------------------------
SELECT
  generic_name,
  COUNT(DISTINCT npi)          AS prescribers,
  SUM(total_claim_count)       AS claims,
  ROUND(SUM(total_drug_cost))  AS drug_cost
FROM `bigquery-public-data.cms_medicare.part_d_prescriber_2014`
WHERE nppes_provider_state = 'OH'
  AND ( UPPER(generic_name) LIKE '%WARFARIN%'
     OR UPPER(generic_name) LIKE '%APIXABAN%'
     OR UPPER(generic_name) LIKE '%RIVAROXABAN%'
     OR UPPER(generic_name) LIKE '%DABIGATRAN%' )
GROUP BY generic_name
ORDER BY drug_cost DESC;
