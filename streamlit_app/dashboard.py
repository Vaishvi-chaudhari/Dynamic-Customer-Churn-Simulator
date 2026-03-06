"""
Dynamic Churn Risk Simulator — Streamlit Dashboard
Professional multi-page dashboard replacing Power BI
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add project root to path so app.* imports work if needed
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Churn Risk Simulator",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# DB is at the project root (two levels up from streamlit_app/)
DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "churn_simulator.db")
)

# ─── HIGH-CONTRAST TECH PALETTE ─────────────────────────────────────────────
# Deep space navy base  ·  Electric cyan primary  ·  Neon state signals
COLORS = {
    "Active":   "#00FF88",   # Neon mint-green
    "At Risk":  "#FFD600",   # Electric amber
    "Churned":  "#FF2D55",   # Hot crimson
    "primary":  "#00E5FF",   # Electric cyan
    "accent2":  "#BF5FFF",   # Violet laser
    "bg_dark":  "#020B18",   # Deep space
    "bg_card":  "#071428",   # Dark navy card
    "bg_surface": "#0B1E38", # Elevated surface
    "border":   "#00E5FF",   # Cyan border glow
    "text":     "#E8F4FD",   # Near-white
    "text_dim": "#6B8CAE",   # Muted slate
    "grid":     "#0E2440",   # Subtle grid
}

STATE_COLOR_MAP = {
    "Active":  COLORS["Active"],
    "At Risk": COLORS["At Risk"],
    "Churned": COLORS["Churned"],
}

# ─── HIGH-CONTRAST TECH STYLES ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #020B18;
        color: #E8F4FD;
    }
    .stApp {
        background-color: #020B18;
        background-image:
            linear-gradient(rgba(0,229,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,229,255,0.025) 1px, transparent 1px);
        background-size: 40px 40px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: 1px solid #334155;
    }
    
    /* ── Metric Cards ─────────────────────────────────────── */
    .metric-card {
        background: linear-gradient(145deg, #071428 0%, #0B1E38 100%);
        border: 1px solid rgba(0,229,255,0.20);
        border-radius: 10px;
        padding: 20px 24px;
        margin: 4px 0;
        position: relative;
        overflow: hidden;
        transition: border-color 0.25s, box-shadow 0.25s;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00E5FF, transparent);
        opacity: 0.6;
    }
    .metric-card:hover {
        border-color: rgba(0,229,255,0.55);
        box-shadow: 0 0 18px rgba(0,229,255,0.12);
    }
    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        font-family: 'Share Tech Mono', monospace;
        line-height: 1;
        margin: 6px 0 4px 0;
        letter-spacing: -0.5px;
    }
    .metric-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #6B8CAE;
        font-weight: 600;
        font-family: 'Rajdhani', sans-serif;
    }
    .metric-delta {
        font-size: 0.78rem;
        font-family: 'Share Tech Mono', monospace;
        margin-top: 6px;
        opacity: 0.85;
    }

    /* ── State Badges ─────────────────────────────────────── */
    .badge-active  { color: #00FF88; background: rgba(0,255,136,0.12);
                     border: 1px solid rgba(0,255,136,0.35);
                     padding: 3px 10px; border-radius: 4px; font-size: 0.72rem;
                     font-weight: 700; font-family: 'Share Tech Mono', monospace;
                     letter-spacing: 1px; text-transform: uppercase; }
    .badge-atrisk  { color: #FFD600; background: rgba(255,214,0,0.10);
                     border: 1px solid rgba(255,214,0,0.35);
                     padding: 3px 10px; border-radius: 4px; font-size: 0.72rem;
                     font-weight: 700; font-family: 'Share Tech Mono', monospace;
                     letter-spacing: 1px; text-transform: uppercase; }
    .badge-churned { color: #FF2D55; background: rgba(255,45,85,0.12);
                     border: 1px solid rgba(255,45,85,0.35);
                     padding: 3px 10px; border-radius: 4px; font-size: 0.72rem;
                     font-weight: 700; font-family: 'Share Tech Mono', monospace;
                     letter-spacing: 1px; text-transform: uppercase; }

    /* ── Section Headers ──────────────────────────────────── */
    .section-header {
        font-size: 0.75rem;
        font-weight: 700;
        font-family: 'Rajdhani', sans-serif;
        color: #00E5FF;
        letter-spacing: 3px;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(0,229,255,0.18);
        padding-bottom: 10px;
        margin: 24px 0 16px 0;
    }

    /* ── Alert Banners ────────────────────────────────────── */
    .alert-banner {
        background: linear-gradient(90deg, rgba(255,45,85,0.12), rgba(255,45,85,0.04));
        border: 1px solid rgba(255,45,85,0.35);
        border-left: 3px solid #FF2D55;
        border-radius: 6px;
        padding: 11px 16px;
        margin: 8px 0;
        font-size: 0.82rem;
        font-family: 'Share Tech Mono', monospace;
        box-shadow: 0 0 12px rgba(255,45,85,0.08);
    }

    /* ── Plotly chart backgrounds ─────────────────────────── */
    .js-plotly-plot .plotly, .js-plotly-plot .plotly .svg-container {
        background: transparent !important;
    }

    /* ── Streamlit component overrides ───────────────────── */
    div[data-testid="stMetric"] {
        background: #071428;
        border: 1px solid rgba(0,229,255,0.18);
        border-radius: 10px;
        padding: 16px;
    }
    .stSelectbox > div > div {
        background: #0B1E38 !important;
        border-color: rgba(0,229,255,0.25) !important;
        color: #E8F4FD !important;
    }
    .stSlider > div { color: #E8F4FD; }
    .stTabs [data-baseweb="tab-list"] {
        background: #071428;
        border-bottom: 1px solid rgba(0,229,255,0.18);
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #6B8CAE;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        letter-spacing: 1px;
        font-size: 0.85rem;
        padding: 8px 20px;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #00E5FF !important;
        border-bottom: 2px solid #00E5FF !important;
        background: rgba(0,229,255,0.06) !important;
    }
    h1 { color: #E8F4FD !important;
         font-family: 'Rajdhani', sans-serif !important;
         font-weight: 700 !important;
         letter-spacing: 1px !important; }
    h2, h3 { color: #E8F4FD !important; font-family: 'Rajdhani', sans-serif !important; }
    .stDataFrame { background: #071428 !important; }
    .dataframe { font-size: 0.80rem !important; font-family: 'Share Tech Mono', monospace !important; }
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input {
        background: #0B1E38 !important;
        border-color: rgba(0,229,255,0.25) !important;
        color: #E8F4FD !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    [data-baseweb="radio"] label { color: #E8F4FD !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #020B18; }
    ::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,229,255,0.6); }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── DB HELPERS ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data(ttl=30)
def load_companies():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM companies ORDER BY company_id", conn)
    conn.close()
    return df

@st.cache_data(ttl=30)
def load_company_summary():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT c.name AS company, cs.company_id,
               COUNT(DISTINCT cs.user_id)                            AS total_users,
               SUM(CASE WHEN cs.state='Active'  THEN 1 ELSE 0 END)  AS active,
               SUM(CASE WHEN cs.state='At Risk' THEN 1 ELSE 0 END)  AS at_risk,
               SUM(CASE WHEN cs.state='Churned' THEN 1 ELSE 0 END)  AS churned,
               ROUND(AVG(cs.churn_probability),4)                    AS avg_risk
        FROM churn_scores cs
        JOIN companies c ON c.company_id = cs.company_id
        JOIN (SELECT user_id, MAX(date) AS max_date FROM churn_scores GROUP BY user_id) l
          ON cs.user_id = l.user_id AND cs.date = l.max_date
        GROUP BY cs.company_id ORDER BY avg_risk DESC
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=30)
def load_high_risk(company_id=None, threshold=0.60):
    conn = sqlite3.connect(DB_PATH)
    where = f"AND cs.company_id = {company_id}" if company_id else ""
    df = pd.read_sql(f"""
        SELECT u.user_id, u.email, c.name AS company, cs.state,
               ROUND(cs.churn_probability,4) AS churn_probability,
               cs.date AS last_updated, u.join_date, u.user_type
        FROM churn_scores cs
        JOIN users u ON u.user_id = cs.user_id
        JOIN companies c ON c.company_id = cs.company_id
        JOIN (SELECT user_id, MAX(date) AS max_date FROM churn_scores GROUP BY user_id) l
          ON cs.user_id = l.user_id AND cs.date = l.max_date
        WHERE cs.churn_probability >= {threshold} {where}
        ORDER BY cs.churn_probability DESC
        LIMIT 500
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_churn_trend(company_id=None):
    conn = sqlite3.connect(DB_PATH)
    where = f"WHERE company_id = {company_id}" if company_id else ""
    df = pd.read_sql(f"""
        SELECT date, churn_probability, state FROM churn_scores {where}
    """, conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    monthly = (df.groupby(pd.Grouper(key="date", freq="M"))["churn_probability"]
               .mean().reset_index()
               .rename(columns={"churn_probability": "avg_churn_prob"}))
    return monthly

@st.cache_data(ttl=60)
def load_state_over_time(company_id=None):
    conn = sqlite3.connect(DB_PATH)
    where = f"WHERE company_id = {company_id}" if company_id else ""
    df = pd.read_sql(f"""
        SELECT date, state, COUNT(*) AS count
        FROM churn_scores {where}
        GROUP BY date, state ORDER BY date
    """, conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    monthly = (df.groupby([pd.Grouper(key="date", freq="M"), "state"])["count"]
               .sum().reset_index())
    return monthly

@st.cache_data(ttl=30)
def load_user_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT date, churn_probability, state, logins_that_day, time_spent_mins
        FROM churn_scores WHERE user_id = ? ORDER BY date
    """, conn, params=(user_id,))
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data(ttl=30)
def load_users_for_company(company_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT user_id, email, current_state, churn_prob, join_date, user_type
        FROM users WHERE company_id = ? ORDER BY churn_prob DESC
    """, conn, params=(company_id,))
    conn.close()
    return df

def update_user_churn(user_id, new_prob, reason):
    """Manual override — writes to DB."""
    conn = sqlite3.connect(DB_PATH)
    new_state = "Churned" if new_prob >= 0.75 else ("At Risk" if new_prob >= 0.45 else "Active")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn.execute("UPDATE users SET churn_prob=?, current_state=?, updated_at=? WHERE user_id=?",
                 (new_prob, new_state, today, user_id))
    conn.execute("""INSERT INTO churn_scores (user_id, company_id, date, churn_probability, state)
                    SELECT ?, company_id, ?, ?, ? FROM users WHERE user_id=?""",
                 (user_id, today, new_prob, new_state, user_id))
    conn.commit()
    conn.close()
    load_user_history.clear()
    load_high_risk.clear()
    return new_state

def ingest_new_activity(user_id, company_id, logins, time_spent, pages, tickets):
    """Bayesian update + insert."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT churn_prob, current_state FROM users WHERE user_id=?",
                       (user_id,)).fetchone()
    if not row:
        conn.close()
        return None

    prior, state = row[0], row[1]
    if state == "Churned":
        conn.close()
        return {"error": "Churned users cannot be updated."}

    # Bayesian update
    prob = prior
    factors = {}
    if logins == 0:         prob += 0.15; factors["No logins"] = "+15%"
    elif logins >= 4:       prob -= 0.08; factors["High logins"] = "-8%"
    elif logins >= 2:       prob -= 0.04; factors["Moderate logins"] = "-4%"
    else:                   prob += 0.05; factors["Low logins"] = "+5%"

    if time_spent == 0:     prob += 0.10; factors["No time spent"] = "+10%"
    elif time_spent > 45:   prob -= 0.06; factors["High engagement"] = "-6%"
    elif time_spent < 10:   prob += 0.05; factors["Low engagement"] = "+5%"

    if tickets >= 2:        prob += 0.06; factors["Multiple tickets"] = "+6%"
    if pages > 10:          prob -= 0.03; factors["Deep exploration"] = "-3%"

    new_prob = round(min(0.95, max(0.01, prob)), 4)
    new_state = "Churned" if new_prob >= 0.75 else ("At Risk" if new_prob >= 0.45 else "Active")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    conn.execute("""INSERT INTO user_activity (user_id, company_id, date, logins,
                    time_spent_mins, pages_visited, support_tickets)
                    VALUES (?,?,?,?,?,?,?)""",
                 (user_id, company_id, today, logins, time_spent, pages, tickets))
    conn.execute("""INSERT INTO churn_scores (user_id, company_id, date, churn_probability,
                    state, logins_that_day, time_spent_mins)
                    VALUES (?,?,?,?,?,?,?)""",
                 (user_id, company_id, today, new_prob, new_state, logins, time_spent))
    conn.execute("UPDATE users SET churn_prob=?, current_state=?, updated_at=? WHERE user_id=?",
                 (new_prob, new_state, today, user_id))
    conn.commit()
    conn.close()

    load_user_history.clear()
    load_high_risk.clear()
    load_company_summary.clear()

    return {"prior": prior, "posterior": new_prob, "state": new_state, "factors": factors,
            "alert": new_prob >= 0.90}


# ─── CHART HELPERS ────────────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(2,11,24,0.85)",          # #020B18 with slight opacity
    font=dict(family="Share Tech Mono", color="#6B8CAE", size=11),
    margin=dict(l=10, r=10, t=34, b=10),
    xaxis=dict(
        gridcolor="#0E2440",
        linecolor="rgba(0,229,255,0.20)",
        tickcolor="#6B8CAE",
        showgrid=True,
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor="#0E2440",
        linecolor="rgba(0,229,255,0.20)",
        tickcolor="#6B8CAE",
        showgrid=True,
        zeroline=False,
    ),
    legend=dict(
        bgcolor="rgba(7,20,40,0.85)",
        bordercolor="rgba(0,229,255,0.20)",
        borderwidth=1,
        font=dict(color="#E8F4FD", size=11),
    ),
)

def styled_chart(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📉 Churn Risk\n### Simulator")
    st.markdown("---")

    companies = load_companies()
    company_options = {"All Companies": None}
    company_options.update({row["name"]: row["company_id"] for _, row in companies.iterrows()})

    selected_company_name = st.selectbox("🏢 Select Company", list(company_options.keys()))
    selected_company_id   = company_options[selected_company_name]

    st.markdown("---")
    page = st.radio("📄 Navigation", [
        "🏠 Overview",
        "📊 Churn Trends",
        "🚨 High-Risk Users",
        "👤 User Deep Dive",
        "⚙️ Live Simulator",
    ])
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.7rem; color:#475569; text-align:center;'>"
        "Bayesian + Markov Engine<br>Multi-Tenant Platform<br>"
        f"<b style='color:#6366f1'>{datetime.now().strftime('%b %d, %Y')}</b>"
        "</div>",
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Overview":
    st.title("📉 Churn Risk Simulator")
    st.markdown(
        "<p style='color:#64748b; margin-top:-12px;'>Real-time Bayesian + Markov churn intelligence platform</p>",
        unsafe_allow_html=True
    )

    summary = load_company_summary()

    if selected_company_id:
        data = summary[summary["company_id"] == selected_company_id]
    else:
        data = summary

    total_users = int(data["total_users"].sum())
    total_active  = int(data["active"].sum())
    total_at_risk = int(data["at_risk"].sum())
    total_churned = int(data["churned"].sum())
    avg_risk = data["avg_risk"].mean()

    churn_rate = total_churned / total_users * 100 if total_users else 0
    risk_rate  = total_at_risk / total_users * 100 if total_users else 0

    # KPI Row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Total Users</div>
            <div class='metric-value' style='color:#6366f1'>{total_users:,}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Active</div>
            <div class='metric-value' style='color:#22c55e'>{total_active:,}</div>
            <div class='metric-delta' style='color:#22c55e'>{total_active/total_users*100:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>At Risk</div>
            <div class='metric-value' style='color:#f59e0b'>{total_at_risk:,}</div>
            <div class='metric-delta' style='color:#f59e0b'>{risk_rate:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Churned</div>
            <div class='metric-value' style='color:#ef4444'>{total_churned:,}</div>
            <div class='metric-delta' style='color:#ef4444'>{churn_rate:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        risk_color = "#ef4444" if avg_risk > 0.6 else "#f59e0b" if avg_risk > 0.4 else "#22c55e"
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Avg Churn Risk</div>
            <div class='metric-value' style='color:{risk_color}'>{avg_risk:.1%}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: Donut + Company bar
    col_left, col_right = st.columns([1, 1.6])

    with col_left:
        st.markdown("<div class='section-header'>User State Distribution</div>", unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=["Active", "At Risk", "Churned"],
            values=[total_active, total_at_risk, total_churned],
            hole=0.65,
            marker_colors=[COLORS["Active"], COLORS["At Risk"], COLORS["Churned"]],
            textinfo="percent",
            textfont=dict(size=13, color="white"),
        ))
        fig_donut.update_layout(
            **PLOTLY_LAYOUT,
            showlegend=True,
            height=280,
            annotations=[dict(text=f"{churn_rate:.0f}%<br><span style='font-size:10px'>churn</span>",
                               x=0.5, y=0.5, font=dict(size=18, color="white"), showarrow=False)],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        st.markdown("<div class='section-header'>Company Risk Comparison</div>", unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Active",  x=summary["company"], y=summary["active"],
                                  marker_color=COLORS["Active"],  opacity=0.85))
        fig_bar.add_trace(go.Bar(name="At Risk", x=summary["company"], y=summary["at_risk"],
                                  marker_color=COLORS["At Risk"], opacity=0.85))
        fig_bar.add_trace(go.Bar(name="Churned", x=summary["company"], y=summary["churned"],
                                  marker_color=COLORS["Churned"],opacity=0.85))
        fig_bar.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=280,
                               xaxis_tickangle=-15)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Company table
    st.markdown("<div class='section-header'>Company KPI Summary</div>", unsafe_allow_html=True)
    display = summary.copy()
    display["churn_rate"] = (display["churned"] / display["total_users"] * 100).round(1).astype(str) + "%"
    display["avg_risk"]   = (display["avg_risk"] * 100).round(1).astype(str) + "%"
    display = display[["company","total_users","active","at_risk","churned","churn_rate","avg_risk"]]
    display.columns = ["Company","Total Users","Active","At Risk","Churned","Churn Rate","Avg Risk"]
    st.dataframe(display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — CHURN TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Churn Trends":
    st.title("📊 Churn Trends & Analytics")

    trend = load_churn_trend(selected_company_id)
    state_time = load_state_over_time(selected_company_id)

    # Monthly churn probability trend
    st.markdown("<div class='section-header'>Average Churn Probability Over Time</div>", unsafe_allow_html=True)
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend["date"], y=trend["avg_churn_prob"],
        mode="lines", name="Avg Churn Risk",
        line=dict(color=COLORS["primary"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.12)",
    ))
    fig_trend.add_hline(y=0.60, line_dash="dash", line_color=COLORS["At Risk"],
                        annotation_text="At Risk threshold", annotation_position="top right")
    fig_trend.add_hline(y=0.75, line_dash="dash", line_color=COLORS["Churned"],
                        annotation_text="Churn threshold", annotation_position="top right")
    fig_trend.update_layout(**PLOTLY_LAYOUT, height=320,
                             yaxis_tickformat=".0%", yaxis_range=[0, 1])
    st.plotly_chart(fig_trend, use_container_width=True)

    # State over time
    st.markdown("<div class='section-header'>User State Distribution Over Time</div>", unsafe_allow_html=True)
    # Helper: convert #rrggbb to rgba(r,g,b,alpha)
    def hex_to_rgba(hex_color, alpha=0.55):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig_area = go.Figure()
    for state in ["Active", "At Risk", "Churned"]:
        sdata = state_time[state_time["state"] == state]
        fig_area.add_trace(go.Scatter(
            x=sdata["date"], y=sdata["count"],
            name=state, stackgroup="one", mode="lines",
            line=dict(color=STATE_COLOR_MAP[state], width=0.5),
            fillcolor=hex_to_rgba(STATE_COLOR_MAP[state]),
        ))
    fig_area.update_layout(**PLOTLY_LAYOUT, height=320)
    st.plotly_chart(fig_area, use_container_width=True)

    # Year-over-year comparison
    st.markdown("<div class='section-header'>Year-over-Year Churn Risk</div>", unsafe_allow_html=True)
    trend["year"]  = trend["date"].dt.year
    trend["month"] = trend["date"].dt.strftime("%b")
    MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    trend["month_num"] = trend["date"].dt.month

    fig_yoy = go.Figure()
    for year in sorted(trend["year"].unique()):
        y_data = trend[trend["year"] == year].sort_values("month_num")
        fig_yoy.add_trace(go.Scatter(
            x=y_data["month"], y=y_data["avg_churn_prob"],
            name=str(year), mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=5),
        ))
    # Filter out xaxis/yaxis from PLOTLY_LAYOUT to avoid duplicate kwarg error
    yoy_layout = {k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")}
    fig_yoy.update_layout(
        **yoy_layout, height=300,
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER, gridcolor="#1e293b"),
        yaxis=dict(tickformat=".0%", gridcolor="#1e293b"),
    )
    st.plotly_chart(fig_yoy, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — HIGH RISK USERS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🚨 High-Risk Users":
    st.title("🚨 High-Risk User Monitor")

    col1, col2 = st.columns([1, 2])
    with col1:
        threshold = st.slider("Risk Threshold", 0.30, 0.95, 0.60, 0.05,
                               format="%.0f%%",
                               help="Show users with churn probability above this value")
    with col2:
        st.markdown(f"""
        <div style='padding:12px; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3);
                    border-radius:8px; margin-top:8px;'>
        ⚠️ Users above <b style='color:#ef4444'>{threshold:.0%}</b> risk threshold are displayed.
        Risk ≥ 90% triggers automatic alerts in production.
        </div>
        """, unsafe_allow_html=True)

    df = load_high_risk(selected_company_id, threshold)

    if df.empty:
        st.success(f"✅ No users above {threshold:.0%} risk threshold!")
    else:
        # Summary counts
        m1, m2, m3 = st.columns(3)
        crit = df[df["churn_probability"] >= 0.90]
        at_risk_count = df[df["state"] == "At Risk"]

        with m1:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>High Risk Users</div>
                <div class='metric-value' style='color:#f59e0b'>{len(df):,}</div>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>Critical (≥90%)</div>
                <div class='metric-value' style='color:#ef4444'>{len(crit):,}</div>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>Companies Affected</div>
                <div class='metric-value' style='color:#6366f1'>{df['company'].nunique()}</div>
            </div>""", unsafe_allow_html=True)

        # Critical alerts
        if len(crit) > 0:
            st.markdown("<div class='section-header'>🔴 Critical Alerts (Risk ≥ 90%)</div>",
                        unsafe_allow_html=True)
            for _, row in crit.head(5).iterrows():
                st.markdown(f"""<div class='alert-banner'>
                    🚨 <b>User {row['user_id']}</b> ({row['email']}) — 
                    <b style='color:#ef4444'>{row['churn_probability']:.1%} risk</b> — 
                    {row['company']} — Last seen: {row['last_updated']}
                </div>""", unsafe_allow_html=True)

        st.markdown("<div class='section-header'>All High-Risk Users</div>", unsafe_allow_html=True)

        # Risk distribution chart
        fig_hist = px.histogram(df, x="churn_probability", nbins=30,
                                 color_discrete_sequence=[COLORS["primary"]])
        # Build layout without duplicate 'margin' key (PLOTLY_LAYOUT already has margin)
        hist_layout = {k: v for k, v in PLOTLY_LAYOUT.items() if k != "margin"}
        hist_layout["margin"] = dict(l=10, r=10, t=10, b=10)
        fig_hist.update_layout(**hist_layout, height=200,
                                xaxis_tickformat=".0%", showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)

        # Table
        disp = df.copy()
        disp["churn_probability"] = (disp["churn_probability"] * 100).round(1).astype(str) + "%"
        st.dataframe(disp, use_container_width=True, hide_index=True,
                     column_config={
                         "churn_probability": st.column_config.TextColumn("Churn Risk"),
                         "state": st.column_config.TextColumn("State"),
                     })


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — USER DEEP DIVE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "👤 User Deep Dive":
    st.title("👤 Individual User Analysis")

    if selected_company_id:
        users_df = load_users_for_company(selected_company_id)
        user_options = {f"#{r['user_id']} — {r['email']} ({r['current_state']})": r["user_id"]
                        for _, r in users_df.iterrows()}
    else:
        conn = sqlite3.connect(DB_PATH)
        users_df = pd.read_sql("SELECT user_id, email, current_state, churn_prob FROM users LIMIT 200", conn)
        conn.close()
        user_options = {f"#{r['user_id']} — {r['email']}": r["user_id"]
                        for _, r in users_df.iterrows()}

    if not user_options:
        st.warning("No users found. Please select a company.")
    else:
        selected_label = st.selectbox("Select User", list(user_options.keys()))
        user_id = user_options[selected_label]

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Fixed: needed for dict(row) conversion
        user_row = conn.execute("""
            SELECT u.*, c.name AS company_name
            FROM users u JOIN companies c ON c.company_id = u.company_id
            WHERE u.user_id = ?
        """, (user_id,)).fetchone()
        conn.close()

        if user_row:
            user_row = dict(user_row)
            state = user_row["current_state"]
            state_color = STATE_COLOR_MAP.get(state, "#94a3b8")

            # User info cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>Company</div>
                    <div class='metric-value' style='color:#6366f1; font-size:1.2rem'>{user_row['company_name']}</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>Current State</div>
                    <div class='metric-value' style='color:{state_color}; font-size:1.4rem'>{state}</div>
                </div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>Churn Probability</div>
                    <div class='metric-value' style='color:{state_color}'>{user_row['churn_prob']:.1%}</div>
                </div>""", unsafe_allow_html=True)
            with col4:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>Member Since</div>
                    <div class='metric-value' style='color:#94a3b8; font-size:1.1rem'>{user_row['join_date']}</div>
                </div>""", unsafe_allow_html=True)

            # History
            history = load_user_history(user_id)
            if not history.empty:
                st.markdown("<div class='section-header'>Churn Probability Over Time</div>",
                            unsafe_allow_html=True)

                fig_user = go.Figure()
                fig_user.add_trace(go.Scatter(
                    x=history["date"], y=history["churn_probability"],
                    mode="lines", name="Churn Probability",
                    line=dict(color=COLORS["primary"], width=2),
                    fill="tozeroy", fillcolor="rgba(99,102,241,0.10)",
                ))

                # Color background by state
                for threshold_val, color, label in [
                    (0.45, "rgba(245,158,11,0.06)", "At Risk zone"),
                    (0.75, "rgba(239,68,68,0.06)",  "Churn zone"),
                ]:
                    fig_user.add_hrect(y0=threshold_val, y1=1.0,
                                       fillcolor=color, line_width=0,
                                       annotation_text=label,
                                       annotation_position="top right")

                fig_user.update_layout(**PLOTLY_LAYOUT, height=300,
                                       yaxis_tickformat=".0%", yaxis_range=[0, 1])
                st.plotly_chart(fig_user, use_container_width=True)

                # Logins & time spent
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown("<div class='section-header'>Daily Logins</div>", unsafe_allow_html=True)
                    fig_log = px.bar(history, x="date", y="logins_that_day",
                                     color_discrete_sequence=[COLORS["primary"]])
                    fig_log.update_layout(**PLOTLY_LAYOUT, height=220, showlegend=False)
                    st.plotly_chart(fig_log, use_container_width=True)

                with col_r:
                    st.markdown("<div class='section-header'>Time Spent (mins)</div>", unsafe_allow_html=True)
                    fig_time = px.area(history, x="date", y="time_spent_mins",
                                       color_discrete_sequence=["#22c55e"])
                    fig_time.update_layout(**PLOTLY_LAYOUT, height=220, showlegend=False)
                    st.plotly_chart(fig_time, use_container_width=True)

                # State timeline
                st.markdown("<div class='section-header'>State Transitions</div>", unsafe_allow_html=True)
                state_map = {"Active": 0, "At Risk": 1, "Churned": 2}
                history["state_num"] = history["state"].map(state_map)
                fig_state = go.Figure(go.Scatter(
                    x=history["date"], y=history["state"],
                    mode="lines+markers",
                    line=dict(color=COLORS["primary"], width=2),
                    marker=dict(
                        color=[STATE_COLOR_MAP.get(s, "#94a3b8") for s in history["state"]],
                        size=6
                    )
                ))
                # Filter out yaxis from PLOTLY_LAYOUT to avoid duplicate kwarg error
                state_layout = {k: v for k, v in PLOTLY_LAYOUT.items() if k != "yaxis"}
                fig_state.update_layout(
                    **state_layout, height=200,
                    yaxis=dict(
                        categoryorder="array",
                        categoryarray=["Active", "At Risk", "Churned"],
                        gridcolor="#1e293b",
                    ),
                )
                st.plotly_chart(fig_state, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — LIVE SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Live Simulator":
    st.title("⚙️ Live Churn Simulator")
    st.markdown(
        "<p style='color:#64748b; margin-top:-12px;'>Ingest activity in real-time and watch Bayesian updates happen live.</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["📥 Ingest Activity", "🔧 Manual Override"])

    # ── TAB 1: INGEST ACTIVITY ─────────────────────────────────────────────
    with tab1:
        st.markdown("<div class='section-header'>Ingest New User Activity</div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            sim_company = st.selectbox("Company", companies["name"].tolist(), key="sim_co")
            sim_company_id = int(companies[companies["name"] == sim_company]["company_id"].values[0])
            users_list = load_users_for_company(sim_company_id)
            user_options = {f"#{r['user_id']} — {r['email']}": r["user_id"]
                            for _, r in users_list.iterrows()}
            sim_user_label = st.selectbox("User", list(user_options.keys()), key="sim_user")
            sim_user_id = user_options[sim_user_label]

        with col2:
            sim_logins   = st.number_input("Logins Today", 0, 20, 2)
            sim_time     = st.number_input("Time Spent (mins)", 0.0, 300.0, 30.0, step=5.0)
            sim_pages    = st.number_input("Pages Visited", 0, 100, 5)
            sim_tickets  = st.number_input("Support Tickets", 0, 5, 0)

        # Show current risk before
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT churn_prob, current_state FROM users WHERE user_id=?",
                           (sim_user_id,)).fetchone()
        conn.close()

        if cur:
            prior_p, prior_s = cur[0], cur[1]
            st.markdown(f"""
            <div style='padding:12px; background:#1e293b; border:1px solid #334155;
                        border-radius:8px; margin:12px 0; font-family:monospace;'>
            <b>Before:</b> Risk = <b style='color:{STATE_COLOR_MAP.get(prior_s,"#94a3b8")}'>{prior_p:.1%}</b>
            &nbsp;|&nbsp; State = <b style='color:{STATE_COLOR_MAP.get(prior_s,"#94a3b8")}'>{prior_s}</b>
            </div>
            """, unsafe_allow_html=True)

        if st.button("▶ Run Bayesian Update", type="primary", use_container_width=True):
            result = ingest_new_activity(sim_user_id, sim_company_id,
                                          sim_logins, sim_time, sim_pages, sim_tickets)
            if result and "error" not in result:
                new_color = STATE_COLOR_MAP.get(result["state"], "#94a3b8")
                delta = result["posterior"] - result["prior"]
                delta_str = f"+{delta:.1%}" if delta > 0 else f"{delta:.1%}"
                delta_color = "#ef4444" if delta > 0 else "#22c55e"

                st.markdown(f"""
                <div style='padding:16px; background:rgba(99,102,241,0.08); border:1px solid #6366f1;
                            border-radius:8px; margin:12px 0;'>
                <b>✅ Update Applied</b><br><br>
                Prior: <code>{result['prior']:.1%}</code> →
                Posterior: <b style='color:{new_color}'>{result['posterior']:.1%}</b>
                &nbsp;<span style='color:{delta_color}'>({delta_str})</span><br>
                State: <b style='color:{new_color}'>{result['state']}</b>
                {"<br><br><b style='color:#ef4444'>🚨 CRITICAL ALERT: Risk ≥ 90%!</b>" if result.get('alert') else ""}
                </div>
                """, unsafe_allow_html=True)

                if result["factors"]:
                    st.markdown("<b>Bayesian Factors Applied:</b>", unsafe_allow_html=True)
                    for factor, impact in result["factors"].items():
                        color = "#ef4444" if "+" in str(impact) else "#22c55e"
                        st.markdown(
                            f"<span style='color:{color}; font-family:monospace; font-size:0.85rem;'>"
                            f"• {factor}: {impact}</span>", unsafe_allow_html=True
                        )

                # Show updated chart
                st.markdown("<div class='section-header'>Updated Risk History</div>",
                            unsafe_allow_html=True)
                hist = load_user_history(sim_user_id)
                if not hist.empty:
                    fig = go.Figure(go.Scatter(
                        x=hist["date"], y=hist["churn_probability"],
                        mode="lines+markers", line=dict(color=COLORS["primary"], width=2),
                        fill="tozeroy", fillcolor="rgba(99,102,241,0.10)"
                    ))
                    fig.update_layout(**PLOTLY_LAYOUT, height=250,
                                      yaxis_tickformat=".0%", yaxis_range=[0, 1])
                    st.plotly_chart(fig, use_container_width=True)
            elif result and "error" in result:
                st.error(result["error"])

    # ── TAB 2: MANUAL OVERRIDE ─────────────────────────────────────────────
    with tab2:
        st.markdown("<div class='section-header'>Admin Manual Override</div>", unsafe_allow_html=True)
        st.info("Use this when you have external context the model doesn't know (e.g., user called support, signed renewal).")

        ov_company = st.selectbox("Company", companies["name"].tolist(), key="ov_co")
        ov_company_id = int(companies[companies["name"] == ov_company]["company_id"].values[0])
        ov_users = load_users_for_company(ov_company_id)
        ov_opts = {f"#{r['user_id']} — {r['email']} (current: {r['churn_prob']:.1%})": r["user_id"]
                   for _, r in ov_users.iterrows()}
        ov_label = st.selectbox("User", list(ov_opts.keys()), key="ov_user")
        ov_user_id = ov_opts[ov_label]

        new_prob = st.slider("Forced Churn Probability", 0.01, 0.95, 0.20, 0.01,
                              format="%.0f%%")
        reason   = st.text_input("Reason", placeholder="e.g. User renewed contract, called in satisfied")

        new_state_preview = "Churned" if new_prob >= 0.75 else ("At Risk" if new_prob >= 0.45 else "Active")
        preview_color = STATE_COLOR_MAP.get(new_state_preview, "#94a3b8")
        st.markdown(f"""
        <div style='padding:10px 14px; background:#1e293b; border-radius:6px; margin-bottom:12px;
                    font-family:monospace; font-size:0.85rem;'>
        Preview → Risk: <b style='color:{preview_color}'>{new_prob:.1%}</b>
        &nbsp;| State: <b style='color:{preview_color}'>{new_state_preview}</b>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⚡ Apply Override", type="primary"):
            new_state = update_user_churn(ov_user_id, new_prob, reason or "Admin override")
            st.success(f"✅ Override applied! User {ov_user_id} → {new_prob:.1%} risk / {new_state}")
            load_company_summary.clear()
