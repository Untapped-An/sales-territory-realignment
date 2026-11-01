"""
sizing.py — is 45 reps the right number?

For each headcount N: allocate reps to regions in proportion to call load,
build a balanced alignment from scratch (a design question, so no
disruption cap), and compute captured value under the smooth curve.

    contribution = captured_value * CONTRIBUTION_MARGIN
    profit       = contribution - N * cost_per_rep

Rep cost is not known, so it is swept at three levels (config.COST_LEVELS).
The honest output is how the optimum moves with cost, not a single
confident number.
"""
import pandas as pd
import config
from src import model as m


def run(acc):
    total = acc["value"].sum()
    rows = []
    for n in config.SIZING_RANGE:
        reps = m.make_reps(acc, n)
        e = m.evaluate(acc, m.build_from_scratch(acc, reps), reps)
        rows.append({"n_reps": n, "captured_value": e["captured_smooth_pct"] * total})
    curve = pd.DataFrame(rows)
    curve["contribution"] = curve["captured_value"] * config.CONTRIBUTION_MARGIN

    out = []
    for level, cost in config.COST_LEVELS.items():
        c = curve.copy()
        c["cost_level"] = level
        c["cost_per_rep"] = round(cost, 0)
        c["total_cost"] = c["n_reps"] * cost
        c["profit"] = c["contribution"] - c["total_cost"]
        out.append(c)
    df = pd.concat(out, ignore_index=True)
    for col in ["captured_value", "contribution", "total_cost", "profit"]:
        df[col] = df[col].round(0)
    return df[["n_reps", "cost_level", "cost_per_rep", "captured_value",
               "contribution", "total_cost", "profit"]]


def optimum(df):
    return df.loc[df.groupby("cost_level")["profit"].idxmax()].set_index("cost_level")
