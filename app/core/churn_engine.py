"""
Core Churn Logic Engine
- Bayesian Belief Updating
- Markov State Transitions
- Risk Scoring & Alerting
"""

from dataclasses import dataclass
from typing import Literal
from datetime import datetime

# ─── STATE DEFINITIONS ───────────────────────────────────────────────────────
UserState = Literal["Active", "At Risk", "Churned"]

# Markov transition thresholds
STATE_THRESHOLDS = {
    "Active":   (0.00, 0.44),
    "At Risk":  (0.45, 0.74),
    "Churned":  (0.75, 1.00),
}

ALERT_THRESHOLD = 0.90  # Fire alert if risk > 90%


@dataclass
class ActivityEvent:
    user_id: int
    company_id: int
    logins: int
    time_spent_mins: float
    pages_visited: int = 0
    support_tickets: int = 0
    date: str = ""


@dataclass
class RiskResult:
    user_id: int
    previous_prob: float
    updated_prob: float
    previous_state: UserState
    new_state: UserState
    state_changed: bool
    alert_triggered: bool
    factors: dict
    timestamp: str


# ─── BAYESIAN UPDATE ENGINE ──────────────────────────────────────────────────
class BayesianUpdater:
    """
    Updates churn probability using new behavioral evidence.
    
    Formula: P(churn | evidence) ∝ P(evidence | churn) × P(churn)
    Simplified as rule-based likelihood adjustments (transparent & explainable).
    """

    @staticmethod
    def compute_likelihood_adjustments(event: ActivityEvent) -> dict:
        """Returns a dict of factors and their probability adjustments."""
        factors = {}

        # ── LOGIN SIGNAL ──────────────────────────────────────
        if event.logins == 0:
            factors["no_login"]       = +0.15   # strong churn signal
        elif event.logins == 1:
            factors["low_login"]      = +0.05
        elif event.logins == 2:
            factors["moderate_login"] = -0.02
        elif event.logins >= 4:
            factors["high_login"]     = -0.08   # strong retention signal
        else:
            factors["normal_login"]   = -0.04

        # ── TIME SPENT SIGNAL ─────────────────────────────────
        if event.time_spent_mins == 0:
            factors["no_time_spent"]   = +0.10
        elif event.time_spent_mins < 10:
            factors["low_engagement"]  = +0.05
        elif event.time_spent_mins > 45:
            factors["high_engagement"] = -0.06
        elif event.time_spent_mins > 25:
            factors["good_engagement"] = -0.03

        # ── PAGE VISITS SIGNAL ────────────────────────────────
        if event.pages_visited == 0 and event.logins > 0:
            factors["no_pages_despite_login"] = +0.04
        elif event.pages_visited > 10:
            factors["deep_exploration"] = -0.03

        # ── SUPPORT TICKETS (frustration signal) ─────────────
        if event.support_tickets >= 2:
            factors["multiple_support_tickets"] = +0.06
        elif event.support_tickets == 1:
            factors["one_support_ticket"] = +0.02

        return factors

    @classmethod
    def update(cls, prior: float, event: ActivityEvent) -> tuple[float, dict]:
        """Apply Bayesian update: prior + likelihood adjustments → posterior."""
        factors = cls.compute_likelihood_adjustments(event)
        delta = sum(factors.values())
        posterior = round(min(0.95, max(0.01, prior + delta)), 4)
        return posterior, factors


# ─── MARKOV STATE MACHINE ─────────────────────────────────────────────────────
class MarkovStateMachine:
    """
    Models user state transitions:
      Active ↔ At Risk → Churned
    
    Churned is a terminal (absorbing) state.
    """

    @staticmethod
    def get_state_from_prob(prob: float) -> UserState:
        if prob < 0.45:
            return "Active"
        elif prob < 0.75:
            return "At Risk"
        else:
            return "Churned"

    @classmethod
    def transition(cls, current_state: UserState, new_prob: float) -> UserState:
        """Apply transition rules — Churned is absorbing."""
        if current_state == "Churned":
            return "Churned"   # Cannot recover once churned
        return cls.get_state_from_prob(new_prob)


# ─── MAIN CHURN ENGINE ────────────────────────────────────────────────────────
class ChurnEngine:
    """
    Orchestrates the full pipeline:
    1. Receive activity event
    2. Bayesian update → new probability
    3. Markov transition → new state
    4. Check alert threshold
    """

    def __init__(self):
        self.bayesian  = BayesianUpdater()
        self.markov    = MarkovStateMachine()

    def process_event(
        self,
        event: ActivityEvent,
        prior_prob: float,
        current_state: UserState,
    ) -> RiskResult:
        """Full pipeline: event → updated risk result."""

        # Step 1: Bayesian update
        new_prob, factors = self.bayesian.update(prior_prob, event)

        # Step 2: Markov state transition
        new_state = self.markov.transition(current_state, new_prob)

        # Step 3: Alert check
        alert = new_prob >= ALERT_THRESHOLD

        result = RiskResult(
            user_id=event.user_id,
            previous_prob=prior_prob,
            updated_prob=new_prob,
            previous_state=current_state,
            new_state=new_state,
            state_changed=(current_state != new_state),
            alert_triggered=alert,
            factors=factors,
            timestamp=datetime.utcnow().isoformat(),
        )

        if alert:
            self._fire_alert(result)

        return result

    def manual_override(
        self,
        user_id: int,
        forced_prob: float,
        current_state: UserState,
        reason: str = "Admin override",
    ) -> RiskResult:
        """Allow admin to manually set churn probability."""
        forced_prob = round(min(0.95, max(0.01, forced_prob)), 4)
        new_state = self.markov.transition(current_state, forced_prob)

        return RiskResult(
            user_id=user_id,
            previous_prob=forced_prob,
            updated_prob=forced_prob,
            previous_state=current_state,
            new_state=new_state,
            state_changed=(current_state != new_state),
            alert_triggered=forced_prob >= ALERT_THRESHOLD,
            factors={"manual_override": 0.0, "reason": reason},
            timestamp=datetime.utcnow().isoformat(),
        )

    @staticmethod
    def _fire_alert(result: RiskResult):
        """Simulated proactive alert — replace with Slack/Webhook in prod."""
        print(
            f"🚨 ALERT | User {result.user_id} | "
            f"Risk: {result.updated_prob:.0%} | "
            f"State: {result.new_state} | "
            f"Time: {result.timestamp}"
        )


# Singleton instance
engine = ChurnEngine()
