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
)

st.set_page_config(
    page_title="CiviQ Que â€” Smart Queue",
    page_icon="ðŸ§ ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# â”€â”€ Token store that survives Streamlit reruns â”€â”€
if "token_store" not in st.session_state:
    st.session_state["token_store"] = {}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DEEP TEAL THEME
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown("""
<style>
    .stApp {
        background-color: #0a2a2a !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #0f3d3d !important;
    }
    section[data-testid="stSidebar"] * {
        color: #cce8e1 !important;
    }
    .stApp, .stApp p, .stApp label, .stApp div {
        color: #cce8e1;
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
    .metric-card {
        background: #0f3d3d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border-left: 5px solid #1d9e75;
        margin-bottom: 10px;
    }
    .alert-green  { border-left: 5px solid #1d9e75 !important; background: #0a3d2a !important; }
    .alert-yellow { border-left: 5px solid #f0c040 !important; background: #2a2a0a !important; }
    .alert-red    { border-left: 5px solid #e05555 !important; background: #3d0f0f !important; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #ffffff; }
    .metric-label { font-size: 0.85rem; color: #5dbdab; margin-top: 4px; }
    .section-header {
        font-size: 1.05rem;
        font-weight: 600;
        color: #9fe1cb;
        margin: 16px 0 8px;
        border-bottom: 2px solid #1a5a5a;
        padding-bottom: 6px;
    }
    .token-card {
        background: #0f5c4a;
        border: 1px solid #1d9e75;
        color: white;
        border-radius: 14px;
        padding: 24px;
        text-align: center;
    }
    .token-number { font-size: 3.5rem; font-weight: 800; }
    .token-label  { font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }
    .recovery-card {
        background: #2a1a0a;
        border: 1px solid #f0c040;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        color: white;
    }
    .recovery-new-token {
        font-size: 3rem;
        font-weight: 800;
        color: #f0c040;
    }
    .recovery-label {
        font-size: 0.85rem;
        color: #f0e080;
        margin-top: 4px;
    }
    .option-card {
        background: #0f3d3d;
        border: 1px solid #1a5a5a;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .option-card.recommended {
        border: 2px solid #1d9e75;
        background: #0a3d2a;
    }
    .option-title { font-size: 1rem; font-weight: 700; color: #ffffff; }
    .option-wait  { font-size: 1.6rem; font-weight: 800; color: #1d9e75; }
    .option-desc  { font-size: 0.82rem; color: #5dbdab; margin-top: 4px; }
    .badge-rec {
        display: inline-block;
        background: #1d9e75;
        color: #fff;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 10px;
        border-radius: 20px;
        margin-bottom: 6px;
    }
    .closed-banner {
        background: #3d0f0f;
        border-left: 5px solid #e05555;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 16px;
        color: #f5a5a5;
    }
    .open-banner {
        background: #0a3d2a;
        border-left: 5px solid #1d9e75;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 16px;
        color: #9fe1cb;
    }
    .holiday-banner {
        background: #2a2a0a;
        border-left: 5px solid #f0c040;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 16px;
        color: #f0e080;
    }
    .stSelectbox > div > div,
    .stNumberInput > div > div,
    .stTextInput > div > div {
        background-color: #0a2a2a !important;
        border-color: #1a5a5a !important;
        color: #cce8e1 !important;
    }
    input, select, textarea {
        background-color: #0a2a2a !important;
        color: #cce8e1 !important;
        border-color: #1a5a5a !important;
    }
    .stButton > button {
        background-color: #1d9e75 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover { background-color: #0f6e56 !important; }
    .stButton > button:active { background-color: #085041 !important; }
    .stCheckbox label { color: #cce8e1 !important; }
    .stSlider > div > div > div { background-color: #1d9e75 !important; }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0f3d3d !important;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #5dbdab !important;
        background-color: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background-color: #1d9e75 !important;
        border-radius: 6px !important;
    }
    .stDataFrame { background-color: #0f3d3d !important; }
    .stDataFrame th { background-color: #1a5a5a !important; color: #9fe1cb !important; }
    .stDataFrame td { color: #cce8e1 !important; }
    .streamlit-expanderHeader {
        background-color: #0f3d3d !important;
        color: #9fe1cb !important;
        border-radius: 8px !important;
    }
    .stAlert {
        background-color: #0f3d3d !important;
        color: #cce8e1 !important;
        border-color: #1a5a5a !important;
    }
    hr { border-color: #1a5a5a !important; }
    [data-testid="metric-container"] {
        background-color: #0f3d3d;
        border-radius: 10px;
        padding: 12px;
        border-left: 4px solid #1d9e75;
    }
    [data-testid="metric-container"] label { color: #5dbdab !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #ffffff !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a2a2a; }
    ::-webkit-scrollbar-thumb { background: #1a5a5a; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #1d9e75; }
</style>
""", unsafe_allow_html=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# LOAD MODELS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PREDICTION HELPERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PLACE_TYPE_MAP = {
    "Government": 0, "Hospital": 1, "Bank": 2, "Post Office": 3,
}
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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SIDEBAR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.sidebar.title("ðŸ§  CiviQ Que")

with st.sidebar.expander("ðŸ”§ SMS Debug", expanded=False):
    sid_ok   = bool(os.getenv("TWILIO_ACCOUNT_SID"))
    token_ok = bool(os.getenv("TWILIO_AUTH_TOKEN"))
    from_ok  = bool(os.getenv("TWILIO_FROM_NUMBER"))
    st.write("**Credentials loaded:**")
    st.write(f"- ACCOUNT_SID : {'âœ…' if sid_ok   else 'âŒ Missing'}")
    st.write(f"- AUTH_TOKEN  : {'âœ…' if token_ok else 'âŒ Missing'}")
    st.write(f"- FROM_NUMBER : {'âœ…' if from_ok  else 'âŒ Missing'}")
    test_phone = st.text_input("Test phone (+country code)", key="debug_phone",
                               placeholder="+919876543210")
    if st.button("Send Test SMS"):
        if not test_phone:
            st.warning("Enter a phone number.")
        else:
            r = send_sms_alert(test_phone, "CiviQ Test: SMS working! âœ…")
            if r["status"] == "sent":
                st.success(f"âœ… Sent! SID: {r['sid']}")
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
selected_place = st.sidebar.selectbox("ðŸ¢ Select Place", list(PLACE_OPTIONS.keys()))
place_type     = PLACE_OPTIONS[selected_place]

now   = datetime.now()
hour  = st.sidebar.slider("ðŸ• Hour of day", 8, 20, now.hour if 8 <= now.hour <= 20 else 10)
dow   = st.sidebar.selectbox(
    "ðŸ“… Day of week",
    options=[0,1,2,3,4,5,6],
    format_func=lambda x: ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][x],
    index=now.weekday()
)
month = st.sidebar.selectbox(
    "ðŸ—“ï¸ Month",
    options=list(range(1, 13)),
    format_func=lambda x: datetime(2024, x, 1).strftime("%B"),
    index=now.month - 1
)
queue_len    = st.sidebar.number_input("ðŸ‘¥ Current queue length", 0, 200, 20)
counters     = st.sidebar.slider("ðŸ–¥ï¸ Counters open", 1, 8, 3)
service_time = st.sidebar.slider("â±ï¸ Avg service time (min)", 2.0, 15.0, 5.0, step=0.5)
weather      = st.sidebar.selectbox("ðŸŒ¤ï¸ Weather", ["Sunny","Cloudy","Rainy","Stormy"])
is_holiday   = st.sidebar.checkbox("ðŸŽ‰ Public holiday today?")

weather_map   = {"Sunny": 1.0, "Cloudy": 0.85, "Rainy": 0.65, "Stormy": 0.4}
weather_score = weather_map[weather]

st.sidebar.markdown("---")
predict_btn = st.sidebar.button("ðŸ”® Run Predictions", use_container_width=True)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN CONTENT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.title("ðŸ§  CiviQ Que â€” Smart Queue Intelligence")
st.markdown("---")

# â”€â”€ Holiday banner â”€â”€
holiday_status = get_holiday_status(place_type=place_type)
if not holiday_status["is_open"]:
    st.markdown(f"""
    <div class="closed-banner">
        ðŸ”´ <strong>CLOSED TODAY</strong> â€” {holiday_status['reason']}<br>
        <small>This {place_type} is not operating today.</small>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="open-banner">
        ðŸŸ¢ <strong>OPEN TODAY</strong> â€” {holiday_status['alert_message']}
    </div>""", unsafe_allow_html=True)

closures = get_upcoming_closures(place_type=place_type, days_ahead=7)
if closures:
    closure_text = " | ".join([f"{c['date']} ({c['reason']})" for c in closures])
    st.markdown(f"""
    <div class="holiday-banner">
        ðŸ“… <strong>Upcoming closures (next 7 days):</strong> {closure_text}
    </div>""", unsafe_allow_html=True)

# â”€â”€ Predictions â”€â”€
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
    0: ("ðŸŸ¢ Normal",      "alert-green",  "#1d9e75"),
    1: ("ðŸŸ¡ Moderate",    "alert-yellow", "#f0c040"),
    2: ("ðŸ”´ Overcrowded", "alert-red",    "#e05555"),
}
alert_label, alert_class, alert_color = alert_config[alert_level]

st.markdown('<p class="section-header">ðŸ“Š Live Predictions</p>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card {alert_class}"><div class="metric-value">{wait_time} min</div><div class="metric-label">â³ Estimated Wait Time</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{queue_len} â†’ {forecast_1h}</div><div class="metric-label">ðŸ‘¥ Queue Now â†’ In 1 Hour</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card {alert_class}"><div class="metric-value">{alert_label}</div><div class="metric-label">ðŸš¨ Current Status</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="font-size:1.2rem">{best_time_str}</div><div class="metric-label">âœ… Best Time (~{best_wait} min)</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# VIRTUAL TOKEN SYSTEM  (3 tabs)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
st.markdown('<p class="section-header">ðŸŽ« Virtual Token System</p>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["âž• Get New Token", "ðŸ” Check My Token", "ðŸ” Missed Token Recovery"])


# â”€â”€ Tab 1: Get token â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        user_name  = st.text_input("Your Name", placeholder="e.g. Pramod Haladkar")
    with col_b:
        user_phone = st.text_input("Your Phone (with +91)", placeholder="+919800000000")

    current_token = st.number_input(
        "Current token being served at counter", min_value=1, max_value=500, value=45
    )

    if st.button("ðŸŽ« Get My Token Number", use_container_width=True):
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
            )
            wait = predict_token_wait(token, service_time, counters)

            st.session_state["my_token"]    = token
            st.session_state["my_token_id"] = token["token_id"]

            st.markdown(f"""
            <div class="token-card">
                <div class="token-label">YOUR TOKEN NUMBER</div>
                <div class="token-number">{token['token_number']}</div>
                <div class="token-label">Token ID: {token['token_id']}</div>
                <br>
                <div style="font-size:1.1rem">
                    ðŸ“ {selected_place}<br>
                    ðŸ• Estimated wait: <strong>{wait} minutes</strong><br>
                    ðŸ‘¥ {token['tokens_ahead']} tokens before you<br>
                    ðŸ•’ Issued at: {token['issued_at']}
                </div>
            </div>""", unsafe_allow_html=True)

            st.success(f"âœ… Token assigned! Save your Token ID: **{token['token_id']}**")

    if st.session_state.get("my_token"):
        token = st.session_state["my_token"]
        st.markdown("---")
        st.markdown(f"**Send confirmation SMS for token `{token['token_id']}`**")
        if st.button("ðŸ“± Send Token Details via SMS"):
            wait = token.get("estimated_wait_min", "?")
            msg = (
                f"CiviQ Que Token Confirmation\n"
                f"Place: {token['place_name']}\n"
                f"Your Token: {token['token_number']}\n"
                f"Token ID: {token['token_id']}\n"
                f"Est. Wait: {wait} min\n"
                f"Save this Token ID to check status later."
            )
            result = send_sms_alert(token["user_phone"], msg)
            if result["status"] == "sent":
                st.success(f"ðŸ“± SMS sent! SID: {result['sid']}")
            elif result["status"] == "not_configured":
                st.info("â„¹ï¸ Add Twilio credentials to .env to enable SMS.")
            else:
                st.error(f"SMS failed: {result['status']}")
                st.json(result)


# â”€â”€ Tab 2: Check token status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    if st.button("ðŸ” Check Status", use_container_width=True):
        if not check_token_id:
            st.warning("Please enter your Token ID.")
        else:
            result = get_token_status(
                check_token_id,
                int(now_serving),
                token_store=st.session_state["token_store"],
            )

            if "error" in result:
                st.error(result["error"])
                st.info("Tip: Token IDs reset when you refresh the page. Get a new token first.")
            else:
                status_colors = {
                    "Waiting": "ðŸ”µ", "Soon": "ðŸŸ¡", "Near": "ðŸŸ ", "Called": "ðŸ”´"
                }
                emoji = status_colors.get(result["status"], "ðŸ”µ")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{emoji} {result['status']}</div>
                    <div class="metric-label">{result['message']}</div>
                </div>""", unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                col1.metric("Your Token",        result["token_number"])
                col2.metric("Currently Serving", result["current_serving"])
                col3.metric("Tokens Remaining",  result["remaining"])

                if result["should_alert"]:
                    phone = result.get("user_phone", "")
                    if phone:
                        sms_result = send_sms_alert(phone, result["message"])
                        if sms_result["status"] == "sent":
                            st.success(f"ðŸ“± Alert SMS sent! SID: {sms_result['sid']}")
                        else:
                            st.warning(f"âš ï¸ Alert triggered but SMS failed: {sms_result['status']}")
                            st.json(sms_result)


# â”€â”€ Tab 3: Missed Token Recovery â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
with tab3:
    st.markdown("""
    <div style="background:#0f3d3d; border-left:4px solid #f0c040; border-radius:0 8px 8px 0;
                padding:12px 16px; margin-bottom:20px; color:#f0e080;">
        ðŸ˜Ÿ <strong>Missed your token?</strong> No need to start over.
        Enter your Token ID below and we'll assign you the next available slot â€”
        either right after the current queue, or immediately if the queue is short.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-header">Step 1 â€” Enter Your Details</p>', unsafe_allow_html=True)

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        missed_token_id = st.text_input(
            "Your Token ID",
            placeholder="e.g. TKN-2847",
            key="missed_token_input"
        )
    with col_r2:
        missed_now_serving = st.number_input(
            "Token currently being served",
            min_value=1, max_value=500, value=45,
            key="missed_now_serving"
        )
    with col_r3:
        missed_queue_len = st.number_input(
            "Current queue length",
            min_value=0, max_value=200, value=int(queue_len),
            key="missed_queue_len"
        )

    if missed_token_id:
        suggestion = get_recovery_suggestion(
            current_queue_length=int(missed_queue_len),
            avg_service_time=service_time,
            num_counters=counters,
        )

        st.markdown('<p class="section-header">Step 2 â€” Choose Recovery Mode</p>', unsafe_allow_html=True)
        st.markdown(f"<small style='color:#5dbdab'>ðŸ’¡ {suggestion['reason']}</small>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        opt_col1, opt_col2 = st.columns(2)

        is_rec_fixed = suggestion["recommended_mode"] == "fixed_buffer"
        is_rec_after = suggestion["recommended_mode"] == "after_queue"

        with opt_col1:
            rec_badge = '<div class="badge-rec">â­ Recommended</div><br>' if is_rec_fixed else ""
            st.markdown(f"""
            <div class="option-card {'recommended' if is_rec_fixed else ''}">
                {rec_badge}
                <div class="option-title">âš¡ Next Available Slot</div>
                <div class="option-wait">{suggestion['wait_fixed']} min</div>
                <div class="option-desc">
                    Jump in as soon as there's a gap.<br>
                    Best when queue is short or empty.<br>
                    Buffer: {suggestion['buffer_size']} tokens ahead of you.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("âš¡ Use Next Available Slot", use_container_width=True, key="btn_fixed"):
                st.session_state["recovery_mode"]    = "fixed_buffer"
                st.session_state["trigger_recovery"] = True

        with opt_col2:
            rec_badge = '<div class="badge-rec">â­ Recommended</div><br>' if is_rec_after else ""
            st.markdown(f"""
            <div class="option-card {'recommended' if is_rec_after else ''}">
                {rec_badge}
                <div class="option-title">ðŸ• After Current Queue</div>
                <div class="option-wait">{suggestion['wait_after_queue']} min</div>
                <div class="option-desc">
                    Placed after everyone currently waiting.<br>
                    Fair when queue is long.<br>
                    Queue: {suggestion['queue_length']} people ahead.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("ðŸ• Place After Queue", use_container_width=True, key="btn_after"):
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
                st.warning(f"âš ï¸ {mark_result['error']}")
                if existing_rec:
                    st.markdown(f"""
                    <div class="recovery-card">
                        <div class="recovery-label">YOUR EXISTING RECOVERY TOKEN</div>
                        <div class="recovery-new-token">{existing_rec.get('token_number', 'â€”')}</div>
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
                st.markdown('<p class="section-header">âœ… Recovery Token Issued</p>', unsafe_allow_html=True)

                st.markdown(f"""
                <div class="recovery-card">
                    <div class="recovery-label">YOUR NEW TOKEN NUMBER</div>
                    <div class="recovery-new-token">{rec['new_token']}</div>
                    <div class="recovery-label">New Token ID: {rec['recovery_id']}</div>
                    <br>
                    <div style="font-size:1rem; color:#f0e080;">
                        ðŸ“ {rec['place_name']}<br>
                        ðŸ• Estimated wait: <strong>{rec['estimated_wait']} minutes</strong><br>
                        ðŸ‘¥ {rec['tokens_ahead']} tokens before you<br>
                        ðŸ“Œ Placed at: {rec['mode_label']}<br>
                        ðŸ•’ Issued at: {rec['issued_at']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.session_state["my_token_id"] = rec["recovery_id"]
                st.success(f"âœ… New token issued! Save your new Token ID: **{rec['recovery_id']}**")

                phone = rec.get("user_phone", "")
                if phone:
                    sms_msg = (
                        f"CiviQ Que â€” Missed Token Recovery\n"
                        f"Hi {rec['user_name']},\n"
                        f"Your missed token has been recovered.\n"
                        f"New Token: {rec['new_token']}\n"
                        f"New Token ID: {rec['recovery_id']}\n"
                        f"Place: {rec['place_name']}\n"
                        f"Est. Wait: {rec['estimated_wait']} min\n"
                        f"Placed: {rec['mode_label']}"
                    )
                    sms_result = send_sms_alert(phone, sms_msg)
                    if sms_result["status"] == "sent":
                        st.success(f"ðŸ“± Recovery details sent via SMS! SID: {sms_result['sid']}")
                    elif sms_result["status"] == "not_configured":
                        st.info("â„¹ï¸ Add Twilio credentials to .env to send recovery SMS.")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CHARTS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<p class="section-header">ðŸ“ˆ Queue Forecast</p>', unsafe_allow_html=True)
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
        height=280,
        margin=dict(t=20, b=20),
        plot_bgcolor="#0f3d3d",
        paper_bgcolor="#0a2a2a",
        font=dict(color="#cce8e1"),
        xaxis=dict(gridcolor="#1a5a5a", tickfont=dict(color="#5dbdab")),
        yaxis=dict(gridcolor="#1a5a5a", tickfont=dict(color="#5dbdab")),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown('<p class="section-header">ðŸ”¥ Busy Hours Heatmap</p>', unsafe_allow_html=True)
    if df is not None:
        hm    = (df.groupby(["day_name", "hour_of_day"])["wait_time_minutes"]
                   .mean().round(1).reset_index())
        pivot = (hm.pivot(index="day_name", columns="hour_of_day", values="wait_time_minutes")
                   .reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]))
        fig2  = px.imshow(
            pivot,
            color_continuous_scale="Teal",
            labels=dict(x="Hour", y="", color="Wait (min)"),
            aspect="auto"
        )
        fig2.update_layout(
            height=280,
            margin=dict(t=20, b=20),
            plot_bgcolor="#0f3d3d",
            paper_bgcolor="#0a2a2a",
            font=dict(color="#cce8e1"),
            xaxis=dict(tickfont=dict(color="#5dbdab")),
            yaxis=dict(tickfont=dict(color="#5dbdab")),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Run generate_dataset.py and train_models.py first.")


# â”€â”€ Best times â”€â”€
st.markdown('<p class="section-header">âœ… Best Times to Visit</p>', unsafe_allow_html=True)
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
        bdf.index = ["ðŸ¥‡","ðŸ¥ˆ","ðŸ¥‰","4ï¸âƒ£","5ï¸âƒ£"]
        st.dataframe(bdf, use_container_width=True)
else:
    st.info("Run train_models.py to see best times.")


# â”€â”€ Prediction history â”€â”€
st.markdown("---")
st.markdown('<p class="section-header">ðŸ—‚ï¸ Prediction History</p>', unsafe_allow_html=True)
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
    "<center><small style='color:#5dbdab'>CiviQ Que â€” Smart Queue Intelligence System Â· "
    "Built by Pramod Haladkar Â· "
    "Powered by XGBoost + Random Forest + Twilio + Streamlit</small></center>",
    unsafe_allow_html=True
)
