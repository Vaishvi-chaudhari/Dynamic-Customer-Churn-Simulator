"""
Data Generator: Creates realistic synthetic CSV data for 2020-2026
Generates: companies, users, user_activity, churn_scores

Run from the project root:
    python scripts/generate_data.py
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

random.seed(42)
np.random.seed(42)

# Output goes to the data/ folder at the project root
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── COMPANIES ────────────────────────────────────────────────────────────────
companies_data = [
    {"company_id": 1, "name": "TechFlow SaaS",     "industry": "Software",      "plan": "Enterprise"},
    {"company_id": 2, "name": "RetailPulse",        "industry": "E-Commerce",    "plan": "Pro"},
    {"company_id": 3, "name": "EduLearn Platform",  "industry": "Education",     "plan": "Pro"},
    {"company_id": 4, "name": "HealthTrack App",    "industry": "Healthcare",    "plan": "Starter"},
    {"company_id": 5, "name": "FinanceEdge",        "industry": "Fintech",       "plan": "Enterprise"},
]
companies_df = pd.DataFrame(companies_data)
companies_df.to_csv(os.path.join(OUTPUT_DIR, "companies.csv"), index=False)
print(f"✅ companies.csv → {len(companies_df)} records")

# ─── USERS ────────────────────────────────────────────────────────────────────
user_types = ["loyal", "at_risk", "churner"]
user_type_weights = [0.50, 0.30, 0.20]

users = []
user_id = 1
for company in companies_data:
    n_users = random.randint(80, 150)
    for _ in range(n_users):
        utype = random.choices(user_types, weights=user_type_weights)[0]
        join_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 365*4))
        users.append({
            "user_id": user_id,
            "company_id": company["company_id"],
            "user_type": utype,
            "join_date": join_date.strftime("%Y-%m-%d"),
            "email": f"user{user_id}@{company['name'].lower().replace(' ','')}.com",
            "current_state": "Active" if utype == "loyal" else ("At Risk" if utype == "at_risk" else "Churned"),
            "initial_churn_prob": round(
                random.uniform(0.05, 0.20) if utype == "loyal" else
                random.uniform(0.40, 0.65) if utype == "at_risk" else
                random.uniform(0.75, 0.95), 4
            )
        })
        user_id += 1

users_df = pd.DataFrame(users)
users_df.to_csv(os.path.join(OUTPUT_DIR, "users.csv"), index=False)
print(f"✅ users.csv → {len(users_df)} records")

# ─── USER ACTIVITY ────────────────────────────────────────────────────────────
START_DATE = datetime(2020, 1, 1)
END_DATE   = datetime(2026, 6, 30)
TOTAL_DAYS = (END_DATE - START_DATE).days

def generate_logins(user_type, day_offset, total_days):
    """Simulate login behavior by user type over time."""
    progress = day_offset / total_days
    if user_type == "loyal":
        base = random.randint(2, 6)
        noise = random.randint(-1, 1)
        return max(1, base + noise)
    elif user_type == "at_risk":
        decay = max(0, 1 - progress * 1.2)
        base = int(random.randint(1, 4) * decay)
        return max(0, base + random.randint(-1, 0))
    else:  # churner
        if progress < 0.4:
            return random.randint(1, 3)
        elif progress < 0.65:
            return random.randint(0, 1)
        else:
            return 0

def generate_time_spent(logins, user_type):
    """Time spent in minutes based on logins."""
    if logins == 0:
        return 0.0
    base_per_login = 25 if user_type == "loyal" else 15 if user_type == "at_risk" else 10
    return round(logins * base_per_login + random.uniform(-10, 10), 2)

activity_records = []
activity_id = 1

# Sample activity every 3-7 days per user (not every single day — realistic)
for _, user in users_df.iterrows():
    uid = user["user_id"]
    utype = user["user_type"]
    join = datetime.strptime(user["join_date"], "%Y-%m-%d")
    
    current_date = max(join, START_DATE)
    day_offset = 0
    
    while current_date <= END_DATE:
        logins = generate_logins(utype, day_offset, TOTAL_DAYS)
        time_spent = generate_time_spent(logins, utype)
        
        pages_visited = max(0, int(logins * random.uniform(2.5, 5.0)))
        support_tickets = random.choices([0, 1, 2], weights=[0.85, 0.12, 0.03])[0]
        
        activity_records.append({
            "activity_id": activity_id,
            "user_id": uid,
            "company_id": user["company_id"],
            "date": current_date.strftime("%Y-%m-%d"),
            "logins": logins,
            "time_spent_mins": time_spent,
            "pages_visited": pages_visited,
            "support_tickets": support_tickets,
        })
        activity_id += 1
        
        # Step forward 3-7 days
        current_date += timedelta(days=random.randint(3, 7))
        day_offset += random.randint(3, 7)

activity_df = pd.DataFrame(activity_records)
activity_df.to_csv(os.path.join(OUTPUT_DIR, "user_activity.csv"), index=False)
print(f"✅ user_activity.csv → {len(activity_df)} records")

# ─── CHURN SCORES (computed via Bayesian logic) ───────────────────────────────
def bayesian_update(prior, logins, time_spent):
    prob = prior
    if logins == 0:
        prob += 0.15
    elif logins >= 4:
        prob -= 0.08
    elif logins >= 2:
        prob -= 0.04
    else:
        prob += 0.05

    if time_spent == 0:
        prob += 0.10
    elif time_spent > 40:
        prob -= 0.05
    elif time_spent < 10:
        prob += 0.05

    return round(min(0.95, max(0.01, prob)), 4)

def get_state(prob, current_state):
    if current_state == "Churned":
        return "Churned"
    if prob >= 0.75:
        return "Churned"
    elif prob >= 0.45:
        return "At Risk"
    else:
        return "Active"

churn_scores = []
score_id = 1

for _, user in users_df.iterrows():
    uid = user["user_id"]
    user_acts = activity_df[activity_df["user_id"] == uid].sort_values("date")
    
    prob = user["initial_churn_prob"]
    state = user["current_state"]
    
    for _, act in user_acts.iterrows():
        prob = bayesian_update(prob, act["logins"], act["time_spent_mins"])
        state = get_state(prob, state)
        
        churn_scores.append({
            "score_id": score_id,
            "user_id": uid,
            "company_id": user["company_id"],
            "date": act["date"],
            "churn_probability": prob,
            "state": state,
            "logins_that_day": act["logins"],
            "time_spent_mins": act["time_spent_mins"],
        })
        score_id += 1

churn_df = pd.DataFrame(churn_scores)
churn_df.to_csv(os.path.join(OUTPUT_DIR, "churn_scores.csv"), index=False)
print(f"✅ churn_scores.csv → {len(churn_df)} records")

# ─── SUMMARY STATS ───────────────────────────────────────────────────────────
print("\n📊 Dataset Summary:")
print(f"   Companies  : {len(companies_df)}")
print(f"   Users      : {len(users_df)}")
print(f"   Activities : {len(activity_df)}")
print(f"   Churn Scores: {len(churn_df)}")
print(f"\n   State distribution:")
latest = churn_df.sort_values("date").groupby("user_id").last()
print(latest["state"].value_counts().to_string())
