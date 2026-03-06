# 📉 Dynamic Churn Risk Simulator

> **Real-time, multi-tenant churn intelligence using Bayesian Belief Updating + Markov Chains**

---

## 🎯 What This Is

A production-ready backend service that predicts **customer churn in real-time** for subscription businesses.
Instead of static ML models, it uses **transparent probabilistic logic** — easy to explain, easy to audit.

---

## 🧠 How The Intelligence Works

```
User Activity Event
       │
       ▼
┌─────────────────────────────┐
│   Bayesian Updater          │
│   prior + likelihood        │
│   ─────────────────────     │
│   logins=0   → +15% risk    │
│   logins≥4   → -8%  risk    │
│   time>45m   → -6%  risk    │
│   tickets≥2  → +6%  risk    │
└──────────┬──────────────────┘
           │ posterior probability
           ▼
┌─────────────────────────────┐
│   Markov State Machine      │
│   prob < 0.45  → Active     │
│   prob < 0.75  → At Risk    │
│   prob ≥ 0.75  → Churned ✗  │
└──────────┬──────────────────┘
           │
           ▼
     Risk Score + State
     Alert if prob ≥ 0.90
```

---

## 🚀 Quick Start

### Option A — Local (3 commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate data & seed database
bash setup.sh

# 3. Launch dashboard
streamlit run streamlit_app/dashboard.py
```

Dashboard → http://localhost:8501

### Option B — Docker (1 command)

```bash
docker-compose up --build
```

- Dashboard → http://localhost:8501
- API Docs  → http://localhost:8000/docs

---

## 📂 Project Structure

```
churn_simulator/
├── app/
│   ├── core/
│   │   └── churn_engine.py      ← Bayesian + Markov logic
│   ├── db/
│   │   ├── models.py            ← SQLAlchemy ORM models
│   │   └── database.py          ← SQLite3 query layer
│   └── main.py                  ← FastAPI REST API
│
├── streamlit_app/
│   └── dashboard.py             ← Full 5-page Streamlit dashboard
│
├── scripts/
│   ├── generate_data.py         ← Synthetic data generator (2020–2026)
│   └── seed_db.py               ← Database seeder
│
├── data/                        ← Generated CSV files
│   ├── companies.csv
│   ├── users.csv
│   ├── user_activity.csv
│   └── churn_scores.csv
│
├── setup.sh                     ← One-command setup
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/health` | Health check |
| POST   | `/ingest_activity` | Ingest activity → Bayesian update |
| GET    | `/user/{id}/risk` | Get current user risk |
| GET    | `/user/{id}/history` | Full churn score history |
| GET    | `/company/{id}/high-risk` | High-risk users list |
| GET    | `/company/{id}/summary` | Company KPIs |
| GET    | `/companies/summary` | All companies (admin) |
| POST   | `/manual_override` | Admin risk override |
| GET    | `/analytics/churn-trend` | Avg risk over time |
| GET    | `/analytics/state-distribution` | State distribution over time |

### Example: Ingest Activity

```bash
curl -X POST http://localhost:8000/ingest_activity \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": 1,
    "user_id": 5,
    "logins": 0,
    "time_spent_mins": 0,
    "pages_visited": 0,
    "support_tickets": 0
  }'
```

Response:
```json
{
  "user_id": 5,
  "previous_prob": 0.12,
  "updated_prob": 0.37,
  "previous_state": "Active",
  "new_state": "At Risk",
  "state_changed": true,
  "alert_triggered": false,
  "factors": {"no_login": 0.15, "no_time_spent": 0.10},
  "timestamp": "2026-03-06T10:45:00"
}
```

---

## 📊 Dashboard Pages

| Page | What You See |
|------|-------------|
| 🏠 Overview | KPIs, donut chart, company comparison |
| 📊 Churn Trends | Monthly trend, state over time, YoY comparison |
| 🚨 High-Risk Users | Filterable alert table, critical user list |
| 👤 User Deep Dive | Per-user probability, logins, state timeline |
| ⚙️ Live Simulator | Run Bayesian updates in real-time, manual override |

---

## 🗃️ Dataset (Auto-Generated)

- **596 users** across 5 companies
- **192,819 activity records** spanning 2020–2026
- **3 behavioral profiles**: Loyal (50%), At Risk (30%), Churner (20%)
- Realistic decay/growth patterns over time

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Python 3.11 |
| Churn Logic | Custom Bayesian + Markov (pure Python) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Dashboard | Streamlit + Plotly |
| Deployment | Docker + AWS EC2/RDS or Render |

---

## 🎤 Interview Answer

> *"I built a real-time churn risk simulator deployed as a backend service. The system models how users transition between engagement states — Active, At Risk, Churned — using Markov chains, and updates churn probability dynamically using Bayesian logic whenever new behavior data arrives. It's designed as a multi-company platform so any product can send user activity and receive real-time churn risk insights with a Streamlit dashboard for business stakeholders."*
