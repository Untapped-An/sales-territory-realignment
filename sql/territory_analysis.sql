-- territory_analysis.sql
-- Descriptive analysis of the Ohio anticoagulant field force.
-- Tables: accounts (data/clean/accounts.csv), reps (data/clean/reps.csv).
-- Written in the common subset of MySQL 8 and SQLite: CTEs and window
-- functions, COALESCE/CASE only, no dialect-specific functions.
-- Run with:  python sql/run_sql.py

-- Q1. Value concentration (Pareto): cumulative share of value by prescriber rank
WITH ranked AS (
    SELECT npi, value,
           ROW_NUMBER() OVER (ORDER BY value DESC) AS rnk,
           SUM(value) OVER (ORDER BY value DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_value,
           SUM(value) OVER () AS total_value,
           COUNT(*) OVER () AS n
    FROM accounts
)
SELECT CASE WHEN cum_value / total_value <= 0.5 THEN 'top 50% of value'
            WHEN cum_value / total_value <= 0.8 THEN 'next 30% of value'
            ELSE 'last 20% of value' END AS value_band,
       COUNT(*) AS prescribers,
       ROUND(100.0 * COUNT(*) / MAX(n), 1) AS pct_of_prescribers
FROM ranked
GROUP BY CASE WHEN cum_value / total_value <= 0.5 THEN 'top 50% of value'
              WHEN cum_value / total_value <= 0.8 THEN 'next 30% of value'
              ELSE 'last 20% of value' END
ORDER BY MIN(rnk);

-- Q2. Top 3 prescribers by value within each specialty group
WITH r AS (
    SELECT specialty_group, npi, city, value,
           RANK() OVER (PARTITION BY specialty_group ORDER BY value DESC) AS rnk_in_group
    FROM accounts
)
SELECT specialty_group, rnk_in_group, npi, city, ROUND(value, 0) AS value
FROM r WHERE rnk_in_group <= 3
ORDER BY specialty_group, rnk_in_group;

-- Q3. Rep workload before and after, ranked into quartiles by original load
WITH before_load AS (
    SELECT original_rep_id AS rep_id, SUM(calls) AS calls_before, COUNT(*) AS accts_before
    FROM accounts GROUP BY original_rep_id
),
after_load AS (
    SELECT rebalanced_rep_id AS rep_id, SUM(calls) AS calls_after
    FROM accounts GROUP BY rebalanced_rep_id
)
SELECT r.rep_id, r.region,
       COALESCE(b.calls_before, 0) AS calls_before,
       COALESCE(a.calls_after, 0) AS calls_after,
       NTILE(4) OVER (ORDER BY COALESCE(b.calls_before, 0) DESC) AS load_quartile_before
FROM reps r
LEFT JOIN before_load b ON b.rep_id = r.rep_id
LEFT JOIN after_load a ON a.rep_id = r.rep_id
ORDER BY calls_before DESC;

-- Q4. The magnitude-blind metric vs total excess load (capacity = 800 calls)
WITH loads AS (
    SELECT 'before' AS state, original_rep_id AS rep_id, SUM(calls) AS calls FROM accounts GROUP BY original_rep_id
    UNION ALL
    SELECT 'after', rebalanced_rep_id, SUM(calls) FROM accounts GROUP BY rebalanced_rep_id
)
SELECT state,
       SUM(CASE WHEN calls > 800 THEN 1 ELSE 0 END) AS reps_over_capacity,
       SUM(CASE WHEN calls > 800 THEN calls - 800 ELSE 0 END) AS total_excess_calls
FROM loads GROUP BY state;

-- Q5. Disruption: share of accounts and of value that changed rep, by region
SELECT region,
       COUNT(*) AS accounts,
       SUM(CASE WHEN original_rep_id <> rebalanced_rep_id THEN 1 ELSE 0 END) AS moved,
       ROUND(100.0 * SUM(CASE WHEN original_rep_id <> rebalanced_rep_id THEN 1 ELSE 0 END) / COUNT(*), 1) AS moved_pct,
       ROUND(100.0 * SUM(CASE WHEN original_rep_id <> rebalanced_rep_id THEN value ELSE 0 END) / SUM(value), 1) AS value_moved_pct
FROM accounts
GROUP BY region
ORDER BY region;

-- Q6. Which accounts moved? Moved vs unmoved by value decile (lowest-value-first check)
WITH d AS (
    SELECT value, original_rep_id, rebalanced_rep_id,
           NTILE(10) OVER (ORDER BY value) AS value_decile
    FROM accounts
)
SELECT value_decile,
       COUNT(*) AS accounts,
       SUM(CASE WHEN original_rep_id <> rebalanced_rep_id THEN 1 ELSE 0 END) AS moved
FROM d
GROUP BY value_decile
ORDER BY value_decile;
