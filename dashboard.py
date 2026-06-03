import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

import plotly.express as px
import plotly.graph_objects as go

from streamlit_autorefresh import st_autorefresh
from civiq_features import (
    get_holiday_status,
    get_upcoming_closures,
    assign_token,
    predict_token_wait,
    get_token_status,
    send_sms_alert,
    check_and_alert,
    mark_token_missed,
    recover_missed_token,
    get_recovery_suggestion,
    SENIOR_AGE_THRESHOLD,
)

st.set_page_config(
    page_title="Smart Civic Analytics",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "token_store" not in st.session_state:
    st.session_state["token_store"] = {}

_refresh_count = st_autorefresh(interval=30_000, limit=None, key="civiq_autorefresh")

# ─────────────────────────────────────────────
# DEEP TEAL THEME
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0a2a2a !important; }
    section[data-testid="stSidebar"] { background-color: #0f3d3d !important; }
    section[data-testid="stSidebar"] * { color: #cce8e1 !important; }
    .stApp, .stApp p, .stApp label, .stApp div { color: #cce8e1; }
    h1, h2, h3 { color: #ffffff !important; }
    .metric-card {
        background: #0f3d3d; border-radius: 12px; padding: 20px;
        text-align: center; border-left: 5px solid #1d9e75; margin-bottom: 10px;
    }
    .alert-green  { border-left: 5px solid #1d9e75 !important; background: #0a3d2a !important; }
    .alert-yellow { border-left: 5px solid #f0c040 !important; background: #2a2a0a !important; }
    .alert-red    { border-left: 5px solid #e05555 !important; background: #3d0f0f !important; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #ffffff; }
    .metric-label { font-size: 0.85rem; color: #5dbdab; margin-top: 4px; }
    .section-header {
        font-size: 1.05rem; font-weight: 600; color: #9fe1cb;
        margin: 16px 0 8px; border-bottom: 2px solid #1a5a5a; padding-bottom: 6px;
    }
    .token-card {
        background: #0f5c4a; border: 1px solid #1d9e75;
        color: white; border-radius: 14px; padding: 24px; text-align: center;
    }
    .senior-token-card {
        background: #3d2a00; border: 2px solid #f0c040;
        color: white; border-radius: 14px; padding: 24px; text-align: center;
    }
    .token-number { font-size: 3.5rem; font-weight: 800; }
    .token-label  { font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }
    .senior-badge {
        display: inline-block; background: #f0c040; color: #1a1a00;
        font-size: 0.8rem; font-weight: 800; padding: 4px 14px;
        border-radius: 20px; margin-bottom: 10px;
    }
    .recovery-card {
        background: #2a1a0a; border: 1px solid #f0c040;
        border-radius: 14px; padding: 20px; text-align: center; color: white;
    }
    .recovery-new-token { font-size: 3rem; font-weight: 800; color: #f0c040; }
    .recovery-label { font-size: 0.85rem; color: #f0e080; margin-top: 4px; }
    .option-card {
        background: #0f3d3d; border: 1px solid #1a5a5a;
        border-radius: 10px; padding: 16px; margin-bottom: 10px;
    }
    .option-card.recommended { border: 2px solid #1d9e75; background: #0a3d2a; }
    .option-title { font-size: 1rem; font-weight: 700; color: #ffffff; }
    .option-wait  { font-size: 1.6rem; font-weight: 800; color: #1d9e75; }
    .option-desc  { font-size: 0.82rem; color: #5dbdab; margin-top: 4px; }
    .badge-rec {
        display: inline-block; background: #1d9e75; color: #fff;
        font-size: 0.7rem; font-weight: 700; padding: 2px 10px;
        border-radius: 20px; margin-bottom: 6px;
    }
    .closed-banner {
        background: #3d0f0f; border-left: 5px solid #e05555;
        border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 16px; color: #f5a5a5;
    }
    .open-banner {
        background: #0a3d2a; border-left: 5px solid #1d9e75;
        border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 16px; color: #9fe1cb;
    }
    .holiday-banner {
        background: #2a2a0a; border-left: 5px solid #f0c040;
        border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 16px; color: #f0e080;
    }
    .stSelectbox > div > div, .stNumberInput > div > div, .stTextInput > div > div {
        background-color: #0a2a2a !important; border-color: #1a5a5a !important; color: #cce8e1 !important;
    }
    input, select, textarea {
        background-color: #0a2a2a !important; color: #cce8e1 !important; border-color: #1a5a5a !important;
    }
    .stButton > button {
        background-color: #1d9e75 !important; color: #ffffff !important;
        border: none !important; border-radius: 8px !important; font-weight: 600 !important;
    }
    .stButton > button:hover { background-color: #0f6e56 !important; }
    .stButton > button:active { background-color: #085041 !important; }
    .stCheckbox label { color: #cce8e1 !important; }
    .stSlider > div > div > div { background-color: #1d9e75 !important; }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0f3d3d !important; border-radius: 8px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] { color: #5dbdab !important; background-color: transparent !important; }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important; background-color: #1d9e75 !important; border-radius: 6px !important;
    }
    .stDataFrame { background-color: #0f3d3d !important; }
    .stDataFrame th { background-color: #1a5a5a !important; color: #9fe1cb !important; }
    .stDataFrame td { color: #cce8e1 !important; }
    .streamlit-expanderHeader {
        background-color: #0f3d3d !important; color: #9fe1cb !important; border-radius: 8px !important;
    }
    .stAlert { background-color: #0f3d3d !important; color: #cce8e1 !important; border-color: #1a5a5a !important; }
    hr { border-color: #1a5a5a !important; }
    [data-testid="metric-container"] {
        background-color: #0f3d3d; border-radius: 10px; padding: 12px; border-left: 4px solid #1d9e75;
    }
    [data-testid="metric-container"] label { color: #5dbdab !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #ffffff !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a2a2a; }
    ::-webkit-scrollbar-thumb { background: #1a5a5a; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #1d9e75; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD MODELS
# ─────────────────────────────────────────────
@st.cache_resource
def load_models():
    models = {}
    files = {
        "wait_time":    "models/wait_time_model.pkl",
        "queue_length": "models/queue_length_model.pkl",
        "alert":        "models/alert_model.pkl",
        "best_time":    "models/best_time_data.pkl",
    }
    for name, path in files.items():
        if os.path.exists(path):
            with open(path, "rb") as f:
                models[name] = pickle.load(f)
        else:
            models[name] = None
    return models

@st.cache_data
def load_cleaned_data():
    path = "data/cleaned_queue_data.csv"
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["datetime"])
    return None

models = load_models()
df     = load_cleaned_data()


# ─────────────────────────────────────────────
# PREDICTION HELPERS
# ─────────────────────────────────────────────
PLACE_TYPE_MAP = {"Government": 0, "Hospital": 1, "Bank": 2, "Post Office": 3}
SEASON_MAP = {"Winter": 0, "Summer": 1, "Monsoon": 2, "Autumn": 3}

def get_season(month):
    if month in [12, 1, 2]:    return "Winter"
    if month in [3, 4, 5]:     return "Summer"
    if month in [6, 7, 8, 9]:  return "Monsoon"
    return "Autumn"

def build_features(hour, dow, queue, service_time, counters,
                   is_holiday, month, weather_score,
                   place_type="Government", staff_on_duty=None,
                   is_festival=0, festival_multiplier=1.0):
    is_weekend          = 1 if dow >= 5 else 0
    is_rush             = 1 if (is_weekend == 0 and hour in [9, 10, 17, 18]) else 0
    counter_eff         = round(counters / max(queue, 1), 3)
    place_type_encoded  = PLACE_TYPE_MAP.get(place_type, 0)
    season_encoded      = SEASON_MAP.get(get_season(month), 0)
    if staff_on_duty is None:
        staff_on_duty   = counters * 2
    staff_counter_ratio = round(staff_on_duty / max(counters, 1), 3)
    return np.array([[
        hour, dow, month,
        is_weekend, is_holiday, is_rush, is_festival,
        place_type_encoded, season_encoded,
        queue, counters, service_time, staff_on_duty,
        weather_score, counter_eff, staff_counter_ratio, festival_multiplier,
        np.sin(2*np.pi*hour/24),  np.cos(2*np.pi*hour/24),
        np.sin(2*np.pi*dow/7),    np.cos(2*np.pi*dow/7),
        np.sin(2*np.pi*month/12), np.cos(2*np.pi*month/12),
    ]])

def predict_wait_time(features):
    if models["wait_time"]:
        return max(0, round(float(models["wait_time"].predict(features)[0]), 1))
    q, c, s = features[0][9], features[0][10], features[0][11]
    return round((q / max(c, 1)) * s, 1)

def predict_queue_forecast(features):
    if models["queue_length"]:
        pred = models["queue_length"].predict(features)[0]
        return int(max(0, pred[0])), int(max(0, pred[1]))
    q = int(features[0][9])
    return max(0, q - 5), max(0, q - 10)

def predict_alert(features):
    if models["alert"]:
        return int(models["alert"].predict(features)[0])
    wait = predict_wait_time(features)
    if wait <= 10: return 0
    if wait <= 25: return 1
    return 2

def get_best_time():
    if models["best_time"] and isinstance(models["best_time"], dict):
        best = models["best_time"].get("best_slots", [])
        if best:
            slot = best[0]
            return f"{slot['day_name']} at {int(slot['hour_of_day']):02d}:00", slot['wait_time_minutes']
    return "Tuesday at 10:00", "~5"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.title("🧠 Smart Civic Analytics")

with st.sidebar.expander("🔧 SMS Debug", expanded=False):
    sid_ok   = bool(os.getenv("TWILIO_ACCOUNT_SID"))
    token_ok = bool(os.getenv("TWILIO_AUTH_TOKEN"))
    from_ok  = bool(os.getenv("TWILIO_FROM_NUMBER"))
    st.write("**Credentials loaded:**")
    st.write(f"- ACCOUNT_SID : {'✅' if sid_ok   else '❌ Missing'}")
    st.write(f"- AUTH_TOKEN  : {'✅' if token_ok else '❌ Missing'}")
    st.write(f"- FROM_NUMBER : {'✅' if from_ok  else '❌ Missing'}")
    test_phone = st.text_input("Test phone (+country code)", key="debug_phone",
                               placeholder="+919876543210")
    if st.button("Send Test SMS"):
        if not test_phone:
            st.warning("Enter a phone number.")
        else:
            r = send_sms_alert(test_phone, "CiviQ Test: SMS working! ✅")
            if r["status"] == "sent":
                st.success(f"✅ Sent! SID: {r['sid']}")
            else:
                st.error(r["status"])
                st.json(r)

st.sidebar.markdown("---")
st.sidebar.markdown("**Select Place & Conditions**")

PLACE_OPTIONS = {
    "RTO Office Pune":      "Government",
    "City Hospital OPD":    "Hospital",
    "SBI Bank Branch":      "Bank",
    "Passport Seva Kendra": "Government",
}
selected_place = st.sidebar.selectbox("🏢 Select Place", list(PLACE_OPTIONS.keys()))
place_type     = PLACE_OPTIONS[selected_place]

now   = datetime.now()
hour  = st.sidebar.slider("🕐 Hour of day", 8, 20, now.hour if 8 <= now.hour <= 20 else 10)
dow   = st.sidebar.selectbox(
    "📅 Day of week",
    options=[0,1,2,3,4,5,6],
    format_func=lambda x: ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][x],
    index=now.weekday()
)
month = st.sidebar.selectbox(
    "🗓️ Month",
    options=list(range(1, 13)),
    format_func=lambda x: datetime(2024, x, 1).strftime("%B"),
    index=now.month - 1
)
queue_len    = st.sidebar.number_input("👥 Current queue length", 0, 200, 20)
counters     = st.sidebar.slider("🖥️ Counters open", 1, 8, 3)
service_time = st.sidebar.slider("⏱️ Avg service time (min)", 2.0, 15.0, 5.0, step=0.5)
weather      = st.sidebar.selectbox("🌤️ Weather", ["Sunny","Cloudy","Rainy","Stormy"])
is_holiday   = st.sidebar.checkbox("🎉 Public holiday today?")

weather_map   = {"Sunny": 1.0, "Cloudy": 0.85, "Rainy": 0.65, "Stormy": 0.4}
weather_score = weather_map[weather]

st.sidebar.markdown("---")
predict_btn = st.sidebar.button("🔮 Run Predictions", use_container_width=True)


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
st.title("🧠 Smart Civic Analytics")
st.markdown("---")

holiday_status = get_holiday_status(place_type=place_type)
if not holiday_status["is_open"]:
    st.markdown(f"""
    <div class="closed-banner">
        🔴 <strong>CLOSED TODAY</strong> — {holiday_status['reason']}<br>
        <small>This {place_type} is not operating today.</small>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="open-banner">
        🟢 <strong>OPEN TODAY</strong> — {holiday_status['alert_message']}
    </div>""", unsafe_allow_html=True)

closures = get_upcoming_closures(place_type=place_type, days_ahead=7)
if closures:
    closure_text = " | ".join([f"{c['date']} ({c['reason']})" for c in closures])
    st.markdown(f"""
    <div class="holiday-banner">
        📅 <strong>Upcoming closures (next 7 days):</strong> {closure_text}
    </div>""", unsafe_allow_html=True)

features = build_features(
    hour, dow, queue_len, service_time, counters,
    int(is_holiday), month, weather_score,
    place_type=place_type, staff_on_duty=counters * 2,
)
wait_time                = predict_wait_time(features)
forecast_1h, forecast_2h = predict_queue_forecast(features)
alert_level              = predict_alert(features)
best_time_str, best_wait = get_best_time()

alert_config = {
    0: ("🟢 Normal",      "alert-green",  "#1d9e75"),
    1: ("🟡 Moderate",    "alert-yellow", "#f0c040"),
    2: ("🔴 Overcrowded", "alert-red",    "#e05555"),
}
alert_label, alert_class, alert_color = alert_config[alert_level]

st.markdown('<p class="section-header">📊 Live Predictions</p>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card {alert_class}"><div class="metric-value">{wait_time} min</div><div class="metric-label">⏳ Estimated Wait Time</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{queue_len} → {forecast_1h}</div><div class="metric-label">👥 Queue Now → In 1 Hour</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card {alert_class}"><div class="metric-value">{alert_label}</div><div class="metric-label">🚨 Current Status</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size:1.2rem">{best_time_str}</div><div class="metric-label">✅ Best Time (~{best_wait} min)</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# VIRTUAL TOKEN SYSTEM
# ══════════════════════════════════════════════
st.markdown('<p class="section-header">🎫 Virtual Token System</p>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["➕ Get New Token", "🔍 Check My Token", "🔁 Missed Token Recovery"])


# ── Tab 1: Get token ──────────────────────────
with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        user_name  = st.text_input("Your Name", placeholder="e.g. Pramod Haladkar")
    with col_b:
        user_phone = st.text_input("Your Phone (with +91)", placeholder="+919800000000")

    # ── Age input row ────────────────────────
    col_age, col_cur = st.columns(2)
    with col_age:
        user_age = st.number_input(
            f"Your Age  (seniors {SENIOR_AGE_THRESHOLD}+ get priority 🌟)",
            min_value=1, max_value=120, value=30
        )
    with col_cur:
        current_token = st.number_input(
            "Current token being served at counter", min_value=1, max_value=500, value=45
        )

    # Show senior notice live
    if user_age >= SENIOR_AGE_THRESHOLD:
        st.markdown(
            f'<div style="background:#3d2a00;border-left:4px solid #f0c040;border-radius:0 8px 8px 0;'
            f'padding:10px 14px;color:#f0e080;margin-bottom:8px;">'
            f'🌟 <strong>Senior Priority Activated</strong> — Age {user_age}: you will be placed near the front of the queue.</div>',
            unsafe_allow_html=True
        )

    if st.button("🎫 Get My Token Number", use_container_width=True):
        if not user_name or not user_phone:
            st.warning("Please enter your name and phone number.")
        elif not user_phone.startswith("+"):
            st.error("Phone must start with + and country code. Example: +919876543210")
        else:
            token = assign_token(
                place_name=selected_place,
                user_name=user_name,
                user_phone=user_phone,
                current_token_number=int(current_token),
                token_store=st.session_state["token_store"],
                user_age=int(user_age),
            )
            wait = predict_token_wait(token, service_time, counters)

            st.session_state["my_token"]    = token
            st.session_state["my_token_id"] = token["token_id"]

            is_senior = token.get("is_senior", False)
            border_color = "#f0c040" if is_senior else "#1d9e75"
            bg_color     = "#3d2a00" if is_senior else "#0f5c4a"

            st.markdown(
                f'<div style="background:{bg_color};border:2px solid {border_color};'
                f'border-radius:14px;padding:24px;text-align:center;color:white;">',
                unsafe_allow_html=True
            )
            if is_senior:
                st.markdown(
                    '<p style="display:inline-block;background:#f0c040;color:#1a1a00;'
                    'font-size:0.85rem;font-weight:800;padding:4px 16px;border-radius:20px;'
                    'margin-bottom:8px;">🌟 SENIOR PRIORITY</p>',
                    unsafe_allow_html=True
                )
            st.markdown(f"<p style='font-size:0.9rem;opacity:0.8;margin:0'>YOUR TOKEN NUMBER</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:3.5rem;font-weight:900;margin:0;color:white'>{token['token_number']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size:0.85rem;opacity:0.75;margin:4px 0 12px'>Token ID: {token['token_id']}</p>", unsafe_allow_html=True)
            c1t, c2t, c3t = st.columns(3)
            c1t.metric("📍 Place",       selected_place)
            c2t.metric("⏳ Est. Wait",   f"{wait} min")
            c3t.metric("👥 Ahead",       token['tokens_ahead'])
            st.caption(f"🕒 Issued at: {token['issued_at']}")
            st.markdown("</div>", unsafe_allow_html=True)

            st.success(f"✅ Token assigned! Save your Token ID: **{token['token_id']}**")

            # ── AUTO-SEND SMS immediately on token assignment ──
            senior_line = "\nSENIOR PRIORITY: You are placed near the front." if is_senior else ""
            auto_msg = (
                f"Hi {user_name},\n"
                f"CiviQ Que - Token Confirmation\n"
                f"Place : {selected_place}\n"
                f"Token : {token['token_number']}\n"
                f"ID    : {token['token_id']}\n"
                f"Wait  : ~{wait} min{senior_line}\n"
                f"Save your Token ID to check status. - CiviQ Que"
            )
            sms_result = send_sms_alert(user_phone, auto_msg)
            if sms_result["status"] == "sent":
                st.success(f"SMS sent {user_name}!")
            elif sms_result["status"] == "not_configured":
                st.info("SMS not sent - add Twilio credentials to .env to enable auto-SMS.")
            else:
                st.warning(f"Auto-SMS failed: {sms_result['status']}")
                st.json(sms_result)


# ── Tab 2: Check token status ─────────────────
with tab2:
    col_x, col_y = st.columns([2, 1])
    with col_x:
        check_token_id = st.text_input(
            "Token ID",
            value=st.session_state.get("my_token_id", ""),
            placeholder="e.g. TKN-2847"
        )
    with col_y:
        now_serving = st.number_input(
            "Currently serving token", min_value=1, max_value=500, value=45
        )

    # ── Auto-display status on every 30s refresh if token ID is known ──
    if check_token_id and check_token_id in st.session_state["token_store"]:
        result = get_token_status(
            check_token_id,
            int(now_serving),
            token_store=st.session_state["token_store"],
        )
        status_colors = {"Waiting": "🔵", "Soon": "🟡", "Near": "🟠", "Called": "🔴"}
        status_bg     = {"Waiting": "#0f3d3d", "Soon": "#2a2a0a", "Near": "#2a1a00", "Called": "#3d0f0f"}
        emoji = status_colors.get(result["status"], "🔵")
        bg    = status_bg.get(result["status"], "#0f3d3d")
        st.markdown(
            f'<div style="background:{bg};border-radius:12px;padding:20px;text-align:center;">'
            f'<p style="font-size:2rem;font-weight:700;color:#fff;margin:0">{emoji} {result["status"]}</p>'
            f'<p style="font-size:0.9rem;color:#cce8e1;margin-top:6px">{result["message"]}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("Your Token",        result["token_number"])
        col2.metric("Currently Serving", result["current_serving"])
        col3.metric("Tokens Remaining",  result["remaining"])
        st.caption("🔄 Status auto-refreshes every 30 seconds")

        # ── Send alert SMS only ONCE per status change ──
        alert_key = f"alerted_{check_token_id}_{result['status']}"
        if result["should_alert"] and not st.session_state.get(alert_key):
            st.session_state[alert_key] = True
            phone = result.get("user_phone", "")
            name  = result.get("user_name", "")
            if phone:
                alert_sms = (
                    f"Hi {name},\n"
                    f"{result['message']}\n"
                    f"Please go to the counter now. - CiviQ Que"
                )
                sms_result = send_sms_alert(phone, alert_sms)
                if sms_result["status"] == "sent":
                    st.success(f"📱 Alert SMS automatically sent to {name}!")
                elif sms_result["status"] != "not_configured":
                    st.warning(f"⚠️ Auto-alert SMS failed: {sms_result['status']}")

    if st.button("🔍 Refresh Status Manually", use_container_width=True):
        if not check_token_id:
            st.warning("Please enter your Token ID.")
        elif check_token_id not in st.session_state["token_store"]:
            st.error("Token not found. Please check your Token ID.")
            st.info("Tip: Token IDs reset when you refresh the page. Get a new token first.")
        else:
            st.rerun()



# ── Tab 3: Missed Token Recovery ─────────────
with tab3:
    st.markdown("""
    <div style="background:#0f3d3d; border-left:4px solid #f0c040; border-radius:0 8px 8px 0;
                padding:12px 16px; margin-bottom:20px; color:#f0e080;">
        😟 <strong>Missed your token?</strong> No need to start over.
        Enter your Token ID below and we'll assign you the next available slot.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-header">Step 1 — Enter Your Details</p>', unsafe_allow_html=True)

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        missed_token_id = st.text_input(
            "Your Token ID", placeholder="e.g. TKN-2847", key="missed_token_input"
        )
    with col_r2:
        missed_now_serving = st.number_input(
            "Token currently being served", min_value=1, max_value=500, value=45, key="missed_now_serving"
        )
    with col_r3:
        missed_queue_len = st.number_input(
            "Current queue length", min_value=0, max_value=200, value=int(queue_len), key="missed_queue_len"
        )

    if missed_token_id:
        
        orig_token = st.session_state["token_store"].get(missed_token_id, {})
        is_senior_recovery = orig_token.get("is_senior", False)

        if is_senior_recovery:
            st.markdown(
                '<div style="background:#3d2a00;border-left:4px solid #f0c040;border-radius:0 8px 8px 0;'
                'padding:10px 14px;color:#f0e080;margin-bottom:8px;">'
                '🌟 <strong>Senior Priority Recovery</strong> — This token belongs to a senior citizen. '
                'They will be placed at the front regardless of queue length.</div>',
                unsafe_allow_html=True
            )

        suggestion = get_recovery_suggestion(
            current_queue_length=int(missed_queue_len),
            avg_service_time=service_time,
            num_counters=counters,
        )

        st.markdown('<p class="section-header">Step 2 — Choose Recovery Mode</p>', unsafe_allow_html=True)
        st.markdown(f"<small style='color:#5dbdab'>💡 {suggestion['reason']}</small>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        opt_col1, opt_col2 = st.columns(2)

        is_rec_fixed = suggestion["recommended_mode"] == "fixed_buffer"
        is_rec_after = suggestion["recommended_mode"] == "after_queue"

        with opt_col1:
            with st.container():
                if is_rec_fixed:
                    st.markdown("⭐ **Recommended**")
                st.markdown(f"### ⚡ Next Available Slot")
                st.markdown(f"**{suggestion['wait_fixed']} min**")
                st.markdown(
                    f"Jump in as soon as there's a gap.  \n"
                    f"Best when queue is short or empty.  \n"
                    f"Buffer: {suggestion['buffer_size']} tokens ahead of you."
                )
                if st.button("⚡ Use Next Available Slot", use_container_width=True, key="btn_fixed"):
                    st.session_state["recovery_mode"]    = "fixed_buffer"
                    st.session_state["trigger_recovery"] = True

        with opt_col2:
            with st.container():
                if is_rec_after:
                    st.markdown("⭐ **Recommended**")
                st.markdown(f"### 🕐 After Current Queue")
                st.markdown(f"**{suggestion['wait_after_queue']} min**")
                st.markdown(
                    f"Placed after everyone currently waiting.  \n"
                    f"Fair when queue is long.  \n"
                    f"Queue: {suggestion['queue_length']} people ahead."
                )
                if st.button("🕐 Place After Queue", use_container_width=True, key="btn_after"):
                    st.session_state["recovery_mode"]    = "after_queue"
                    st.session_state["trigger_recovery"] = True

    if st.session_state.get("trigger_recovery") and missed_token_id:
        st.session_state["trigger_recovery"] = False
        chosen_mode = st.session_state.get("recovery_mode", "fixed_buffer")

        mark_result = mark_token_missed(
            token_id=missed_token_id,
            token_store=st.session_state["token_store"],
        )

        if not mark_result["success"]:
            if "recovery_token" in mark_result:
                existing_rec = st.session_state["token_store"].get(mark_result["recovery_token"], {})
                st.warning(f"⚠️ {mark_result['error']}")
                if existing_rec:
                    st.markdown(f"""
                    <div class="recovery-card">
                        <div class="recovery-label">YOUR EXISTING RECOVERY TOKEN</div>
                        <div class="recovery-new-token">{existing_rec.get('token_number', '—')}</div>
                        <div class="recovery-label">Token ID: {mark_result['recovery_token']}</div>
                        <div style="margin-top:8px; font-size:0.9rem; color:#f0e080;">
                            Est. wait: {existing_rec.get('estimated_wait_min', '?')} min
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error(mark_result["error"])
        else:
            rec = recover_missed_token(
                token_id=missed_token_id,
                current_serving_number=int(missed_now_serving),
                current_queue_length=int(missed_queue_len),
                avg_service_time=service_time,
                num_counters=counters,
                token_store=st.session_state["token_store"],
                recovery_mode=chosen_mode,
            )

            if not rec["success"]:
                st.error(rec.get("error", "Recovery failed."))
            else:
                st.markdown("---")
                st.markdown("### ✅ Recovery Token Issued")

                border_color = "#f0c040" if rec.get("is_senior") else "#f0c040"
                st.markdown(
                    f'<div style="background:#2a1a0a;border:2px solid {border_color};'
                    f'border-radius:14px;padding:24px;text-align:center;color:white;">',
                    unsafe_allow_html=True
                )
                if rec.get("is_senior"):
                    st.markdown(
                        '<p style="display:inline-block;background:#f0c040;color:#1a1a00;'
                        'font-size:0.85rem;font-weight:800;padding:4px 16px;border-radius:20px;'
                        'margin-bottom:8px;">🌟 SENIOR PRIORITY</p>',
                        unsafe_allow_html=True
                    )
                st.markdown("<p style='font-size:0.85rem;color:#f0e080;margin:0'>YOUR NEW TOKEN NUMBER</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:3rem;font-weight:900;color:#f0c040;margin:0'>{rec['new_token']}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:0.85rem;color:#f0e080;margin:4px 0 12px'>New Token ID: {rec['recovery_id']}</p>", unsafe_allow_html=True)
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("📍 Place",     rec['place_name'])
                rc2.metric("⏳ Est. Wait", f"{rec['estimated_wait']} min")
                rc3.metric("👥 Ahead",     rec['tokens_ahead'])
                st.caption(f"📌 {rec['mode_label']}  |  🕒 {rec['issued_at']}")
                st.markdown("</div>", unsafe_allow_html=True)

                st.session_state["my_token_id"] = rec["recovery_id"]
                st.success(f"✅ New token issued! Save your new Token ID: **{rec['recovery_id']}**")

                phone = rec.get("user_phone", "")
                name  = rec.get("user_name", "")
                if phone:
                    senior_sms_line = "\n🌟 Senior Priority Applied — placed near the front." if rec.get("is_senior") else ""
                    # ── Personalised recovery SMS ──
                    senior_note = "\nSENIOR PRIORITY: Placed near the front." if rec.get("is_senior") else ""
                    sms_msg = (
                        f"Hi {name},\n"
                        f"CiviQ Que - Missed Token Recovered\n"
                        f"Place     : {rec['place_name']}\n"
                        f"New Token : {rec['new_token']}\n"
                        f"New ID    : {rec['recovery_id']}\n"
                        f"Wait      : ~{rec['estimated_wait']} min\n"
                        f"Placed    : {rec['mode_label']}{senior_note}\n"
                        f"Save your new Token ID. - CiviQ Que"
                    )
                    sms_result = send_sms_alert(phone, sms_msg)
                    if sms_result["status"] == "sent":
                        st.success(f"📱 Recovery SMS sent to {name}! SID: {sms_result['sid']}")
                    elif sms_result["status"] == "not_configured":
                        st.info("ℹ️ Add Twilio credentials to .env to send recovery SMS.")


# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<p class="section-header">📈 Queue Forecast</p>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Now", "+1 Hour", "+2 Hours"],
        y=[queue_len, forecast_1h, forecast_2h],
        marker_color=[
            "#1d9e75",
            "#f0c040" if forecast_1h > queue_len * 1.1 else "#1d9e75",
            "#e05555" if forecast_2h > queue_len * 1.2 else "#1d9e75",
        ],
        text=[queue_len, forecast_1h, forecast_2h],
        textposition="outside",
        textfont=dict(color="#cce8e1"),
    ))
    fig.update_layout(
        height=280, margin=dict(t=20, b=20),
        plot_bgcolor="#0f3d3d", paper_bgcolor="#0a2a2a",
        font=dict(color="#cce8e1"),
        xaxis=dict(gridcolor="#1a5a5a", tickfont=dict(color="#5dbdab")),
        yaxis=dict(gridcolor="#1a5a5a", tickfont=dict(color="#5dbdab")),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown('<p class="section-header">🔥 Busy Hours Heatmap</p>', unsafe_allow_html=True)
    if df is not None:
        hm    = (df.groupby(["day_name", "hour_of_day"])["wait_time_minutes"]
                   .mean().round(1).reset_index())
        pivot = (hm.pivot(index="day_name", columns="hour_of_day", values="wait_time_minutes")
                   .reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]))
        fig2  = px.imshow(
            pivot, color_continuous_scale="Teal",
            labels=dict(x="Hour", y="", color="Wait (min)"), aspect="auto"
        )
        fig2.update_layout(
            height=280, margin=dict(t=20, b=20),
            plot_bgcolor="#0f3d3d", paper_bgcolor="#0a2a2a",
            font=dict(color="#cce8e1"),
            xaxis=dict(tickfont=dict(color="#5dbdab")),
            yaxis=dict(tickfont=dict(color="#5dbdab")),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Run generate_dataset.py and train_models.py first.")

st.markdown('<p class="section-header">✅ Best Times to Visit</p>', unsafe_allow_html=True)
if models["best_time"] and isinstance(models["best_time"], dict):
    best_slots = models["best_time"].get("best_slots", [])
    if best_slots:
        bdf = pd.DataFrame(best_slots)
        bdf["Time"] = bdf.apply(
            lambda r: f"{r['day_name']} {int(r['hour_of_day']):02d}:00", axis=1
        )
        bdf = bdf[["Time", "wait_time_minutes"]].rename(
            columns={"wait_time_minutes": "Avg Wait (min)"}
        )
        bdf.index = ["🥇","🥈","🥉","4️⃣","5️⃣"]
        st.dataframe(bdf, use_container_width=True)
else:
    st.info("Run train_models.py to see best times.")

st.markdown("---")
st.markdown('<p class="section-header">🗂️ Prediction History</p>', unsafe_allow_html=True)
if "history" not in st.session_state:
    st.session_state.history = []

if predict_btn or len(st.session_state.history) == 0:
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    st.session_state.history.insert(0, {
        "Time":       datetime.now().strftime("%H:%M:%S"),
        "Place":      selected_place,
        "Day":        day_names[dow],
        "Hour":       f"{hour:02d}:00",
        "Queue":      queue_len,
        "Wait (min)": wait_time,
        "+1hr Queue": forecast_1h,
        "Status":     alert_label,
        "Weather":    weather,
    })
    st.session_state.history = st.session_state.history[:10]

if st.session_state.history:
    st.dataframe(pd.DataFrame(st.session_state.history),
                 use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(
    "<center><small style='color:#5dbdab'>CiviQ Que — Smart Queue Intelligence System · "
    "Built by Pramod Haladkar · "
    "Powered by XGBoost + Random Forest + Twilio + Streamlit</small></center>",
    unsafe_allow_html=True
)