"""
clean.py — turn the BigQuery prescriber extract into the account universe.

Input is one row per NPI (Query A, already aggregated in BigQuery).
Steps, each logged so DATA_NOTES.md can quote the counts:

1. Validate NPIs (10 digits, unique).
2. Normalise city spellings and map city -> region (src/geo.py).
3. Collapse 57 raw specialty labels into 6 analytic buckets.
4. Drop beneficiary count from the model: it is suppressed (<11) for ~43%
   of prescribers and cannot be summed across drugs (one patient can be on
   two), so claims and cost are used instead.
5. Apply the coverage threshold (config.MIN_VALUE_USD).
6. Assign value tiers and the call plan that defines workload.

Note on suppression: CMS removes any prescriber-drug row with fewer than
11 claims from the public file entirely. It is not flagged — those rows are
simply absent. The minimum total_claims in the extract is exactly 11, which
is the fingerprint of that left-censoring.
"""
import pandas as pd
import config
from src.geo import clean_city, region_of

SPECIALTY_BUCKETS = {
    "Cardiology": ["Cardiology", "Cardiac Electrophysiology", "Cardiac Surgery",
                   "Peripheral Vascular Disease", "Thoracic Surgery"],
    "Primary Care": ["Internal Medicine", "Family Practice", "Family Medicine",
                     "General Practice", "Geriatric Medicine", "Preventive Medicine",
                     "Hospitalist"],
    "APP (NP/PA)": ["Nurse Practitioner", "Physician Assistant",
                    "Certified Clinical Nurse Specialist", "Registered Nurse",
                    "Certified Nurse Midwife"],
    "Hematology/Oncology": ["Hematology/Oncology", "Hematology", "Medical Oncology",
                            "Gynecological/Oncology"],
    "Surgery": ["General Surgery", "Vascular Surgery", "Orthopedic Surgery", "Surgery"],
}
_BUCKET = {s: b for b, specs in SPECIALTY_BUCKETS.items() for s in specs}


def load_universe(log=print):
    raw = pd.read_csv(config.RAW_FILE)
    log(f"raw prescribers: {len(raw):,}")

    npi = raw["npi"].astype(str)
    assert npi.str.fullmatch(r"\d{10}").all(), "malformed NPI"
    assert not npi.duplicated().any(), "duplicate NPI"
    assert (raw["brand_cost"] + raw["generic_cost"] - raw["total_drug_cost"]).abs().max() < 0.01

    df = raw.copy()
    df["city_raw"] = df["city"]
    df["city"] = df["city"].map(clean_city)
    log(f"city spellings fixed: {(df['city'] != df['city_raw'].str.upper().str.strip()).sum()} rows")
    df["region"] = df["city"].map(region_of)
    df["specialty_group"] = df["specialty"].map(_BUCKET).fillna("Other")
    df["brand_share"] = (df["brand_cost"] / df["total_drug_cost"]).round(4)

    df = df.drop(columns=["max_bene_count"])  # suppressed / non-additive, see docstring

    target = df[df["total_drug_cost"] >= config.MIN_VALUE_USD].copy()
    log(f"target universe (>= ${config.MIN_VALUE_USD:,}): {len(target):,} prescribers, "
        f"{target.total_drug_cost.sum() / df.total_drug_cost.sum():.1%} of value")
    unmapped = (target["region"] == "UNMAPPED").sum()
    assert unmapped == 0, f"{unmapped} target prescribers have unmapped cities"

    # value tiers -> call plan (workload)
    rank = target["total_drug_cost"].rank(ascending=False, method="first") / len(target)
    target["tier"] = "C"
    target.loc[rank <= config.TIER_A_TOP_PCT + config.TIER_B_NEXT_PCT, "tier"] = "B"
    target.loc[rank <= config.TIER_A_TOP_PCT, "tier"] = "A"
    target["calls"] = target["tier"].map(config.CALLS_PER_YEAR)
    target = target.rename(columns={"total_drug_cost": "value"})
    target = target.sort_values("npi").reset_index(drop=True)
    return df, target
