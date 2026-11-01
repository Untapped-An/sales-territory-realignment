"""
frontier.py — the balance-versus-disruption frontier.

Every account moved to a new rep breaks a relationship. So instead of one
"optimal" realignment, we trace how much balance and revenue capture each
level of disruption buys: re-run the rebalance with a hard cap on moves
(cap_pct of all target accounts) and record the outcome at each cap.
"""
import pandas as pd
import config
from src import model as m


def run(acc, reps, base):
    rows = []
    for cap in config.CAP_PCT_GRID:
        assign, moves = m.rebalance(acc, reps, base, max_moves=int(cap / 100 * len(acc)))
        e = m.evaluate(acc, assign, reps, baseline=base)
        rows.append({
            "cap_pct": cap,
            "moves_used": moves,
            "disruption_pct_actual": round(100 * e["disruption_pct"], 2),
            "disruption_value_pct": round(100 * e["disruption_value_pct"], 2),
            "load_stddev": round(e["load_std"], 1),
            "potential_stddev": round(e["potential_std"], 0),
            "excess_calls": int(e["excess_calls"]),
            "reps_over_capacity": e["reps_over_capacity"],
            "captured_hard_pct": round(100 * e["captured_hard_pct"], 2),
            "captured_smooth_pct": round(100 * e["captured_smooth_pct"], 2),
        })
    return pd.DataFrame(rows)
