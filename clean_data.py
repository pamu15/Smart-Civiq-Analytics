
import pandas as pd
import numpy as np
import os

INPUT_FILE   = "data/raw_queue_data.csv"
OUTPUT_FILE  = "data/cleaned_queue_data.csv"
SUMMARY_FILE = "data/feature_summary.csv"


def clean_data():
    print("=" * 55)
    print("  CiviQ Que — Data Cleaning (Updated)")
    print("=" * 55)

    # ── Load ──────────────────────────────────────
    df = pd.read_csv(INPUT_FILE, parse_dates=["datetime"])
    print(f"\n  Loaded : {len(df):,} rows  |  {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns)}")

    # ── Check missing values ──────────────────────
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(f"\n  Missing values found:")
        print(missing[missing > 0].to_string())
        df.dropna(inplace=True)
        print(f"  Dropped nulls. Remaining: {len(df):,}")
    else:
        print("\n  No missing values found")

    # ── Remove duplicates ─────────────────────────
    before = len(df)
    df.drop_duplicates(subset=["datetime", "place_name"], inplace=True)
    removed = before - len(df)
    print(f"  Duplicates removed: {removed}")

    # ── Remove outliers (IQR method) ──────────────
    print("\n  Removing outliers...")
    for col in ["wait_time_minutes", "current_queue_length"]:
        Q1    = df[col].quantile(0.25)
        Q3    = df[col].quantile(0.75)
        IQR   = Q3 - Q1
        lower = Q1 - 3 * IQR
        upper = Q3 + 3 * IQR
        before = len(df)
        df = df[(df[col] >= lower) & (df[col] <= upper)]
        removed = before - len(df)
        if removed:
            print(f"    Outliers removed from {col}: {removed} rows")
        else:
            print(f"    {col}: no outliers found")

    # ── Encode place_type ─────────────────────────
    place_type_map = {
        "Government": 0,
        "Hospital":   1,
        "Bank":       2,
        "Temple":     3,
        "Post Office":4,
    }
    df["place_type_encoded"] = df["place_type"].map(place_type_map).fillna(0).astype(int)

    # ── Encode season ─────────────────────────────
    season_map = {
        "Winter":  0,
        "Summer":  1,
        "Monsoon": 2,
        "Autumn":  3,
    }
    df["season_encoded"] = df["season"].map(season_map).fillna(0).astype(int)

    # ── Weather score ─────────────────────────────
    weather_map = {"Sunny": 1.0, "Cloudy": 0.85, "Rainy": 0.65, "Stormy": 0.4}
    df["weather_score"] = df["weather"].map(weather_map)

    # ── Rush hour flag ────────────────────────────
    # Weekday 9–11 AM or 4–6 PM
    df["is_rush_hour"] = (
        (df["is_weekend"] == 0) &
        (df["hour_of_day"].isin([9, 10, 17, 18]))
    ).astype(int)

    # ── Counter efficiency ratio ──────────────────
    df["counter_efficiency"] = (
        df["num_counters_open"] / df["current_queue_length"].replace(0, 1)
    ).round(3)

    # ── Staff to counter ratio ────────────────────
    df["staff_counter_ratio"] = (
        df["staff_on_duty"] / df["num_counters_open"].replace(0, 1)
    ).round(3)

    # ── Cyclical time encoding ────────────────────
    # Helps ML models understand circular nature of time
    df["hour_sin"]  = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"]  = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["dow_sin"]   = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"]   = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # ── Alert level ───────────────────────────────
    # 0 = Normal (<10 min), 1 = Moderate (10–25 min), 2 = High (>25 min)
    df["alert_level"] = pd.cut(
        df["wait_time_minutes"],
        bins=[-1, 10, 25, float("inf")],
        labels=[0, 1, 2]
    ).astype(int)

    # ── Festival surge flag ───────────────────────
    # Make sure column exists
    if "is_festival" not in df.columns:
        df["is_festival"] = 0

    if "festival_multiplier" not in df.columns:
        df["festival_multiplier"] = 1.0

    # ── Final column order ────────────────────────
    feature_cols = [
        # Identifiers
        "datetime", "date", "place_name", "place_type", "place_type_encoded",

        # Time features
        "hour_of_day", "day_of_week", "day_name",
        "month", "month_name", "season", "season_encoded",
        "is_weekend", "is_holiday", "is_rush_hour", "is_festival",

        # Weather
        "weather", "weather_score",

        # Queue features
        "current_queue_length", "num_counters_open",
        "staff_on_duty", "avg_service_time",
        "counter_efficiency", "staff_counter_ratio",

        # Multipliers
        "peak_multiplier", "festival_multiplier",

        # Cyclical encodings
        "hour_sin", "hour_cos",
        "dow_sin",  "dow_cos",
        "month_sin","month_cos",

        # Targets
        "wait_time_minutes", "is_overcrowded", "alert_level",
    ]

    # Keep only columns that actually exist in the dataframe
    df = df[[c for c in feature_cols if c in df.columns]]

    # ── Save cleaned data ─────────────────────────
    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    # ── Feature summary ───────────────────────────
    summary = df.describe().T
    summary.to_csv(SUMMARY_FILE)

    # ── Print results ─────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"  Cleaning complete!")
    print(f"{'=' * 55}")
    print(f"  Final shape  : {df.shape[0]:,} rows  ×  {df.shape[1]} columns")
    print(f"  Saved to     : {OUTPUT_FILE}")
    print(f"  Summary at   : {SUMMARY_FILE}")

    print(f"\n── Rows per place ──")
    if "place_name" in df.columns:
        for name, cnt in df["place_name"].value_counts().items():
            print(f"   {name:<35} {cnt:>5} rows")

    print(f"\n── Alert level distribution ──")
    for level, cnt in df["alert_level"].value_counts().sort_index().items():
        label = {0:"Normal", 1:"Moderate", 2:"High"}[level]
        pct   = cnt / len(df) * 100
        print(f"   Level {level} ({label:<10}): {cnt:>5} rows  ({pct:.1f}%)")

    print(f"\n── Wait time stats ──")
    print(f"   Min  : {df['wait_time_minutes'].min():.1f} min")
    print(f"   Max  : {df['wait_time_minutes'].max():.1f} min")
    print(f"   Mean : {df['wait_time_minutes'].mean():.1f} min")
    print(f"   Std  : {df['wait_time_minutes'].std():.1f} min")

    print(f"\n── Queue length stats ──")
    print(f"   Min  : {df['current_queue_length'].min()}")
    print(f"   Max  : {df['current_queue_length'].max()}")
    print(f"   Mean : {df['current_queue_length'].mean():.1f}")

    print(f"\n── Sample rows ──")
    sample_cols = [
        "place_name", "hour_of_day", "day_name",
        "current_queue_length", "wait_time_minutes",
        "alert_level", "weather", "season"
    ]
    print(df[[c for c in sample_cols if c in df.columns]].head(5).to_string(index=False))

    return df


if __name__ == "__main__":
    df = clean_data()
