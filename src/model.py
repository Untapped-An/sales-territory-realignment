"""
model.py — capture curves, metrics, baseline assignment and rebalancing.

Workload of a rep = sum of planned calls of the accounts they cover.
x = capacity / load  (> 1 means spare capacity)

Capture models (how much of an account's value a rep converts):
  hard   : min(1, x)                    — the original project's model
  smooth : 1 - exp(-LAMBDA * x)         — diminishing returns; 0.90 at x = 1

Under the hard model, an overloaded rep captures exactly `capacity` calls'
worth whatever the overload, so HOW overload is distributed does not matter —
only how much of it there is. Under the smooth model, concentrated overload
is worse than spread overload. Reporting both shows the conclusion does not
hinge on the functional form.
"""
import math
import numpy as np
import pandas as pd
import config


# ------------------------------------------------------------------ capture
def capture(x, model, lam=config.LAMBDA):
    x = np.asarray(x, dtype=float)
    if model == "hard":
        return np.minimum(1.0, x)
    if model == "smooth":
        return 1.0 - np.exp(-lam * x)
    raise ValueError(model)


# ------------------------------------------------------------------ metrics
def rep_table(acc, assign, reps, capacity=config.CAPACITY_CALLS):
    t = (acc.assign(rep_id=assign.values)
            .groupby("rep_id")
            .agg(load=("calls", "sum"), potential=("value", "sum"), accounts=("npi", "size")))
    t = reps.set_index("rep_id")[["region"]].join(t).fillna(0)
    t["x"] = np.where(t["load"] > 0, capacity / t["load"].clip(lower=1e-9), np.inf)
    return t


def evaluate(acc, assign, reps, baseline=None, capacity=config.CAPACITY_CALLS):
    t = rep_table(acc, assign, reps, capacity)
    x_of_acc = assign.map(t["x"]).values
    total = acc["value"].sum()
    out = {
        "load_std": t["load"].std(ddof=0),
        "load_cv": t["load"].std(ddof=0) / t["load"].mean(),
        "potential_std": t["potential"].std(ddof=0),
        "excess_calls": (t["load"] - capacity).clip(lower=0).sum(),
        "reps_over_capacity": int((t["load"] > capacity).sum()),
        "captured_hard_pct": (acc["value"].values * capture(x_of_acc, "hard")).sum() / total,
        "captured_smooth_pct": (acc["value"].values * capture(x_of_acc, "smooth")).sum() / total,
    }
    if baseline is not None:
        moved = assign.values != baseline.values
        median = acc["value"].median()
        above = acc["value"].values > median
        out.update({
            "disruption_pct": moved.mean(),
            "disruption_value_pct": acc["value"].values[moved].sum() / total,
            "tier_a_moved": int((moved & (acc["tier"].values == "A")).sum()),
            "above_median_moved": int((moved & above).sum()),
            "n_moved": int(moved.sum()),
        })
    return out


# ------------------------------------------------------------------ reps
def allocate_headcount(acc, n_reps):
    """Reps per region proportional to regional call load (largest remainder, min 1)."""
    load = acc.groupby("region")["calls"].sum().reindex(config.REGIONS)
    quota = load / load.sum() * n_reps
    base = np.maximum(1, np.floor(quota)).astype(int)
    rem = n_reps - base.sum()
    for r in (quota - np.floor(quota)).sort_values(ascending=False).index[:max(rem, 0)]:
        base[r] += 1
    return base


def make_reps(acc, n_reps):
    per_region = allocate_headcount(acc, n_reps)
    rows, k = [], 1
    for region in config.REGIONS:
        for _ in range(per_region[region]):
            rows.append({"rep_id": f"R{k:02d}", "region": region})
            k += 1
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ baseline (synthetic)
def drifted_baseline(acc, reps, sigma=config.DRIFT_SIGMA, seed=config.SEED):
    """Legacy territory map: within each region, every rep has a random 'pull'
    on accounts (lognormal weight), so some reps accumulated far more over the
    years. Accounts never cross regions. Synthetic by necessity — no company
    publishes who covers which doctor."""
    rng = np.random.default_rng(seed)
    assign = pd.Series(index=acc.index, dtype=object)
    for region in config.REGIONS:
        rids = reps.loc[reps.region == region, "rep_id"].to_numpy()
        w = rng.lognormal(0.0, sigma, size=len(rids))
        idx = acc.index[acc.region == region]
        assign.loc[idx] = rng.choice(rids, size=len(idx), p=w / w.sum())
    return assign


# ------------------------------------------------------------------ rebalance
def rebalance(acc, reps, start, max_moves=None):
    """Move-budgeted, region-constrained greedy rebalance.

    Each step, in every region, consider moving the LOWEST-VALUE account of
    the most-loaded rep to the least-loaded rep. Apply the single move that
    most reduces the sum of squared rep loads (equivalently, load variance).
    Stop when the move budget is spent or no move improves balance.

    Lowest-value-first is deliberate: it protects the relationships that
    matter most. max_moves=None means no budget (the full realignment).
    """
    assign = start.copy()
    calls = acc["calls"].to_dict()
    value = acc["value"].to_dict()
    budget = math.inf if max_moves is None else max_moves

    # per-rep account lists, kept sorted by value ascending
    books = {r: sorted(assign.index[assign == r], key=lambda i: value[i]) for r in reps.rep_id}
    load = {r: sum(calls[i] for i in books[r]) for r in reps.rep_id}
    by_region = {g: list(reps.loc[reps.region == g, "rep_id"]) for g in config.REGIONS}

    moves = 0
    while moves < budget:
        best = None
        for g, rids in by_region.items():
            a = max(rids, key=lambda r: load[r])
            b = min(rids, key=lambda r: load[r])
            if not books[a]:
                continue
            i = books[a][0]
            w = calls[i]
            gain = 2 * w * (load[a] - load[b] - w)
            if gain > 0 and (best is None or gain > best[0]):
                best = (gain, i, a, b)
        if best is None:
            break
        _, i, a, b = best
        books[a].pop(0)
        books[b].append(i)
        books[b].sort(key=lambda j: value[j])
        load[a] -= calls[i]
        load[b] += calls[i]
        assign.loc[i] = b
        moves += 1
    return assign, moves


def build_from_scratch(acc, reps):
    """Balanced design with no legacy: largest workloads first, each to the
    least-loaded rep in the account's region (LPT heuristic)."""
    assign = pd.Series(index=acc.index, dtype=object)
    for region in config.REGIONS:
        rids = list(reps.loc[reps.region == region, "rep_id"])
        load = {r: 0 for r in rids}
        sub = acc[acc.region == region].sort_values(["calls", "value"], ascending=False)
        for i, c in zip(sub.index, sub["calls"]):
            r = min(rids, key=lambda k: load[k])
            assign.loc[i] = r
            load[r] += c
    return assign
