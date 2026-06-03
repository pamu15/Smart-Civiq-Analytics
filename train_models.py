
import pandas as pd
import numpy as np
import pickle
import os
import json
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection  import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble         import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics          import (
    mean_absolute_error, mean_squared_error, r2_score,
    classification_report, accuracy_score, f1_score
)
from xgboost import XGBRegressor

# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────
INPUT_FILE = "data/cleaned_queue_data.csv"
MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# UPDATED FEATURE SET
# Includes new columns from updated dataset
# ─────────────────────────────────────────────
BASE_FEATURES = [
    # Time
    "hour_of_day", "day_of_week", "month",
    "is_weekend", "is_holiday", "is_rush_hour",
    "is_festival",

    # Place
    "place_type_encoded",

    # Season
    "season_encoded",

    # Queue
    "current_queue_length", "num_counters_open",
    "avg_service_time", "staff_on_duty",

    # Engineered
    "weather_score", "counter_efficiency", "staff_counter_ratio",
    "festival_multiplier",

    # Cyclical encodings
    "hour_sin", "hour_cos",
    "dow_sin",  "dow_cos",
    "month_sin","month_cos",
]


# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
def load_data():
    print("=" * 55)
    print("  CiviQ Que — Model Training (Updated)")
    print("=" * 55)

    global BASE_FEATURES

    df = pd.read_csv(INPUT_FILE, parse_dates=["datetime"])
    print(f"\n  Data loaded : {len(df):,} rows  |  {df.shape[1]} columns")

    # Check all required features are present
    missing_cols = [c for c in BASE_FEATURES if c not in df.columns]
    

    # Keep only existing features
    BASE_FEATURES = [c for c in BASE_FEATURES if c in df.columns]
    print(f"  Features used: {len(BASE_FEATURES)}")

    return df


# ─────────────────────────────────────────────
# SAVE MODEL
# ─────────────────────────────────────────────
def save_model(model, filename):
    path = os.path.join(MODELS_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    size = os.path.getsize(path) / 1024
    print(f"  Saved: {path}  ({size:.1f} KB)")


# ═════════════════════════════════════════════
# MODEL 1 — Wait Time Predictor (XGBoost)
# ═════════════════════════════════════════════
def train_wait_time_model(df):
    print("\n" + "─" * 55)
    print("  Model 1 — Wait Time Predictor  (XGBoost)")
    

    X = df[BASE_FEATURES]
    y = df["wait_time_minutes"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"  Train: {len(X_train):,} rows  |  Test: {len(X_test):,} rows")

    print("  Tuning hyperparameters (GridSearchCV)...")
    param_grid = {
        "n_estimators":     [100, 200, 300],
        "max_depth":        [4, 6, 8],
        "learning_rate":    [0.05, 0.1],
        "subsample":        [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
    }
    xgb  = XGBRegressor(random_state=42, eval_metric="rmse", verbosity=0)
    grid = GridSearchCV(
        xgb, param_grid,
        cv=3, scoring="neg_mean_absolute_error",
        n_jobs=-1, verbose=0
    )
    grid.fit(X_train, y_train)
    best = grid.best_estimator_

    y_pred = best.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    rmse   = np.sqrt(mean_squared_error(y_test, y_pred))
    r2     = r2_score(y_test, y_pred)

    print(f"\n  Best params  : {grid.best_params_}")
    print(f"  MAE          : {mae:.2f} minutes")
    print(f"  RMSE         : {rmse:.2f} minutes")
    print(f"  R² Score     : {r2:.4f}")

    # Top features
    importances = pd.Series(
        best.feature_importances_, index=BASE_FEATURES
    ).sort_values(ascending=False)
    print(f"\n  Top 5 important features:")
    for feat, imp in importances.head(5).items():
        bar = "█" * int(imp * 100)
        print(f"    {feat:<30} {imp:.4f}  {bar}")

    # Cross validation
    cv = cross_val_score(best, X, y, cv=5, scoring="r2")
    print(f"\n  Cross-val R² : {cv.mean():.4f} ± {cv.std():.4f}")

    save_model(best, "wait_time_model.pkl")

    return {
        "model":       "Wait Time Predictor",
        "algorithm":   "XGBoost Regression",
        "mae":         round(mae, 2),
        "rmse":        round(rmse, 2),
        "r2":          round(r2, 4),
        "cv_r2_mean":  round(cv.mean(), 4),
    }


# ═════════════════════════════════════════════
# MODEL 2 — Queue Length Forecaster (Random Forest)
# ═════════════════════════════════════════════
def train_queue_forecast_model(df):
    print("\n" + "─" * 55)
    print("  Model 2 — Queue Length Forecaster  (Random Forest)")
    print("─" * 55)

    df = df.copy().sort_values(["place_name", "datetime"]).reset_index(drop=True)

    # Create future queue targets (next 1hr and 2hr for same place)
    df["queue_next_1h"] = df.groupby("place_name")["current_queue_length"].shift(-1)
    df["queue_next_2h"] = df.groupby("place_name")["current_queue_length"].shift(-2)
    df = df.dropna(subset=["queue_next_1h", "queue_next_2h"])

    X = df[BASE_FEATURES]
    y = df[["queue_next_1h", "queue_next_2h"]]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"  Train: {len(X_train):,} rows  |  Test: {len(X_test):,} rows")

    print("  Training multi-output Random Forest...")
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        n_jobs=-1,
        random_state=42
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae_1h = mean_absolute_error(y_test["queue_next_1h"], y_pred[:, 0])
    mae_2h = mean_absolute_error(y_test["queue_next_2h"], y_pred[:, 1])
    r2_1h  = r2_score(y_test["queue_next_1h"], y_pred[:, 0])
    r2_2h  = r2_score(y_test["queue_next_2h"], y_pred[:, 1])

    print(f"\n  1-hour forecast  →  MAE: {mae_1h:.1f} people  |  R²: {r2_1h:.4f}")
    print(f"  2-hour forecast  →  MAE: {mae_2h:.1f} people  |  R²: {r2_2h:.4f}")

    save_model(model, "queue_length_model.pkl")

    return {
        "model":     "Queue Length Forecaster",
        "algorithm": "Random Forest (multi-output)",
        "mae_1h":    round(mae_1h, 2),
        "mae_2h":    round(mae_2h, 2),
        "r2_1h":     round(r2_1h, 4),
        "r2_2h":     round(r2_2h, 4),
    }


# ═════════════════════════════════════════════
# MODEL 3 — Overcrowding Alert (Classifier)
# ═════════════════════════════════════════════
def train_alert_model(df):
    print("\n" + "─" * 55)
    print("  Model 3 — Overcrowding Alert  (Random Forest Classifier)")
    print("─" * 55)

    X = df[BASE_FEATURES]
    y = df["alert_level"]   # 0=Normal, 1=Moderate, 2=High

    print(f"  Class distribution:")
    for level, count in y.value_counts().sort_index().items():
        label = {0:"Normal", 1:"Moderate", 2:"High"}[level]
        pct   = count / len(y) * 100
        bar   = "█" * int(pct / 2)
        print(f"    Level {level} ({label:<10}): {count:>6} rows  ({pct:.1f}%)  {bar}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n  Train: {len(X_train):,} rows  |  Test: {len(X_test):,} rows")

    print("  Tuning hyperparameters...")
    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth":    [6, 10, None],
        "class_weight": ["balanced", None],
    }
    rf   = RandomForestClassifier(random_state=42)
    grid = GridSearchCV(
        rf, param_grid,
        cv=3, scoring="f1_macro",
        n_jobs=-1, verbose=0
    )
    grid.fit(X_train, y_train)
    best = grid.best_estimator_

    y_pred   = best.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1       = f1_score(y_test, y_pred, average="macro")

    label_map          = {0:"Normal", 1:"Moderate", 2:"High"}
    present_labels     = sorted(y.unique())
    present_label_names = [label_map[l] for l in present_labels]

    print(f"\n  Best params  : {grid.best_params_}")
    print(f"  Accuracy     : {accuracy*100:.2f}%")
    print(f"  F1 (macro)   : {f1:.4f}")
    print(f"\n  Classification Report:")
    print(classification_report(
        y_test, y_pred,
        labels=present_labels,
        target_names=present_label_names
    ))

    save_model(best, "alert_model.pkl")

    return {
        "model":     "Overcrowding Alert",
        "algorithm": "Random Forest Classifier",
        "accuracy":  round(accuracy * 100, 2),
        "f1_macro":  round(f1, 4),
    }


# ═════════════════════════════════════════════
# MODEL 4 — Best Time Recommender (Per Place)
# ═════════════════════════════════════════════
def train_best_time_model(df):
    print("\n" + "─" * 55)
    print("  Model 4 — Best Time Recommender  (Pattern Analysis)")
    print("─" * 55)

    results = {}

    # Overall heatmap across all places
    heatmap = (
        df.groupby(["day_of_week", "hour_of_day"])["wait_time_minutes"]
        .mean().round(1).reset_index()
    )
    day_map = {0:"Monday",1:"Tuesday",2:"Wednesday",
               3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
    heatmap["day_name"] = heatmap["day_of_week"].map(day_map)

    best_slots  = heatmap.nsmallest(5, "wait_time_minutes")[
        ["day_name","hour_of_day","wait_time_minutes"]
    ].reset_index(drop=True)

    worst_slots = heatmap.nlargest(5, "wait_time_minutes")[
        ["day_name","hour_of_day","wait_time_minutes"]
    ].reset_index(drop=True)

    print("\n  Top 5 BEST times (overall — shortest wait):")
    for _, row in best_slots.iterrows():
        print(f"    {row['day_name']:<12} {int(row['hour_of_day']):02d}:00"
              f"  →  {row['wait_time_minutes']} min avg")

    print("\n  Top 5 WORST times (overall — longest wait):")
    for _, row in worst_slots.iterrows():
        print(f"    {row['day_name']:<12} {int(row['hour_of_day']):02d}:00"
              f"  →  {row['wait_time_minutes']} min avg")

    # Per-place best times
    print("\n  Per-place best time to visit:")
    per_place = {}
    if "place_name" in df.columns:
        for place in df["place_name"].unique():
            place_df = df[df["place_name"] == place]
            ph = (
                place_df.groupby(["day_of_week","hour_of_day"])["wait_time_minutes"]
                .mean().round(1).reset_index()
            )
            ph["day_name"] = ph["day_of_week"].map(day_map)
            best = ph.nsmallest(3, "wait_time_minutes")[
                ["day_name","hour_of_day","wait_time_minutes"]
            ].reset_index(drop=True)
            per_place[place] = best.to_dict(orient="records")
            top = best.iloc[0]
            print(f"    {place:<35} → {top['day_name']} {int(top['hour_of_day']):02d}:00"
                  f"  ({top['wait_time_minutes']} min)")

    # Hourly and daily averages
    hourly_avg = (
        df.groupby("hour_of_day")["wait_time_minutes"]
        .mean().round(1).to_dict()
    )
    daily_avg = (
        df.groupby("day_name")["wait_time_minutes"]
        .mean().round(1).to_dict()
    )

    # Festival impact
    if "is_festival" in df.columns:
        festival_avg    = df[df["is_festival"]==1]["wait_time_minutes"].mean()
        non_festival_avg = df[df["is_festival"]==0]["wait_time_minutes"].mean()
        print(f"\n  Festival days avg wait   : {festival_avg:.1f} min")
        print(f"  Normal days avg wait     : {non_festival_avg:.1f} min")
        print(f"  Festival surge factor    : {festival_avg/max(non_festival_avg,1):.2f}x")

    # Pack everything
    best_time_data = {
        "heatmap":      heatmap.to_dict(orient="records"),
        "best_slots":   best_slots.to_dict(orient="records"),
        "worst_slots":  worst_slots.to_dict(orient="records"),
        "hourly_avg":   {int(k): v for k, v in hourly_avg.items()},
        "daily_avg":    daily_avg,
        "per_place":    per_place,
    }

    save_model(best_time_data, "best_time_data.pkl")

    json_path = os.path.join(MODELS_DIR, "best_time_data.json")
    with open(json_path, "w") as f:
        json.dump(best_time_data, f, indent=2)
    print(f"\n  Also saved as JSON: {json_path}")

    return {
        "model":     "Best Time Recommender",
        "algorithm": "Historical Pattern Analysis",
        "best_slot": f"{best_slots.iloc[0]['day_name']} "
                     f"{int(best_slots.iloc[0]['hour_of_day'])}:00",
        "best_wait": best_slots.iloc[0]["wait_time_minutes"],
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    df = load_data()

    results = []
    results.append(train_wait_time_model(df))
    results.append(train_queue_forecast_model(df))
    results.append(train_alert_model(df))
    results.append(train_best_time_model(df))

    # ── Final Summary ──────────────────────────
    print("\n" + "=" * 55)
    print("  TRAINING COMPLETE — Summary")
    print("=" * 55)
    for r in results:
        print(f"\n  {r['model']}")
        print(f"    Algorithm : {r['algorithm']}")
        for k, v in r.items():
            if k not in ("model", "algorithm"):
                print(f"    {k:<16}: {v}")

    print(f"\n  All models saved in: {MODELS_DIR}/")
    print(f"\n  Files:")
    for fname in sorted(os.listdir(MODELS_DIR)):
        size = os.path.getsize(os.path.join(MODELS_DIR, fname)) / 1024
        print(f"    {fname:<40} {size:.1f} KB")



if __name__ == "__main__":
    main()