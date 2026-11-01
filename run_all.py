"""
run_all.py — one command, end to end.

    python run_all.py

Reads data/clean/prescribers_raw_query.csv (the BigQuery extract), builds
the target universe, the synthetic legacy map, the full realignment, the
balance-disruption frontier, the sizing curve and the capacity sensitivity,
then writes Tableau-ready CSVs + sanity-check PNGs to out/ and runs the
acceptance checks.
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from src.clean import load_universe
from src import model as m, frontier, sizing, sensitivity

os.makedirs("out", exist_ok=True)
os.makedirs("data/clean", exist_ok=True)


def pareto_share(values, share):
    v = np.sort(np.asarray(values))[::-1]
    c = v.cumsum() / v.sum()
    return (int((c < share).sum()) + 1) / len(v)


def main():
    raw, acc = load_universe()
    reps = m.make_reps(acc, config.BASELINE_REPS)
    base = m.drifted_baseline(acc, reps)
    full, full_moves = m.rebalance(acc, reps, base)
    before = m.evaluate(acc, base, reps)
    after = m.evaluate(acc, full, reps, baseline=base)

    # ------------------------------------------------ tidy data for SQL / Tableau
    accounts = acc[["npi", "specialty", "specialty_group", "city", "region", "value",
                    "total_claims", "brand_cost", "generic_cost", "brand_share",
                    "tier", "calls"]].copy()
    accounts["original_rep_id"] = base.values
    accounts["rebalanced_rep_id"] = full.values
    accounts.to_csv("data/clean/accounts.csv", index=False)
    reps.to_csv("data/clean/reps.csv", index=False)

    tb, ta = m.rep_table(acc, base, reps), m.rep_table(acc, full, reps)
    cmp_ = pd.DataFrame({
        "rep_id": tb.index, "region": tb["region"],
        "accounts_before": tb["accounts"].astype(int), "accounts_after": ta["accounts"].astype(int),
        "calls_before": tb["load"].astype(int), "calls_after": ta["load"].astype(int),
        "potential_before": tb["potential"].round(0), "potential_after": ta["potential"].round(0),
        "over_capacity_before": (tb["load"] > config.CAPACITY_CALLS).astype(int),
        "over_capacity_after": (ta["load"] > config.CAPACITY_CALLS).astype(int),
    })
    cmp_.to_csv("out/alignment_compare.csv", index=False)

    moved = accounts[accounts.original_rep_id != accounts.rebalanced_rep_id].copy()
    moved["value_decile"] = pd.qcut(acc["value"].rank(method="first"), 10, labels=range(1, 11)).astype(int)[moved.index]
    moved.rename(columns={"original_rep_id": "from_rep", "rebalanced_rep_id": "to_rep"})[
        ["npi", "region", "specialty_group", "value", "tier", "value_decile", "from_rep", "to_rep"]
    ].to_csv("out/moved_accounts.csv", index=False)

    fr = frontier.run(acc, reps, base)
    fr.to_csv("out/frontier.csv", index=False)
    sz = sizing.run(acc)
    sz.to_csv("out/sizing.csv", index=False)
    opt = sizing.optimum(sz)
    se = sensitivity.run(acc, reps, base, full)
    se.to_csv("out/capacity_sensitivity.csv", index=False)

    seg = (accounts.groupby("specialty_group")
           .agg(prescribers=("npi", "size"), value=("value", "sum"))
           .assign(value_share_pct=lambda d: (100 * d.value / d.value.sum()).round(1))
           .sort_values("value", ascending=False))
    seg.to_csv("out/specialty_summary.csv")

    # ------------------------------------------------ headline numbers
    def at(cap, col):
        return fr.loc[fr.cap_pct == cap, col].item()
    h = {
        "raw_prescribers": len(raw),
        "target_prescribers": len(acc),
        "target_value_share_pct": round(100 * acc.value.sum() / raw.total_drug_cost.sum(), 1),
        "nontarget_prescribers_pct": round(100 * (1 - len(acc) / len(raw)), 1),
        "total_value_usd": round(raw.total_drug_cost.sum()),
        "pareto_50_pct_of_prescribers": round(100 * pareto_share(raw.total_drug_cost, 0.5), 1),
        "pareto_80_pct_of_prescribers": round(100 * pareto_share(raw.total_drug_cost, 0.8), 1),
        "total_calls": int(acc.calls.sum()),
        "capacity_total": config.BASELINE_REPS * config.CAPACITY_CALLS,
        "reps": config.BASELINE_REPS,
        "before": {k: round(float(v), 4) for k, v in before.items()},
        "after": {k: round(float(v), 4) for k, v in after.items()},
        "full_moves": full_moves,
        "load_std_reduction_pct": round(100 * (1 - after["load_std"] / before["load_std"]), 1),
        "excess_reduction_pct": round(100 * (1 - after["excess_calls"] / before["excess_calls"]), 1),
        "frontier_10pct": {c: at(10, c) for c in ["load_stddev", "captured_hard_pct",
                                                  "captured_smooth_pct", "disruption_value_pct"]},
        "frontier_20pct": {c: at(20, c) for c in ["load_stddev", "captured_hard_pct",
                                                  "captured_smooth_pct", "disruption_value_pct"]},
        "sizing_optimum": {lvl: {"n_reps": int(r.n_reps), "cost_per_rep": float(r.cost_per_rep),
                                 "profit": float(r.profit)} for lvl, r in opt.iterrows()},
    }
    with open("out/headline.json", "w") as f:
        json.dump(h, f, indent=2)

    # ------------------------------------------------ sanity-check charts
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(fr.disruption_pct_actual, fr.load_stddev, "o-")
    ax[0].set(xlabel="% of accounts moved", ylabel="Std dev of rep call load", title="Balance vs disruption")
    ax[1].plot(fr.disruption_pct_actual, fr.captured_hard_pct, "o-", label="hard cutoff")
    ax[1].plot(fr.disruption_pct_actual, fr.captured_smooth_pct, "s-", label="smooth")
    ax[1].set(xlabel="% of accounts moved", ylabel="% of value captured", title="Capture vs disruption")
    ax[1].legend(); fig.tight_layout(); fig.savefig("out/frontier.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for lvl, g in sz.groupby("cost_level"):
        ax.plot(g.n_reps, g.profit / 1e6, label=f"{lvl} cost")
        ax.scatter(opt.loc[lvl, "n_reps"], opt.loc[lvl, "profit"] / 1e6)
    ax.axvline(config.BASELINE_REPS, ls="--", c="grey")
    ax.set(xlabel="Reps", ylabel="Profit ($M)", title="Sales force sizing"); ax.legend()
    fig.tight_layout(); fig.savefig("out/sizing.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist([cmp_.calls_before, cmp_.calls_after], bins=15, label=["before", "after"])
    ax.axvline(config.CAPACITY_CALLS, ls="--", c="k")
    ax.set(xlabel="Annual calls per rep", ylabel="Reps", title="Rep workload before vs after"); ax.legend()
    fig.tight_layout(); fig.savefig("out/load_distribution.png", dpi=120); plt.close(fig)

    # ------------------------------------------------ acceptance checks
    checks = {
        "cap 0 => zero disruption and baseline spread":
            fr.loc[0, "disruption_pct_actual"] == 0 and abs(fr.loc[0, "load_stddev"] - before["load_std"]) < 0.1,
        "spread non-increasing as cap rises": bool((fr.load_stddev.diff().dropna() <= 1e-9).all()),
        "captured never exceeds potential": bool((fr[["captured_hard_pct", "captured_smooth_pct"]] <= 100).all().all()),
        "accounts never cross regions": bool((acc.region.values == base.map(reps.set_index("rep_id").region).values).all()
                                             and (acc.region.values == full.map(reps.set_index("rep_id").region).values).all()),
        "every target account assigned": bool(full.notna().all()),
    }
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    assert all(checks.values())

    print(json.dumps(h, indent=2))


if __name__ == "__main__":
    main()
