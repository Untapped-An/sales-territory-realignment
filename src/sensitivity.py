"""
sensitivity.py — does the conclusion survive a different capacity assumption?

Capacity (calls per rep per year on this brand) is asserted, not measured.
Re-run baseline vs full realignment at several capacities, under both
capture curves, and check whether the realignment ever stops helping.
The territory map itself does not depend on capacity, only its evaluation.
"""
import pandas as pd
import config
from src import model as m


def run(acc, reps, base, full):
    rows = []
    for cap in config.CAPACITY_GRID:
        b = m.evaluate(acc, base, reps, capacity=cap)
        a = m.evaluate(acc, full, reps, capacity=cap)
        for model in ["hard", "smooth"]:
            k = f"captured_{model}_pct"
            rows.append({
                "capacity_calls": cap,
                "utilisation_pct": round(100 * acc["calls"].sum() / (cap * len(reps)), 1),
                "model": model,
                "captured_before_pct": round(100 * b[k], 2),
                "captured_after_pct": round(100 * a[k], 2),
                "uplift_pts": round(100 * (a[k] - b[k]), 2),
            })
    return pd.DataFrame(rows)
