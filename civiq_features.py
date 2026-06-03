import os
import json
import random
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID",  "")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN",   "")
TWILIO_FROM_NUMBER  = os.getenv("TWILIO_FROM_NUMBER",  "")

INDIA_HOLIDAYS = {
    "2023-01-26": "Republic Day",
    "2023-03-08": "Holi",
    "2023-04-04": "Ram Navami",
    "2023-04-14": "Ambedkar Jayanti",
    "2023-08-15": "Independence Day",
    "2023-10-02": "Gandhi Jayanti",
    "2023-10-24": "Dussehra",
    "2023-11-12": "Diwali",
    "2023-11-27": "Guru Nanak Jayanti",
    "2023-12-25": "Christmas",
    "2024-01-26": "Republic Day",
    "2024-03-25": "Holi",
    "2024-04-14": "Ambedkar Jayanti",
    "2024-04-17": "Ram Navami",
    "2024-08-15": "Independence Day",
    "2024-10-02": "Gandhi Jayanti",
    "2024-10-12": "Dussehra",
    "2024-11-01": "Diwali",
    "2024-11-15": "Guru Nanak Jayanti",
    "2024-12-25": "Christmas",
    "2025-01-26": "Republic Day",
    "2025-03-14": "Holi",
    "2025-04-06": "Ram Navami",
    "2025-04-14": "Ambedkar Jayanti",
    "2025-08-15": "Independence Day",
    "2025-10-02": "Gandhi Jayanti",
    "2025-10-20": "Diwali",
    "2025-11-05": "Guru Nanak Jayanti",
    "2025-12-25": "Christmas",
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-04-14": "Ambedkar Jayanti",
    "2026-08-15": "Independence Day",
    "2026-10-02": "Gandhi Jayanti",
    "2026-12-25": "Christmas",
}

PLACE_CLOSED_DAYS = {
    "Bank":        ["Saturday", "Sunday"],
    "Government":  ["Sunday"],
    "Hospital":    [],
    "Post Office": ["Sunday"],
}

# Age threshold for senior priority
SENIOR_AGE_THRESHOLD = 70
SENIOR_BUFFER = 2   


# ─────────────────────────────────────────────
# FEATURE 1 — HOLIDAY CLOSURE ALERT
# ─────────────────────────────────────────────

def get_holiday_status(place_type="Government", check_date=None):
    if check_date is None:
        check_date = date.today()

    date_str = check_date.strftime("%Y-%m-%d")
    day_name = check_date.strftime("%A")

    if date_str in INDIA_HOLIDAYS:
        holiday_name = INDIA_HOLIDAYS[date_str]
        return {
            "is_open":       False,
            "status":        "Closed",
            "reason":        f"Public Holiday: {holiday_name}",
            "holiday_name":  holiday_name,
            "alert_message": f"⚠️ Closed today — {holiday_name} (Public Holiday)",
            "emoji":         "🔴",
        }

    closed_days = PLACE_CLOSED_DAYS.get(place_type, [])
    if day_name in closed_days:
        return {
            "is_open":       False,
            "status":        "Closed",
            "reason":        f"Weekly Off: {day_name}",
            "holiday_name":  None,
            "alert_message": f"⚠️ Closed today — Weekly off ({day_name})",
            "emoji":         "🔴",
        }

    return {
        "is_open":       True,
        "status":        "Open",
        "reason":        "Open today",
        "holiday_name":  None,
        "alert_message": f"✅ Open today ({day_name})",
        "emoji":         "🟢",
    }


def get_upcoming_closures(place_type="Government", days_ahead=7):
    today    = date.today()
    closures = []
    for i in range(1, days_ahead + 1):
        check  = today + timedelta(days=i)
        status = get_holiday_status(place_type=place_type, check_date=check)
        if not status["is_open"]:
            closures.append({
                "date":   check.strftime("%Y-%m-%d"),
                "day":    check.strftime("%A"),
                "reason": status["reason"],
            })
    return closures


# ─────────────────────────────────────────────
# FEATURE 2 — VIRTUAL TOKEN NUMBER SYSTEM
# ─────────────────────────────────────────────

def assign_token(place_name, user_name, user_phone,
                 current_token_number, token_store: dict,
                 user_age: int = 0):
    """
    Assigns a virtual token.
    - If user_age >= SENIOR_AGE_THRESHOLD (70), the person gets
      SENIOR_BUFFER tokens ahead instead of the usual 10–30,
      giving them priority placement near the front.
    """
    is_senior = user_age >= SENIOR_AGE_THRESHOLD

    if is_senior:
        tokens_ahead = SENIOR_BUFFER          
    else:
        tokens_ahead = random.randint(10, 30)

    your_token = current_token_number + tokens_ahead
    token_id   = f"TKN-{random.randint(1000, 9999)}"
    issued_at  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    token_data = {
        "token_id":           token_id,
        "token_number":       your_token,
        "current_token":      current_token_number,
        "tokens_ahead":       tokens_ahead,
        "user_name":          user_name,
        "user_phone":         user_phone,
        "user_age":           user_age,
        "is_senior":          is_senior,
        "place_name":         place_name,
        "issued_at":          issued_at,
        "status":             "Waiting",
        "estimated_wait_min": None,
        "is_missed":          False,
        "recovery_token":     None,
    }

    token_store[token_id] = token_data
    return token_data


def predict_token_wait(token_data, avg_service_time, num_counters):
    tokens_ahead    = token_data["tokens_ahead"]
    effective_speed = num_counters * (1 / avg_service_time)
    estimated_wait  = tokens_ahead / effective_speed
    noise           = random.uniform(-2, 2)
    estimated_wait  = round(max(1, estimated_wait + noise), 1)
    token_data["estimated_wait_min"] = estimated_wait
    return estimated_wait


def get_token_status(token_id, current_serving_number, token_store: dict):
    if token_id not in token_store:
        return {"error": "Token not found. Please check your token ID."}

    token     = token_store[token_id]
    remaining = token["token_number"] - current_serving_number
    name      = token["user_name"]

    if remaining <= 0:
        status  = "Called"
        message = f"🔔 {name}, Token {token['token_number']} — Please proceed to the counter NOW!"
        alert   = True
    elif remaining <= 3:
        status  = "Near"
        message = f"⚡ {name}, hurry! Only {remaining} tokens before yours ({token['token_number']}). Go to the counter."
        alert   = True
    elif remaining <= 8:
        status  = "Soon"
        message = f"⏳ {name}, {remaining} tokens before yours ({token['token_number']}). Start moving!"
        alert   = False
    else:
        status  = "Waiting"
        message = f"🕐 {name}, {remaining} tokens ahead. Your token: {token['token_number']}. Relax."
        alert   = False

    token["status"] = status

    return {
        "token_id":        token_id,
        "token_number":    token["token_number"],
        "current_serving": current_serving_number,
        "remaining":       max(0, remaining),
        "status":          status,
        "message":         message,
        "should_alert":    alert,
        "user_name":       token["user_name"],
        "user_phone":      token["user_phone"],
    }


# ─────────────────────────────────────────────
# FEATURE 3 — SMS ALERT (Twilio)
# ─────────────────────────────────────────────

def send_sms_alert(to_phone: str, message: str) -> dict:
    missing = []
    if not TWILIO_ACCOUNT_SID:  missing.append("TWILIO_ACCOUNT_SID")
    if not TWILIO_AUTH_TOKEN:   missing.append("TWILIO_AUTH_TOKEN")
    if not TWILIO_FROM_NUMBER:  missing.append("TWILIO_FROM_NUMBER")

    if missing:
        return {
            "status":  "not_configured",
            "message": f"Missing in .env: {', '.join(missing)}",
            "debug":   {
                "SID_loaded":   bool(TWILIO_ACCOUNT_SID),
                "Token_loaded": bool(TWILIO_AUTH_TOKEN),
                "From_loaded":  bool(TWILIO_FROM_NUMBER),
            }
        }

    if not to_phone.startswith("+"):
        return {
            "status":  "invalid_phone",
            "message": f"Phone must start with +country_code. Got: {to_phone}",
        }

    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        sms = client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=to_phone,
        )
        return {
            "status":  "sent",
            "sid":     sms.sid,
            "to":      to_phone,
            "message": message,
        }

    except ImportError:
        return {
            "status":  "error",
            "message": "Twilio not installed. Run: pip install twilio",
        }
    except Exception as e:
        return {
            "status":  "error",
            "message": str(e),
        }


def check_and_alert(token_id, current_serving_number,
                    avg_service_time, num_counters,
                    token_store: dict):
    status = get_token_status(token_id, current_serving_number, token_store)
    if "error" in status:
        return status

    token      = token_store[token_id]
    wait_time  = predict_token_wait(token, avg_service_time, num_counters)
    sms_result = None

    if status["should_alert"]:
        sms_message = (
            f"CiviQ Que Alert!\n"
            f"Hi {status['user_name']},\n"
            f"{status['message']}\n"
            f"Place: {token['place_name']}\n"
            f"Est. wait: {wait_time} min"
        )
        sms_result = send_sms_alert(status["user_phone"], sms_message)

    return {
        "token_status": status,
        "wait_time":    wait_time,
        "sms_result":   sms_result,
    }


# ─────────────────────────────────────────────
# FEATURE 4 — MISSED TOKEN RECOVERY
# ─────────────────────────────────────────────

def mark_token_missed(token_id: str, token_store: dict) -> dict:
    if token_id not in token_store:
        return {
            "success": False,
            "error":   "Token not found. Please check your Token ID.",
        }

    token = token_store[token_id]

    if token.get("recovery_token"):
        return {
            "success":        False,
            "error":          "A recovery token has already been issued for this token.",
            "recovery_token": token["recovery_token"],
        }

    if token.get("is_missed"):
        return {
            "success": False,
            "error":   "Token is already marked as missed.",
        }

    token["is_missed"] = True
    token["status"]    = "Missed"
    return {"success": True}


def get_recovery_suggestion(current_queue_length: int,
                             avg_service_time: float,
                             num_counters: int) -> dict:
    BUFFER_SIZE       = 5
    SHORT_QUEUE_LIMIT = 15

    effective_speed   = num_counters * (1.0 / max(avg_service_time, 1))

    wait_after_queue  = round(
        max(1, current_queue_length / effective_speed + random.uniform(-1, 1)), 1
    )

    buffer_tokens     = min(BUFFER_SIZE, max(1, current_queue_length))
    wait_fixed        = round(
        max(1, buffer_tokens / effective_speed + random.uniform(-1, 1)), 1
    )

    if current_queue_length <= SHORT_QUEUE_LIMIT:
        recommended = "fixed_buffer"
        reason      = (
            f"Queue is short ({current_queue_length} people). "
            "You can jump in quickly with just a small buffer."
        )
    else:
        recommended = "after_queue"
        reason      = (
            f"Queue is long ({current_queue_length} people). "
            "Placing you after the queue is fairer to others."
        )

    return {
        "recommended_mode": recommended,
        "wait_fixed":       wait_fixed,
        "wait_after_queue": wait_after_queue,
        "buffer_size":      buffer_tokens,
        "queue_length":     current_queue_length,
        "reason":           reason,
    }


def recover_missed_token(token_id: str,
                          current_serving_number: int,
                          current_queue_length: int,
                          avg_service_time: float,
                          num_counters: int,
                          token_store: dict,
                          recovery_mode: str = "fixed_buffer") -> dict:
    if token_id not in token_store:
        return {"success": False, "error": "Original token not found."}

    original  = token_store[token_id]
    is_senior = original.get("is_senior", False)

    if not original.get("is_missed"):
        return {
            "success": False,
            "error":   "Token has not been marked as missed yet. "
                       "Call mark_token_missed() first.",
        }

    if original.get("recovery_token"):
        return {
            "success":        False,
            "error":          "Recovery token already issued.",
            "recovery_token": original["recovery_token"],
        }

    BUFFER = 2 if is_senior else 5

    if recovery_mode == "fixed_buffer" or is_senior:
        tokens_ahead  = BUFFER
        new_token_num = current_serving_number + BUFFER
        if is_senior:
            mode_label = f"Senior priority — placed {BUFFER} tokens from current (age {original.get('user_age', '70+')})"
        else:
            mode_label = f"Next available slot (~{BUFFER} tokens ahead of current)"
    else:
        padding       = random.randint(1, 3)
        tokens_ahead  = current_queue_length + padding
        new_token_num = current_serving_number + tokens_ahead
        mode_label    = f"After current queue ({current_queue_length} people)"

    effective_speed  = num_counters * (1.0 / max(avg_service_time, 1))
    estimated_wait   = round(
        max(1, tokens_ahead / effective_speed + random.uniform(-1, 1)), 1
    )

    recovery_id   = f"TKN-{random.randint(1000, 9999)}"
    issued_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    recovery_data = {
        "token_id":           recovery_id,
        "token_number":       new_token_num,
        "current_token":      current_serving_number,
        "tokens_ahead":       tokens_ahead,
        "user_name":          original["user_name"],
        "user_phone":         original["user_phone"],
        "user_age":           original.get("user_age", 0),
        "is_senior":          is_senior,
        "place_name":         original["place_name"],
        "issued_at":          issued_at,
        "status":             "Waiting",
        "estimated_wait_min": estimated_wait,
        "is_missed":          False,
        "recovery_token":     None,
        "recovered_from":     token_id,
    }

    token_store[recovery_id]          = recovery_data
    original["recovery_token"]        = recovery_id
    original["status"]                = "Recovered"

    return {
        "success":        True,
        "recovery_id":    recovery_id,
        "new_token":      new_token_num,
        "tokens_ahead":   tokens_ahead,
        "estimated_wait": estimated_wait,
        "mode_label":     mode_label,
        "place_name":     original["place_name"],
        "user_name":      original["user_name"],
        "user_phone":     original["user_phone"],
        "user_age":       original.get("user_age", 0),
        "is_senior":      is_senior,
        "issued_at":      issued_at,
    }