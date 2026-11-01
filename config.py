"""
config.py — every modelling assumption in one place.

An interviewer should be able to open this file and see, in ten seconds,
every number the analysis takes on faith. Anything here is an ASSUMPTION,
not a finding. Results in RESULTS.md always state which of these they rest on.
"""

# ---------------------------------------------------------------- data
# Source: CMS Medicare Part D Prescriber data, 2014 (BigQuery public dataset
# bigquery-public-data.cms_medicare.part_d_prescriber_2014), Ohio,
# oral anticoagulants: rivaroxaban (Xarelto), apixaban (Eliquis), warfarin.
# Aggregated to one row per prescriber (NPI) by the BigQuery query (Query A).
RAW_FILE = "data/clean/prescribers_raw_query.csv"
DATA_YEAR = 2014

# Coverage universe: prescribers below this annual drug cost are treated as
# non-target (no rep calls on them). Real field forces do this too.
MIN_VALUE_USD = 2_500

# ---------------------------------------------------------------- workload
# Workload is measured in CALLS per year, set by value tier (call plan).
# Tier cut points are percentiles of account value within the target universe.
TIER_A_TOP_PCT = 0.20      # top 20% of accounts by value
TIER_B_NEXT_PCT = 0.30     # next 30%
CALLS_PER_YEAR = {"A": 24, "B": 12, "C": 6}   # twice-monthly / monthly / bi-monthly

# Rep capacity on THIS franchise: ~1,600 calls/yr per rep, of which an
# assumed 50% is spent on the anticoagulant brand (reps carry 2–3 products).
CAPACITY_CALLS = 800

# ---------------------------------------------------------------- field force
BASELINE_REPS = 45          # current (synthetic) headcount
REGIONS = ["Northeast", "Northwest", "Central", "Southwest", "Southeast"]

# Legacy drift: each rep's "pull" on accounts ~ lognormal(0, DRIFT_SIGMA).
# Higher sigma = more historical imbalance. Synthetic — no real territory
# map is public for any company.
DRIFT_SIGMA = 0.35
SEED = 7

# ---------------------------------------------------------------- response
# Hard cutoff: capture = min(1, capacity / load)
# Smooth:      capture = 1 - exp(-LAMBDA * capacity / load)
# LAMBDA = 2.303 gives 90% capture when a rep is exactly at capacity.
LAMBDA = 2.303

# ---------------------------------------------------------------- frontier
CAP_PCT_GRID = [0, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 40, 50]

# ---------------------------------------------------------------- sizing
SIZING_RANGE = range(30, 81)
# Share of captured drug cost that is contribution to the manufacturer.
# Medicare Part D cost is a proxy for brand revenue in the account.
CONTRIBUTION_MARGIN = 0.70
# Annual cost of one rep CHARGED TO THIS FRANCHISE (USD): 50% of a
# fully-loaded rep cost of $160k / $240k / $320k, matching the 50% time
# share in CAPACITY_CALLS. Swept, never fixed — optimal N is sensitive to
# it and we report that sensitivity rather than one confident number.
COST_LEVELS = {"low": 80_000, "mid": 120_000, "high": 160_000}

# ---------------------------------------------------------------- sensitivity
CAPACITY_GRID = [500, 650, 800, 1000, 1200]
