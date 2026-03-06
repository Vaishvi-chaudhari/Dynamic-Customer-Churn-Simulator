"""
Database Layer — Pure SQLite3 (no extra dependencies needed)
Handles all DB operations for the Churn Risk Simulator
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime

# DB is placed at the project root (two levels up from app/db/)
DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "churn_simulator.db")
)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # Fixed: safe for FastAPI threads
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id   INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            industry     TEXT,
            plan         TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id         INTEGER PRIMARY KEY,
            company_id      INTEGER NOT NULL,
            email           TEXT,
            user_type       TEXT,
            join_date       TEXT,
            current_state   TEXT DEFAULT 'Active',
            churn_prob      REAL DEFAULT 0.10,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(company_id)
        );

        CREATE TABLE IF NOT EXISTS user_activity (
            activity_id      INTEGER PRIMARY KEY,
            user_id          INTEGER NOT NULL,
            company_id       INTEGER NOT NULL,
            date             TEXT,
            logins           INTEGER DEFAULT 0,
            time_spent_mins  REAL DEFAULT 0.0,
            pages_visited    INTEGER DEFAULT 0,
            support_tickets  INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS churn_scores (
            score_id           INTEGER PRIMARY KEY,
            user_id            INTEGER NOT NULL,
            company_id         INTEGER NOT NULL,
            date               TEXT,
            churn_probability  REAL,
            state              TEXT,
            logins_that_day    INTEGER DEFAULT 0,
            time_spent_mins    REAL DEFAULT 0.0,
            created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_churn_user     ON churn_scores(user_id);
        CREATE INDEX IF NOT EXISTS idx_churn_company  ON churn_scores(company_id);
        CREATE INDEX IF NOT EXISTS idx_churn_date     ON churn_scores(date);
        CREATE INDEX IF NOT EXISTS idx_activity_user  ON user_activity(user_id);
    """)
    conn.commit()
    conn.close()
    print("✅ DB tables initialised.")


def seed_from_csv(data_dir: str):
    """Load all CSVs into the SQLite database."""
    conn = get_conn()

    tables = {
        "companies":    "companies.csv",
        "users":        "users.csv",
        "user_activity":"user_activity.csv",
        "churn_scores": "churn_scores.csv",
    }

    for table, fname in tables.items():
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count > 0:
            print(f"⏭  {table} already seeded ({count} rows), skipping.")
            continue

        path = os.path.join(data_dir, fname)
        df   = pd.read_csv(path)

        # Column alignment for users table
        if table == "users":
            df = df.rename(columns={"initial_churn_prob": "churn_prob"})
            df = df[["user_id","company_id","email","user_type","join_date","current_state","churn_prob"]]

        BATCH = 10_000
        for i in range(0, len(df), BATCH):
            df.iloc[i:i+BATCH].to_sql(table, conn, if_exists="append", index=False)
            print(f"  {table}: {min(i+BATCH, len(df))} / {len(df)}", end="\r")

        print(f"\n✅ Seeded {len(df):,} rows → {table}")

    conn.close()
    print("\n🎉 Seeding complete!")


# ─── QUERY HELPERS ───────────────────────────────────────────────────────────

def get_companies():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM companies ORDER BY company_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company_summary(company_id: int = None):
    """Returns latest-state summary per company (or all companies)."""
    conn = get_conn()
    where = f"WHERE cs.company_id = {company_id}" if company_id else ""
    sql = f"""
        SELECT
            c.name AS company,
            cs.company_id,
            COUNT(DISTINCT cs.user_id)                        AS total_users,
            SUM(CASE WHEN cs.state='Active'   THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN cs.state='At Risk'  THEN 1 ELSE 0 END) AS at_risk,
            SUM(CASE WHEN cs.state='Churned'  THEN 1 ELSE 0 END) AS churned,
            ROUND(AVG(cs.churn_probability),4)                AS avg_risk
        FROM churn_scores cs
        JOIN companies c ON c.company_id = cs.company_id
        JOIN (
            SELECT user_id, MAX(date) AS max_date
            FROM churn_scores
            GROUP BY user_id
        ) latest ON cs.user_id = latest.user_id AND cs.date = latest.max_date
        {where}
        GROUP BY cs.company_id
        ORDER BY avg_risk DESC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df


def get_user_risk(user_id: int):
    conn = get_conn()
    row = conn.execute("""
        SELECT u.user_id, u.company_id, u.email, u.current_state, u.churn_prob,
               u.join_date, u.user_type
        FROM users u WHERE u.user_id = ?
    """, (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_history(user_id: int):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT date, churn_probability, state, logins_that_day, time_spent_mins
        FROM churn_scores
        WHERE user_id = ?
        ORDER BY date
    """, conn, params=(user_id,))
    conn.close()
    return df


def get_high_risk_users(company_id: int = None, threshold: float = 0.60):
    conn = get_conn()
    where = f"AND cs.company_id = {company_id}" if company_id else ""
    df = pd.read_sql_query(f"""
        SELECT u.user_id, u.email, c.name AS company, cs.state,
               cs.churn_probability, cs.date AS last_updated,
               u.join_date
        FROM churn_scores cs
        JOIN users u  ON u.user_id  = cs.user_id
        JOIN companies c ON c.company_id = cs.company_id
        JOIN (
            SELECT user_id, MAX(date) AS max_date
            FROM churn_scores GROUP BY user_id
        ) latest ON cs.user_id = latest.user_id AND cs.date = latest.max_date
        WHERE cs.churn_probability >= {threshold}
        {where}
        ORDER BY cs.churn_probability DESC
    """, conn)
    conn.close()
    return df


def get_churn_trend(company_id: int = None, freq: str = "M"):
    """Monthly average churn probability trend."""
    conn = get_conn()
    where = f"WHERE company_id = {company_id}" if company_id else ""
    df = pd.read_sql_query(f"""
        SELECT date, churn_probability, state, company_id
        FROM churn_scores {where}
    """, conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    trend = (
        df.groupby(pd.Grouper(key="date", freq=freq))["churn_probability"]
        .mean()
        .reset_index()
        .rename(columns={"churn_probability": "avg_churn_prob"})
    )
    return trend


def get_state_distribution_over_time(company_id: int = None):
    conn = get_conn()
    where = f"WHERE company_id = {company_id}" if company_id else ""
    df = pd.read_sql_query(f"""
        SELECT date, state, COUNT(*) AS count FROM churn_scores
        {where}
        GROUP BY date, state ORDER BY date
    """, conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def ingest_activity(user_id: int, company_id: int, logins: int,
                    time_spent: float, pages: int = 0, tickets: int = 0):
    """Insert new activity and update churn score."""
    from app.core.churn_engine import engine as churn_engine, ActivityEvent

    conn = get_conn()

    # Get current state
    row = conn.execute(
        "SELECT churn_prob, current_state FROM users WHERE user_id=?", (user_id,)
    ).fetchone()

    if not row:
        conn.close()
        return {"error": f"User {user_id} not found"}

    prior_prob, current_state = row["churn_prob"], row["current_state"]
    today = datetime.utcnow().strftime("%Y-%m-%d")

    event = ActivityEvent(
        user_id=user_id, company_id=company_id,
        logins=logins, time_spent_mins=time_spent,
        pages_visited=pages, support_tickets=tickets, date=today
    )
    result = churn_engine.process_event(event, prior_prob, current_state)

    # Save activity
    conn.execute("""
        INSERT INTO user_activity (user_id, company_id, date, logins,
                                   time_spent_mins, pages_visited, support_tickets)
        VALUES (?,?,?,?,?,?,?)
    """, (user_id, company_id, today, logins, time_spent, pages, tickets))

    # Save churn score
    conn.execute("""
        INSERT INTO churn_scores (user_id, company_id, date, churn_probability,
                                   state, logins_that_day, time_spent_mins)
        VALUES (?,?,?,?,?,?,?)
    """, (user_id, company_id, today, result.updated_prob,
          result.new_state, logins, time_spent))

    # Update user
    conn.execute("""
        UPDATE users SET churn_prob=?, current_state=?, updated_at=?
        WHERE user_id=?
    """, (result.updated_prob, result.new_state, today, user_id))

    conn.commit()
    conn.close()
    return result


def manual_override(user_id: int, forced_prob: float, reason: str = "Admin override"):
    from app.core.churn_engine import engine as churn_engine

    conn = get_conn()
    row = conn.execute(
        "SELECT current_state FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {"error": "User not found"}

    result = churn_engine.manual_override(user_id, forced_prob, row["current_state"], reason)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    conn.execute(
        "UPDATE users SET churn_prob=?, current_state=?, updated_at=? WHERE user_id=?",
        (result.updated_prob, result.new_state, today, user_id)
    )
    conn.commit()
    conn.close()
    return result
