"""
FastAPI Backend — Dynamic Churn Risk Simulator
All REST API endpoints for activity ingestion, risk queries, and overrides.

Run from the project root:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Import database using the correct package path
from app.db import database as db

# ─── APP INIT ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Dynamic Churn Risk Simulator",
    description="Real-time, multi-tenant churn intelligence API using Bayesian + Markov logic.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── SCHEMAS ─────────────────────────────────────────────────────────────────

class ActivityPayload(BaseModel):
    company_id:      int   = Field(..., description="Company identifier")
    user_id:         int   = Field(..., description="User identifier")
    logins:          int   = Field(..., ge=0, description="Number of logins today")
    time_spent_mins: float = Field(..., ge=0, description="Minutes spent in app")
    pages_visited:   int   = Field(0,  ge=0)
    support_tickets: int   = Field(0,  ge=0)


class OverridePayload(BaseModel):
    user_id:     int   = Field(..., description="User to override")
    forced_prob: float = Field(..., ge=0.0, le=1.0, description="Forced probability [0–1]")
    reason:      str   = Field("Admin override", description="Reason for override")


# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """System health check."""
    return {"status": "ok", "service": "Churn Risk Simulator v1.0"}


@app.post("/ingest_activity")
def ingest_activity(payload: ActivityPayload):
    """
    Ingest new user activity and dynamically update churn risk.
    Triggers Bayesian update + Markov state transition.
    """
    result = db.ingest_activity(
        user_id=payload.user_id,
        company_id=payload.company_id,
        logins=payload.logins,
        time_spent=payload.time_spent_mins,
        pages=payload.pages_visited,
        tickets=payload.support_tickets,
    )
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {
        "user_id":        result.user_id,
        "previous_prob":  result.previous_prob,
        "updated_prob":   result.updated_prob,
        "previous_state": result.previous_state,
        "new_state":      result.new_state,
        "state_changed":  result.state_changed,
        "alert_triggered":result.alert_triggered,
        "factors":        result.factors,
        "timestamp":      result.timestamp,
    }


@app.get("/user/{user_id}/risk")
def get_user_risk(user_id: int):
    """Return current churn risk and state for a specific user."""
    user = db.get_user_risk(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@app.get("/user/{user_id}/history")
def get_user_history(user_id: int):
    """Return full churn score history for a user."""
    history = db.get_user_history(user_id)
    return history.to_dict(orient="records")


@app.get("/company/{company_id}/high-risk")
def get_high_risk_users(
    company_id: int,
    threshold: float = Query(0.60, ge=0.0, le=1.0, description="Risk threshold"),
):
    """
    Return all high-risk users for a company above the given threshold.
    Multi-tenant: each company only sees their own users.
    """
    df = db.get_high_risk_users(company_id=company_id, threshold=threshold)
    return df.to_dict(orient="records")


@app.get("/company/{company_id}/summary")
def get_company_summary(company_id: int):
    """Return KPI summary for a specific company."""
    df = db.get_company_summary(company_id=company_id)
    return df.to_dict(orient="records")


@app.get("/companies/summary")
def get_all_companies_summary():
    """Return KPI summary for ALL companies (admin view)."""
    df = db.get_company_summary()
    return df.to_dict(orient="records")


@app.post("/manual_override")
def manual_override(payload: OverridePayload):
    """
    Admin override — manually set a user's churn probability.
    Use when you have external context the model doesn't.
    """
    result = db.manual_override(
        user_id=payload.user_id,
        forced_prob=payload.forced_prob,
        reason=payload.reason,
    )
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {
        "user_id":    result.user_id,
        "new_prob":   result.updated_prob,
        "new_state":  result.new_state,
        "reason":     payload.reason,
        "timestamp":  result.timestamp,
    }


@app.get("/analytics/churn-trend")
def churn_trend(
    company_id: Optional[int] = Query(None),
    freq: str = Query("M", description="Frequency: D=daily, W=weekly, M=monthly"),
):
    """Return average churn probability trend over time."""
    df = db.get_churn_trend(company_id=company_id, freq=freq)
    return df.to_dict(orient="records")


@app.get("/analytics/state-distribution")
def state_distribution(company_id: Optional[int] = Query(None)):
    """Return state distribution over time."""
    df = db.get_state_distribution_over_time(company_id=company_id)
    df["date"] = df["date"].astype(str)
    return df.to_dict(orient="records")
