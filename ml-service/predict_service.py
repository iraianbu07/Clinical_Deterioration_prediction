"""
VITAL-GUARD AI — Prediction Service
Loads trained models and provides risk predictions with explainability.
"""
import os
import pickle
import numpy as np

ML_DIR = os.path.dirname(__file__)
SNAPSHOT_MODEL_PATH = os.path.join(ML_DIR, "snapshot_model.pkl")
TREND_MODEL_PATH = os.path.join(ML_DIR, "trend_model.pkl")
TREND_WINDOW = 10

FEATURES = ["heart_rate", "respiratory_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"]

# Load models
_snapshot_model = None
_trend_model = None


def _load_snapshot():
    global _snapshot_model
    if _snapshot_model is None and os.path.exists(SNAPSHOT_MODEL_PATH):
        with open(SNAPSHOT_MODEL_PATH, "rb") as f:
            _snapshot_model = pickle.load(f)
    return _snapshot_model


def _load_trend():
    global _trend_model
    if _trend_model is None and os.path.exists(TREND_MODEL_PATH):
        with open(TREND_MODEL_PATH, "rb") as f:
            _trend_model = pickle.load(f)
    return _trend_model


def classify_risk(vgi: float) -> str:
    if vgi < 30:
        return "Stable"
    elif vgi < 50:
        return "Systemic Inflammation"
    elif vgi < 70:
        return "Cardiac Risk"
    elif vgi < 85:
        return "Respiratory Failure"
    else:
        return "Critical Deterioration"


def snapshot_predict(vitals: dict) -> dict:
    model = _load_snapshot()
    if model is None:
        return None

    X = np.array([[vitals[f] for f in FEATURES]])
    risk_score = float(model["regressor"].predict(X)[0])
    risk_score = max(0, min(100, risk_score))
    category = model["classifier"].predict(X)[0]

    importances = model.get("feature_importances", {})

    return {
        "risk_score": round(risk_score, 1),
        "risk_category": category,
        "feature_importances": importances,
    }


def trend_predict(history: list) -> dict:
    model = _load_trend()
    if model is None or len(history) < 2:
        return None

    window = model.get("window", TREND_WINDOW)

    # Use last `window` records, pad if less
    recent = history[-window:]
    row = []
    for record in recent:
        row.extend([
            record.get("heart_rate", 72),
            record.get("respiratory_rate", 16),
            record.get("spo2", 98),
            record.get("temperature", 37.0),
            record.get("systolic_bp", 120),
            record.get("diastolic_bp", 80),
        ])

    # Pad if fewer than window records
    while len(row) < window * 6:
        row = row[:6] + row  # repeat first record

    row = row[:window * 6]

    X = np.array([row])
    risk_score = float(model["regressor"].predict(X)[0])
    risk_score = max(0, min(100, risk_score))
    category = model["classifier"].predict(X)[0]
    hours = float(model["hours_regressor"].predict(X)[0])
    hours = max(0.5, hours)

    return {
        "risk_score": round(risk_score, 1),
        "risk_category": category,
        "estimated_hours": round(hours, 1),
    }


def compute_baseline(history: list) -> dict:
    if len(history) < 3:
        return {}
    baseline = {}
    for feat in FEATURES:
        key = feat
        vals = [h.get(key, 0) for h in history if key in h]
        if vals:
            baseline[key] = round(sum(vals) / len(vals), 1)
    return baseline


def compute_explanation(vitals: dict, baseline: dict, snapshot_result: dict) -> list:
    factors = []
    feature_importances = snapshot_result.get("feature_importances", {}) if snapshot_result else {}

    labels = {
        "heart_rate": "Heart Rate",
        "respiratory_rate": "Respiratory Rate",
        "spo2": "SpO₂",
        "temperature": "Temperature",
        "systolic_bp": "Systolic BP",
        "diastolic_bp": "Diastolic BP",
    }
    units = {
        "heart_rate": "bpm",
        "respiratory_rate": "/min",
        "spo2": "%",
        "temperature": "°C",
        "systolic_bp": "mmHg",
        "diastolic_bp": "mmHg",
    }

    anomalies = {
        "heart_rate": lambda v: v > 100 or v < 55,
        "respiratory_rate": lambda v: v > 22 or v < 10,
        "spo2": lambda v: v < 94,
        "temperature": lambda v: v > 38.3 or v < 35.5,
        "systolic_bp": lambda v: v < 90 or v > 170,
        "diastolic_bp": lambda v: v < 55 or v > 100,
    }

    sorted_features = sorted(feature_importances.items(), key=lambda x: -x[1]) if feature_importances else [(f, 0) for f in FEATURES]

    for feat, imp in sorted_features:
        val = vitals.get(feat, 0)
        bl = baseline.get(feat)
        is_anomaly = anomalies.get(feat, lambda v: False)(val)
        deviation = round(val - bl, 1) if bl else None

        if is_anomaly or (deviation and abs(deviation) > 5):
            impact = "high" if (is_anomaly and deviation and abs(deviation) > 15) else ("medium" if is_anomaly else "low")
            desc = f"{labels.get(feat, feat)}"
            if deviation:
                direction = "above" if deviation > 0 else "below"
                desc += f" {direction} baseline"
            factors.append({
                "factor": desc,
                "value": f"{val} {units.get(feat, '')}",
                "baseline": f"{bl} {units.get(feat, '')}" if bl else None,
                "deviation": deviation,
                "impact": impact,
                "importance": round(imp, 4) if imp else 0,
            })

    if not factors:
        factors.append({"factor": "All Vitals Within Normal Range", "value": "Normal", "impact": "low", "importance": 0})

    return factors[:6]


def compute_timeline(current_vgi: float, history: list) -> list:
    """Project risk trajectory into the future."""
    timeline = []
    # Estimate rate of change from history
    if len(history) >= 3:
        recent_vgis = []
        for h in history[-5:]:
            # Estimate VGI from vitals if not stored
            v = h
            hr_risk = max(0, (v.get("heart_rate", 72) - 90) * 0.5)
            spo2_risk = max(0, (95 - v.get("spo2", 98)) * 3)
            rr_risk = max(0, (v.get("respiratory_rate", 16) - 20) * 1.5)
            temp_risk = max(0, (v.get("temperature", 37) - 37.5) * 5)
            est_vgi = min(100, max(0, hr_risk + spo2_risk + rr_risk + temp_risk))
            recent_vgis.append(est_vgi)
        if len(recent_vgis) >= 2:
            rate = (recent_vgis[-1] - recent_vgis[0]) / max(1, len(recent_vgis))
        else:
            rate = current_vgi * 0.02
    else:
        rate = current_vgi * 0.025

    for h in [0, 2, 4, 6, 8, 10, 12]:
        projected = min(100, max(0, current_vgi + rate * h))
        timeline.append({"hours": h, "risk": round(projected, 1)})

    return timeline


def predict_risk(current_vitals: dict, history: list) -> dict:
    """Main prediction function combining snapshot and trend models."""
    # Snapshot prediction
    snap = snapshot_predict(current_vitals)

    # Trend prediction
    full_history = history + [current_vitals]
    trend = trend_predict(full_history)

    # Risk fusion
    if snap and trend:
        vgi = (snap["risk_score"] + trend["risk_score"]) / 2
        hours = trend["estimated_hours"]
    elif snap:
        vgi = snap["risk_score"]
        hours = max(1, (100 - vgi) * 0.15)
    elif trend:
        vgi = trend["risk_score"]
        hours = trend["estimated_hours"]
    else:
        # No models available — will not happen if backend fallback handles it
        return None

    vgi = round(max(0, min(100, vgi)), 1)
    category = classify_risk(vgi)
    hours = round(max(0.5, hours), 1)

    # Baseline
    baseline = compute_baseline(history)

    # Explanation
    explanation = compute_explanation(current_vitals, baseline, snap)

    # Timeline
    timeline = compute_timeline(vgi, history)

    # Alert
    alert = vgi >= 80

    return {
        "vgi": vgi,
        "risk_category": category,
        "estimated_hours_to_deterioration": hours,
        "explanation": explanation,
        "baseline": baseline,
        "timeline": timeline,
        "alert": alert,
        "alert_message": f"Patient predicted to deteriorate within {hours} hours. Immediate clinical review recommended." if alert else None,
    }
