"""
Seed Script: Loads generated CSV data into SQLite database.
Uses only stdlib sqlite3 + pandas (no sqlalchemy required).

Run from the project root:
    python scripts/seed_db.py
"""

import sqlite3, os, pandas as pd

# Both paths are relative to the project root (one level up from scripts/)
DB_PATH  = os.path.join(os.path.dirname(__file__), '..', 'churn_simulator.db')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY, name TEXT, industry TEXT, plan TEXT);
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, company_id INTEGER, email TEXT,
            user_type TEXT, join_date TEXT, current_state TEXT DEFAULT 'Active',
            churn_prob REAL DEFAULT 0.10, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS user_activity (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, company_id INTEGER, date TEXT,
            logins INTEGER DEFAULT 0, time_spent_mins REAL DEFAULT 0.0,
            pages_visited INTEGER DEFAULT 0, support_tickets INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS churn_scores (
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, company_id INTEGER, date TEXT,
            churn_probability REAL, state TEXT,
            logins_that_day INTEGER DEFAULT 0, time_spent_mins REAL DEFAULT 0.0);
        CREATE INDEX IF NOT EXISTS idx_cs_user ON churn_scores(user_id);
        CREATE INDEX IF NOT EXISTS idx_cs_co   ON churn_scores(company_id);
        CREATE INDEX IF NOT EXISTS idx_ua_user ON user_activity(user_id);
    """)
    conn.commit()
    print("✅ Tables created.")

    configs = [
        ("companies",    "companies.csv",    None),
        ("users",        "users.csv",        {"initial_churn_prob":"churn_prob"}),
        ("user_activity","user_activity.csv",None),
        ("churn_scores", "churn_scores.csv", None),
    ]

    for table, fname, rename in configs:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count > 0:
            print(f"⏭  {table}: {count:,} rows exist, skipping."); continue

        df = pd.read_csv(os.path.join(DATA_DIR, fname))
        if rename: df = df.rename(columns=rename)
        if table == "users":
            df = df[["user_id","company_id","email","user_type","join_date","current_state","churn_prob"]]

        for i in range(0, len(df), 10_000):
            df.iloc[i:i+10_000].to_sql(table, conn, if_exists="append", index=False)
            print(f"  {table}: {min(i+10_000,len(df)):,}/{len(df):,}", end="\r")
        conn.commit()
        print(f"\n✅ Seeded {len(df):,} rows → {table}")

    conn.close()
    print("\n🎉 Database ready!")

if __name__ == "__main__":
    seed()
