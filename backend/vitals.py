import sys
import os
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import Patient, Vital
from auth import get_current_patient

# Add ml-service to path for predictions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml-service"))

router = APIRouter(prefix="/vitals", tags=["Vitals"])


# ── Schemas ──────────────────────────────────────────────
class VitalInput(BaseModel):
    heart_rate: float
    spo2: float
    temperature: float
    respiratory_rate: float
    systolic_bp: float
    diastolic_bp: float


class VitalResponse(BaseModel):
    id: int
    heart_rate: float
    spo2: float
    temperature: float
    respiratory_rate: float
    systolic_bp: float
    diastolic_bp: float
    vgi: Optional[float] = None
    risk_category: Optional[str] = None
    estimated_hours_to_deterioration: Optional[float] = None
    timestamp: str

    class Config:
        from_attributes = True


class VitalAddResponse(BaseModel):
    vital: VitalResponse
    prediction: dict


# ── Helpers ──────────────────────────────────────────────
def get_prediction(current_vitals: dict, history: list) -> dict:
    """Get prediction from ML service, with rule-based fallback."""
    try:
        from predict_service import predict_risk
        result = predict_risk(current_vitals, history)
        if result is not None:
            return result
    except Exception as e:
        pass
    # Fallback: rule-based prediction if ML models not available
    return rule_based_prediction(current_vitals, history)


def rule_based_prediction(vitals: dict, history: list) -> dict:
    """Fallback rule-based risk calculation."""
    risk = 0.0

    # Heart rate risk
    hr = vitals["heart_rate"]
    if hr > 120 or hr < 50:
        risk += 25
    elif hr > 100 or hr < 60:
        risk += 12

    # SpO2 risk
    spo2 = vitals["spo2"]
    if spo2 < 88:
        risk += 30
    elif spo2 < 92:
        risk += 20
    elif spo2 < 95:
        risk += 10

    # Temperature risk
    temp = vitals["temperature"]
    if temp > 39.5 or temp < 35:
        risk += 20
    elif temp > 38.5 or temp < 36:
        risk += 10

    # Respiratory rate risk
    rr = vitals["respiratory_rate"]
    if rr > 30 or rr < 8:
        risk += 25
    elif rr > 24 or rr < 10:
        risk += 12

    # Blood pressure risk
    sbp = vitals["systolic_bp"]
    if sbp < 80 or sbp > 200:
        risk += 20
    elif sbp < 90 or sbp > 180:
        risk += 10

    # Trend analysis from history
    trend_risk = 0.0
    if len(history) >= 3:
        recent = history[-3:]
        hr_trend = recent[-1]["heart_rate"] - recent[0]["heart_rate"]
        spo2_trend = recent[-1]["spo2"] - recent[0]["spo2"]
        rr_trend = recent[-1]["respiratory_rate"] - recent[0]["respiratory_rate"]

        if hr_trend > 15:
            trend_risk += 10
        if spo2_trend < -3:
            trend_risk += 15
        if rr_trend > 5:
            trend_risk += 10

    # Baseline analysis
    baseline_deviation_risk = 0.0
    if len(history) >= 5:
        avg_hr = sum(h["heart_rate"] for h in history) / len(history)
        avg_spo2 = sum(h["spo2"] for h in history) / len(history)
        hr_dev = abs(vitals["heart_rate"] - avg_hr)
        spo2_dev = avg_spo2 - vitals["spo2"]
        if hr_dev > 30:
            baseline_deviation_risk += 10
        if spo2_dev > 5:
            baseline_deviation_risk += 10

    vgi = min(100, max(0, risk * 0.6 + trend_risk * 0.25 + baseline_deviation_risk * 0.15))

    # Classify
    if vgi < 30:
        category = "Stable"
    elif vgi < 50:
        category = "Systemic Inflammation"
    elif vgi < 70:
        category = "Cardiac Risk"
    elif vgi < 85:
        category = "Respiratory Failure"
    else:
        category = "Critical Deterioration"

    # Estimate hours
    if vgi >= 85:
        hours = round(1.0 + (100 - vgi) * 0.2, 1)
    elif vgi >= 70:
        hours = round(3.0 + (85 - vgi) * 0.3, 1)
    elif vgi >= 50:
        hours = round(6.0 + (70 - vgi) * 0.3, 1)
    else:
        hours = round(12.0 + (50 - vgi) * 0.5, 1)

    # Explanation
    factors = []
    if hr > 100:
        factors.append({"factor": "Heart Rate Elevated", "value": f"{hr} bpm", "impact": "high" if hr > 120 else "medium"})
    if spo2 < 95:
        factors.append({"factor": "SpO₂ Below Normal", "value": f"{spo2}%", "impact": "high" if spo2 < 90 else "medium"})
    if temp > 38.5:
        factors.append({"factor": "Temperature Elevated", "value": f"{temp}°C", "impact": "high" if temp > 39.5 else "medium"})
    if rr > 24:
        factors.append({"factor": "Respiratory Rate Elevated", "value": f"{rr}/min", "impact": "high" if rr > 30 else "medium"})
    if sbp < 90:
        factors.append({"factor": "Systolic BP Low", "value": f"{sbp} mmHg", "impact": "high" if sbp < 80 else "medium"})
    if sbp > 180:
        factors.append({"factor": "Systolic BP High", "value": f"{sbp} mmHg", "impact": "high" if sbp > 200 else "medium"})
    if not factors:
        factors.append({"factor": "All Vitals Within Range", "value": "Normal", "impact": "low"})

    # Baseline data
    baseline = {}
    if len(history) >= 5:
        baseline = {
            "heart_rate": round(sum(h["heart_rate"] for h in history) / len(history), 1),
            "spo2": round(sum(h["spo2"] for h in history) / len(history), 1),
            "temperature": round(sum(h["temperature"] for h in history) / len(history), 1),
            "respiratory_rate": round(sum(h["respiratory_rate"] for h in history) / len(history), 1),
            "systolic_bp": round(sum(h["systolic_bp"] for h in history) / len(history), 1),
            "diastolic_bp": round(sum(h["diastolic_bp"] for h in history) / len(history), 1),
        }

    # Timeline forecast
    timeline = []
    for h in [0, 2, 4, 6, 8, 10, 12]:
        projected = min(100, vgi + h * (vgi * 0.03))
        timeline.append({"hours": h, "risk": round(projected, 1)})

    return {
        "vgi": round(vgi, 1),
        "risk_category": category,
        "estimated_hours_to_deterioration": hours,
        "explanation": factors,
        "baseline": baseline,
        "timeline": timeline,
        "alert": vgi >= 80,
        "alert_message": f"Patient predicted to deteriorate within {hours} hours. Immediate clinical review recommended." if vgi >= 80 else None,
    }


# ── Routes ───────────────────────────────────────────────
@router.post("/add", response_model=VitalAddResponse)
def add_vital(vital_input: VitalInput, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    # Get patient history
    history_records = (
        db.query(Vital)
        .filter(Vital.patient_id == patient.patient_id)
        .order_by(Vital.timestamp)
        .all()
    )

    history = [
        {
            "heart_rate": v.heart_rate,
            "spo2": v.spo2,
            "temperature": v.temperature,
            "respiratory_rate": v.respiratory_rate,
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
        }
        for v in history_records
    ]

    current = vital_input.model_dump()
    prediction = get_prediction(current, history)

    # Save vital with prediction
    vital = Vital(
        patient_id=patient.patient_id,
        heart_rate=vital_input.heart_rate,
        spo2=vital_input.spo2,
        temperature=vital_input.temperature,
        respiratory_rate=vital_input.respiratory_rate,
        systolic_bp=vital_input.systolic_bp,
        diastolic_bp=vital_input.diastolic_bp,
        vgi=prediction["vgi"],
        risk_category=prediction["risk_category"],
        estimated_hours_to_deterioration=prediction["estimated_hours_to_deterioration"],
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)

    return VitalAddResponse(
        vital=VitalResponse(
            id=vital.id,
            heart_rate=vital.heart_rate,
            spo2=vital.spo2,
            temperature=vital.temperature,
            respiratory_rate=vital.respiratory_rate,
            systolic_bp=vital.systolic_bp,
            diastolic_bp=vital.diastolic_bp,
            vgi=vital.vgi,
            risk_category=vital.risk_category,
            estimated_hours_to_deterioration=vital.estimated_hours_to_deterioration,
            timestamp=vital.timestamp.isoformat() if vital.timestamp else "",
        ),
        prediction=prediction,
    )


@router.get("/history", response_model=List[VitalResponse])
def get_history(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    records = (
        db.query(Vital)
        .filter(Vital.patient_id == patient.patient_id)
        .order_by(desc(Vital.timestamp))
        .all()
    )
    return [
        VitalResponse(
            id=v.id,
            heart_rate=v.heart_rate,
            spo2=v.spo2,
            temperature=v.temperature,
            respiratory_rate=v.respiratory_rate,
            systolic_bp=v.systolic_bp,
            diastolic_bp=v.diastolic_bp,
            vgi=v.vgi,
            risk_category=v.risk_category,
            estimated_hours_to_deterioration=v.estimated_hours_to_deterioration,
            timestamp=v.timestamp.isoformat() if v.timestamp else "",
        )
        for v in records
    ]
