
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

np.random.seed(42)
random.seed(42)


START_DATE      = datetime(2023, 1, 1, 8, 0)  
END_DATE        = datetime(2025, 12, 31, 20, 0)
OPERATING_HOURS = range(8, 21)                  # 8 AM to 8 PM
MAX_COUNTERS    = 8                             
OUTPUT_FILE     = "data/raw_queue_data.csv"

# ─────────────────────────────────────────────
# PLACE TYPES (4 types, each with own pattern)
# ─────────────────────────────────────────────
PLACES = [
    {
        "name":        "RTO Office Pune",
        "type":        "Government",
        "base_demand": 90,
        "peak_hours":  [9, 10, 11, 15, 16],   # morning + post-lunch
        "max_counters": 6,
        "closed_on":   ["Sunday"],
    },
    {
        "name":        "City Hospital OPD",
        "type":        "Hospital",
        "base_demand": 120,
        "peak_hours":  [9, 10, 11, 12],        # morning heavy
        "max_counters": 8,
        "closed_on":   [],                     # open all days
    },
    {
        "name":        "SBI Bank Branch",
        "type":        "Bank",
        "base_demand": 70,
        "peak_hours":  [10, 11, 14, 15],       # standard banking hours peak
        "max_counters": 5,
        "closed_on":   ["Saturday", "Sunday"],
    },
    {
        "name":        "Passport Seva Kendra",
        "type":        "Government",
        "base_demand": 80,
        "peak_hours":  [9, 10, 14, 15],
        "max_counters": 6,
        "closed_on":   ["Saturday", "Sunday"],
    },
    
]

# ─────────────────────────────────────────────
# INDIA PUBLIC HOLIDAYS (2023 + 2024 + 2025)
# ─────────────────────────────────────────────
HOLIDAYS = set([
    # 2023
    "2023-01-26", "2023-03-08", "2023-04-04", "2023-04-14",
    "2023-08-15", "2023-10-02", "2023-10-24", "2023-11-12",
    "2023-11-27", "2023-12-25",
    # 2024
    "2024-01-26", "2024-03-25", "2024-04-14", "2024-04-17",
    "2024-08-15", "2024-10-02", "2024-10-12", "2024-11-01",
    "2024-11-15", "2024-12-25",
    # 2025
    "2025-01-26", "2025-03-25", "2025-04-14", "2025-04-17",
    "2025-08-15", "2025-10-02", "2025-10-12", "2025-11-01",
    "2025-11-15", "2025-12-25",
])

# ─────────────────────────────────────────────
# FESTIVAL SURGE DATES
# ─────────────────────────────────────────────
 
FESTIVAL_SURGES = {
    # date_str: multiplier
    "2023-10-23": 1.8, "2023-10-24": 2.0, "2023-10-25": 1.9,  # Diwali 2023
    "2023-03-07": 1.6, "2023-03-08": 1.7,                      # Holi 2023
    "2024-11-01": 2.0, "2024-11-02": 1.9, "2024-11-03": 1.7,  # Diwali 2024
    "2024-03-24": 1.6, "2024-03-25": 1.8,                      # Holi 2024
    "2025-10-20": 1.8, "2025-10-21": 2.0, "2025-10-22": 1.9,  # Diwali 2025
    "2025-03-13": 1.6, "2025-03-14": 1.7,                      # Holi 2025
}

WEATHER_OPTIONS = ["Sunny", "Cloudy", "Rainy", "Stormy"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_season(month):
    if month in [12, 1, 2]:   return "Winter"
    if month in [3, 4, 5]:    return "Summer"
    if month in [6, 7, 8, 9]: return "Monsoon"
    return "Autumn"


def get_peak_multiplier(hour, day_of_week, place):
    """Returns demand multiplier based on hour, day, and place type."""
    is_weekend = day_of_week >= 5

    if hour in place["peak_hours"]:
        base = 1.0
    elif hour in [h - 1 for h in place["peak_hours"]] or \
         hour in [h + 1 for h in place["peak_hours"]]:
        base = 0.75   # near-peak hours
    else:
        base = 0.4    # off-peak

    # Temples are busier on weekends
    if place["type"] == "Temple" and is_weekend:
        base *= 1.3

    # Banks/Govt offices are quieter on weekends (often closed)
    if place["type"] in ["Government", "Bank"] and is_weekend:
        base *= 0.5

    # Very early or very late → quiet
    if hour in [8, 20]:
        base *= 0.6

    return round(min(base, 1.0), 2)


def get_counters_open(hour, day_of_week, is_holiday, place):
    """Number of service counters open."""
    multiplier  = get_peak_multiplier(hour, day_of_week, place)
    max_c       = place["max_counters"]

    if is_holiday:
        counters = max(1, int(max_c * multiplier * 0.5))
    elif day_of_week >= 5:
        counters = max(1, int(max_c * multiplier * 0.7))
    else:
        counters = max(1, int(max_c * multiplier))

    return min(counters, max_c)


def get_weather_multiplier(weather):
    return {"Sunny": 1.0, "Cloudy": 0.9, "Rainy": 0.65, "Stormy": 0.35}.get(weather, 1.0)


def get_month_multiplier(month):
    return {
        1: 0.85, 2: 0.90, 3: 1.05, 4: 0.95,
        5: 0.90, 6: 0.85, 7: 0.80, 8: 0.95,
        9: 1.00, 10: 1.10, 11: 1.20, 12: 1.05
    }.get(month, 1.0)


def calculate_wait_time(queue_length, num_counters, avg_service_time):
    """Realistic wait time with noise."""
    if num_counters == 0 or queue_length == 0:
        return 0.0
    base_wait = (queue_length / num_counters) * avg_service_time
    noise     = np.random.normal(0, base_wait * 0.12)
    return round(max(0, base_wait + noise), 1)


def get_staff_on_duty(counters, is_holiday, day_of_week):
    """Total staff including support (1.5x to 2x counters)."""
    multiplier = 1.5 if is_holiday or day_of_week >= 5 else random.uniform(1.5, 2.2)
    return max(counters, int(counters * multiplier))


# ─────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────
def generate_dataset():
    print("=" * 55)
    print("  CiviQ Que — Dataset Generator (20,000+ rows)")
    print("=" * 55)

    records     = []
    holiday_set = HOLIDAYS

    weather_timeline = []
    for _ in range(1500):
        w = random.choices(
            WEATHER_OPTIONS,
            weights=[0.55, 0.25, 0.15, 0.05]
        )[0]
        for _ in range(random.randint(3, 8)):
            weather_timeline.append(w)

    weather_idx = 0

    for place in PLACES:
        print(f"\n  Generating data for: {place['name']} ({place['type']})")
        current_dt = START_DATE

        while current_dt <= END_DATE:
            hour     = current_dt.hour
            dow      = current_dt.weekday()   # 0=Mon, 6=Sun
            month    = current_dt.month
            date_str = current_dt.strftime("%Y-%m-%d")
            day_name = current_dt.strftime("%A")

            is_holiday = 1 if date_str in holiday_set else 0

            # Skip if place is closed on this day
            if day_name in place["closed_on"]:
                current_dt += timedelta(hours=1)
                weather_idx += 1
                continue

            # Only generate during operating hours
            if hour in OPERATING_HOURS:
                weather     = weather_timeline[weather_idx % len(weather_timeline)]
                w_mult      = get_weather_multiplier(weather)
                m_mult      = get_month_multiplier(month)
                p_mult      = get_peak_multiplier(hour, dow, place)
                fest_mult   = FESTIVAL_SURGES.get(date_str, 1.0)
                counters    = get_counters_open(hour, dow, is_holiday, place)
                staff       = get_staff_on_duty(counters, is_holiday, dow)

                base_demand = place["base_demand"]
                if is_holiday:
                    base_demand = int(base_demand * 0.5)

                # Queue with all multipliers + noise
                raw_queue = base_demand * p_mult * w_mult * m_mult * fest_mult
                noise     = np.random.normal(0, raw_queue * 0.15)
                queue_len = max(0, int(raw_queue + noise))

                # Service time varies by place type
                if place["type"] == "Hospital":
                    avg_service_time = round(np.random.uniform(5.0, 15.0), 1)
                elif place["type"] == "Temple":
                    avg_service_time = round(np.random.uniform(1.0, 4.0), 1)
                elif place["type"] == "Government":
                    avg_service_time = round(np.random.uniform(6.0, 12.0), 1)
                else:
                    avg_service_time = round(np.random.uniform(3.0, 8.0), 1)

                wait_time      = calculate_wait_time(queue_len, counters, avg_service_time)
                is_overcrowded = 1 if (queue_len > 60 or wait_time > 35) else 0
                season         = get_season(month)
                is_festival    = 1 if date_str in FESTIVAL_SURGES else 0

                records.append({
                    "datetime":              current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "date":                  date_str,
                    "place_name":            place["name"],
                    "place_type":            place["type"],
                    "hour_of_day":           hour,
                    "day_of_week":           dow,
                    "day_name":              day_name,
                    "month":                 month,
                    "month_name":            current_dt.strftime("%B"),
                    "season":                season,
                    "is_weekend":            1 if dow >= 5 else 0,
                    "is_holiday":            is_holiday,
                    "is_festival":           is_festival,
                    "weather":               weather,
                    "current_queue_length":  queue_len,
                    "num_counters_open":     counters,
                    "staff_on_duty":         staff,
                    "avg_service_time":      avg_service_time,
                    "wait_time_minutes":     wait_time,
                    "is_overcrowded":        is_overcrowded,
                    "peak_multiplier":       p_mult,
                    "festival_multiplier":   fest_mult,
                })

            weather_idx += 1
            current_dt += timedelta(hours=1)

    # ─────────────────────────────────────────
    # Build DataFrame
    # ─────────────────────────────────────────
    df = pd.DataFrame(records)

    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    # ─────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"  Dataset saved: {OUTPUT_FILE}")
    print(f"{'=' * 55}")
    print(f"  Total rows       : {len(df):,}")
    print(f"  Date range       : {df['date'].min()}  →  {df['date'].max()}")
    print(f"  Places covered   : {df['place_name'].nunique()}")
    print(f"  Columns          : {df.shape[1]}")

    print(f"\n── Rows per place ──")
    for name, cnt in df["place_name"].value_counts().items():
        print(f"   {name:<35} {cnt:>5} rows")

    print(f"\n── Queue Length ──")
    print(f"   Min  : {df['current_queue_length'].min()}")
    print(f"   Max  : {df['current_queue_length'].max()}")
    print(f"   Mean : {df['current_queue_length'].mean():.1f}")

    print(f"\n── Wait Time (minutes) ──")
    print(f"   Min  : {df['wait_time_minutes'].min()}")
    print(f"   Max  : {df['wait_time_minutes'].max():.1f}")
    print(f"   Mean : {df['wait_time_minutes'].mean():.1f}")

    print(f"\n── Overcrowded hours ──")
    print(f"   Count : {df['is_overcrowded'].sum():,} / {len(df):,} "
          f"({df['is_overcrowded'].mean()*100:.1f}%)")

    print(f"\n── Festival surge rows ──")
    print(f"   Count : {df['is_festival'].sum():,}")

    print(f"\n── Season distribution ──")
    print(df['season'].value_counts().to_string())

    print(f"\n── Weather distribution ──")
    print(df['weather'].value_counts().to_string())

    print(f"\n── Busiest hours (avg queue across all places) ──")
    busy = (df.groupby("hour_of_day")["current_queue_length"]
              .mean()
              .sort_values(ascending=False)
              .head(5)
              .round(1))
    print(busy.to_string())

    return df



if __name__ == "__main__":
    df = generate_dataset()
    print(f"\n  Done! Total rows generated: {len(df):,}")
    print("  Next step → run: python clean_data.py")