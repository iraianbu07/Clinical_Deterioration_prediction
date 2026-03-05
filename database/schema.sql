-- VITAL-GUARD AI Database Schema
-- PostgreSQL-compatible (SQLite used for local dev)

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id VARCHAR(50) NOT NULL,
    heart_rate REAL NOT NULL,
    spo2 REAL NOT NULL,
    temperature REAL NOT NULL,
    respiratory_rate REAL NOT NULL,
    systolic_bp REAL NOT NULL,
    diastolic_bp REAL NOT NULL,
    vgi REAL,
    risk_category VARCHAR(50),
    estimated_hours_to_deterioration REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE INDEX IF NOT EXISTS idx_vitals_patient ON vitals(patient_id);
CREATE INDEX IF NOT EXISTS idx_vitals_timestamp ON vitals(timestamp);
