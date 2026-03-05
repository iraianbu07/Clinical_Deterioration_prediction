"""
VITAL-GUARD AI — Synthetic Dataset Generator
Generates realistic patient vital sign data for training snapshot and trend models.
"""
import csv
import random
import os

random.seed(42)

VITAL_RANGES = {
    "stable": {
        "heart_rate": (60, 85),
        "respiratory_rate": (12, 18),
        "spo2": (96, 100),
        "temperature": (36.2, 37.2),
        "systolic_bp": (110, 130),
        "diastolic_bp": (70, 85),
    },
    "inflammation": {
        "heart_rate": (85, 110),
        "respiratory_rate": (18, 24),
        "spo2": (93, 97),
        "temperature": (37.5, 38.8),
        "systolic_bp": (95, 130),
        "diastolic_bp": (60, 80),
    },
    "cardiac": {
        "heart_rate": (100, 140),
        "respiratory_rate": (20, 28),
        "spo2": (90, 96),
        "temperature": (36.5, 38.0),
        "systolic_bp": (80, 110),
        "diastolic_bp": (50, 70),
    },
    "respiratory": {
        "heart_rate": (95, 130),
        "respiratory_rate": (26, 36),
        "spo2": (82, 92),
        "temperature": (37.0, 39.0),
        "systolic_bp": (85, 120),
        "diastolic_bp": (55, 75),
    },
    "critical": {
        "heart_rate": (120, 165),
        "respiratory_rate": (30, 45),
        "spo2": (70, 88),
        "temperature": (38.5, 41.0),
        "systolic_bp": (60, 95),
        "diastolic_bp": (35, 60),
    },
}

RISK_LABELS = {
    "stable": (0, 30),
    "inflammation": (30, 50),
    "cardiac": (50, 70),
    "respiratory": (70, 85),
    "critical": (85, 100),
}

CATEGORY_NAMES = {
    "stable": "Stable",
    "inflammation": "Systemic Inflammation",
    "cardiac": "Cardiac Risk",
    "respiratory": "Respiratory Failure",
    "critical": "Critical Deterioration",
}


def gen_vital(ranges):
    return {k: round(random.uniform(*v), 1) for k, v in ranges.items()}


def gen_risk(label):
    lo, hi = RISK_LABELS[label]
    return round(random.uniform(lo, hi), 1)


def gen_hours(label):
    mapping = {"stable": (12, 48), "inflammation": (8, 18), "cardiac": (4, 10), "respiratory": (2, 6), "critical": (0.5, 3)}
    lo, hi = mapping[label]
    return round(random.uniform(lo, hi), 1)


def generate_snapshot_dataset(n=5000):
    os.makedirs(os.path.dirname(__file__) or ".", exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), "snapshot_dataset.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["heart_rate", "respiratory_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp", "risk_score", "risk_category"])
        for _ in range(n):
            label = random.choice(list(VITAL_RANGES.keys()))
            v = gen_vital(VITAL_RANGES[label])
            risk = gen_risk(label)
            writer.writerow([v["heart_rate"], v["respiratory_rate"], v["spo2"], v["temperature"], v["systolic_bp"], v["diastolic_bp"], risk, CATEGORY_NAMES[label]])
    print(f"Generated {n} snapshot samples → {path}")


def generate_trend_dataset(n=3000, window=10):
    path = os.path.join(os.path.dirname(__file__), "trend_dataset.csv")
    headers = []
    for i in range(window):
        for feat in ["hr", "rr", "spo2", "temp", "sbp", "dbp"]:
            headers.append(f"{feat}_{i}")
    headers += ["risk_score", "risk_category", "hours_to_deterioration"]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for _ in range(n):
            # Pick a trajectory
            trajectory = random.choice(["stable_stable", "stable_inflam", "stable_critical", "inflam_cardiac", "cardiac_respiratory", "respiratory_critical"])
            parts = trajectory.split("_")
            start_label = parts[0] if parts[0] in VITAL_RANGES else "stable"
            end_label = parts[1] if parts[1] in VITAL_RANGES else parts[0]

            row = []
            for i in range(window):
                t = i / (window - 1) if window > 1 else 1.0
                # Interpolate between start and end ranges
                vitals = {}
                for feat in ["heart_rate", "respiratory_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"]:
                    s_lo, s_hi = VITAL_RANGES[start_label][feat]
                    e_lo, e_hi = VITAL_RANGES[end_label][feat]
                    lo = s_lo + (e_lo - s_lo) * t
                    hi = s_hi + (e_hi - s_hi) * t
                    vitals[feat] = round(random.uniform(lo, hi), 1)
                row.extend([vitals["heart_rate"], vitals["respiratory_rate"], vitals["spo2"], vitals["temperature"], vitals["systolic_bp"], vitals["diastolic_bp"]])

            risk = gen_risk(end_label)
            hours = gen_hours(end_label)
            row.extend([risk, CATEGORY_NAMES[end_label], hours])
            writer.writerow(row)

    print(f"Generated {n} trend samples (window={window}) → {path}")


if __name__ == "__main__":
    generate_snapshot_dataset()
    generate_trend_dataset()
    print("Dataset generation complete!")
