"""
VITAL-GUARD AI — Trend Model Training
Trains a Gradient Boosting model on sliding-window vital sign trends.
"""
import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score, classification_report

MODEL_PATH = os.path.join(os.path.dirname(__file__), "trend_model.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "trend_dataset.csv")
WINDOW = 10


def train():
    print("Loading trend dataset...")
    df = pd.read_csv(DATA_PATH)

    feature_cols = [c for c in df.columns if c not in ["risk_score", "risk_category", "hours_to_deterioration"]]
    X = df[feature_cols].values
    y_score = df["risk_score"].values
    y_cat = df["risk_category"].values
    y_hours = df["hours_to_deterioration"].values

    X_train, X_test, y_score_train, y_score_test, y_cat_train, y_cat_test, y_hours_train, y_hours_test = train_test_split(
        X, y_score, y_cat, y_hours, test_size=0.2, random_state=42
    )

    # Risk score regressor
    print("Training trend risk regressor...")
    regressor = GradientBoostingRegressor(n_estimators=150, max_depth=5, random_state=42)
    regressor.fit(X_train, y_score_train)
    pred = regressor.predict(X_test)
    print(f"  MAE (risk): {mean_absolute_error(y_score_test, pred):.2f}")

    # Risk category classifier
    print("Training trend risk classifier...")
    classifier = GradientBoostingClassifier(n_estimators=150, max_depth=5, random_state=42)
    classifier.fit(X_train, y_cat_train)
    cat_pred = classifier.predict(X_test)
    print(f"  Accuracy: {accuracy_score(y_cat_test, cat_pred):.4f}")
    print(classification_report(y_cat_test, cat_pred))

    # Hours-to-deterioration regressor
    print("Training time-to-deterioration regressor...")
    hours_regressor = GradientBoostingRegressor(n_estimators=150, max_depth=5, random_state=42)
    hours_regressor.fit(X_train, y_hours_train)
    hours_pred = hours_regressor.predict(X_test)
    print(f"  MAE (hours): {mean_absolute_error(y_hours_test, hours_pred):.2f}")

    # Feature importances
    importances = regressor.feature_importances_

    model_bundle = {
        "regressor": regressor,
        "classifier": classifier,
        "hours_regressor": hours_regressor,
        "feature_cols": feature_cols,
        "feature_importances": dict(zip(feature_cols, importances.tolist())),
        "window": WINDOW,
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model_bundle, f)
    print(f"Trend model saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
