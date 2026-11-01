"""Run sql/territory_analysis.sql against SQLite (in memory) and print each result."""
import sqlite3
import pandas as pd

con = sqlite3.connect(":memory:")
pd.read_csv("data/clean/accounts.csv").to_sql("accounts", con, index=False)
pd.read_csv("data/clean/reps.csv").to_sql("reps", con, index=False)

sql = open("sql/territory_analysis.sql").read()
blocks = [b.strip() for b in sql.split(";") if b.strip()]
for block in blocks:
    title = next((l for l in block.splitlines() if l.startswith("-- Q")), "query")
    body = "\n".join(l for l in block.splitlines() if not l.strip().startswith("--"))
    print("\n" + title)
    print(pd.read_sql_query(body, con).to_string(index=False))
