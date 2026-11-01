# RESULTS — every quotable number, with the assumption it rests on

Rule: never quote a number from this project without the caveat beside it.
All figures come from `python run_all.py` (seed 7, fully reproducible).

## Data (real — CMS Medicare Part D, Ohio, 2014, oral anticoagulants)

| Number | Caveat |
|---|---|
| 7,759 Ohio prescribers, $58.7M Medicare anticoagulant drug cost | Medicare Part D only (not commercial); 2014 data; rivaroxaban, apixaban, warfarin |
| Top 6.8% of prescribers = 50% of value; top 21.5% = 80% | Measured on Part D drug cost, all 7,759 prescribers |
| 3,282 target prescribers (≥ $2,500/yr) hold 95.6% of value; 57.7% of prescribers hold 4.4% | $2,500 coverage threshold is an assumption |
| Cardiology = 22% of target prescribers but 48.5% of value | Specialty grouped from 57 raw CMS labels into 6 buckets |
| 65 city records had spelling variants fixed; prescriber–drug rows < 11 claims are absent from the public file | CMS suppression; light prescribers are under-represented |

## Baseline vs full realignment (45 reps, 5 regions)

| Number | Caveat |
|---|---|
| Workload CV 37% → 2%; std dev of rep call load 307 → 16 calls (−95%) | Baseline territory map is SYNTHETIC (legacy-drift model); workload = planned calls by value tier (24/12/6 per year) |
| Total excess calls 5,772 → 1,420 (−75%) | Capacity assumed 800 calls/rep/yr on this brand |
| Reps over capacity 27 → 40 (the old metric says it got WORSE) | Same capacity assumption; this is the magnitude-blind finding |
| Value captured 84.5% → 96.2% (+11.7 pts, ≈ $6.6M) under hard-cutoff model | Response curve assumed, not estimated |
| Value captured 85.8% → 89.1% (+3.3 pts, ≈ $1.8M) under smooth model | λ = 2.303 (90% capture at capacity); the conservative figure to quote |
| Full realignment moved 22.1% of accounts but only 7.9% of value | Lowest-value-first move rule |
| 0 of 328 top-decile accounts moved; 3 of 656 Tier A accounts moved; 68% of moves came from the bottom 3 value deciles | Same rule |

## Balance–disruption frontier

| Number | Caveat |
|---|---|
| 10% move cap (3.6% of value): load spread −56%, delivers 48% (hard) – 69% (smooth) of the full capture uplift | Greedy heuristic, not a global optimum |
| 15% move cap (5.5% of value): 74% (hard) – 87% (smooth) of the full uplift | Same |
| The share of benefit bought early depends on the response curve — the smooth curve front-loads it | Both curves reported side by side |

## Sales-force sizing

| Number | Caveat |
|---|---|
| Profit-maximising headcount = 50 / 56 / 65 reps at rep cost $160k / $120k / $80k (franchise share) vs 45 today | Contribution margin 70% of Part D cost; cost charged to franchise = 50% of fully loaded rep cost |
| Under-sized at every cost level tested; but profit is flat near the peak (+0.5% to +3.4% vs 45 reps) | Direction is robust, exact N is not |

## Capacity sensitivity

| Number | Caveat |
|---|---|
| Realignment improves capture at every capacity tested (500–1,200 calls) under both curves: +1.6 to +11.7 pts | Uplift is largest when the force is near 100% utilised |
