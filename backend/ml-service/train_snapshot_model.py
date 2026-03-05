"""
VITAL-GUARD AI — Snapshot Model Training
Trains a Random Forest model on current vital signs to predict risk score and category.
"""
import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score, classification_report

FEATURES = ["heart_rate", "respiratory_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "snapshot_model.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "snapshot_dataset.csv")


def train():
    print("Loading snapshot dataset...")
    df = pd.read_csv(DATA_PATH)

    X = df[FEATURES].values
    y_score = df["risk_score"].values
    y_cat = df["risk_category"].values

    X_train, X_test, y_score_train, y_score_test, y_cat_train, y_cat_test = train_test_split(
        X, y_score, y_cat, test_size=0.2, random_state=42
    )

    # Train regression model for risk score
    print("Training risk score regressor...")
    regressor = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    regressor.fit(X_train, y_score_train)
    score_pred = regressor.predict(X_test)
    mae = mean_absolute_error(y_score_test, score_pred)
    print(f"  MAE: {mae:.2f}")

    # Train classifier for risk category
    print("Training risk category classifier...")
    classifier = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    classifier.fit(X_train, y_cat_train)
    cat_pred = classifier.predict(X_test)
    acc = accuracy_score(y_cat_test, cat_pred)
    print(f"  Accuracy: {acc:.4f}")
    print(classification_report(y_cat_test, cat_pred))

    # Feature importances
    importances = regressor.feature_importances_
    print("Feature importances:")
    for feat, imp in sorted(zip(FEATURES, importances), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.4f}")

    # Save model bundle
    model_bundle = {
        "regressor": regressor,
        "classifier": classifier,
        "features": FEATURES,
        "feature_importances": dict(zip(FEATURES, importances.tolist())),
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model_bundle, f)
    print(f"Snapshot model saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
