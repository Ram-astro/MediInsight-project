from sqlalchemy import text
from datetime import date
from typing import Optional, Literal
from uuid import uuid4
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware



from sqlalchemy.exc import SQLAlchemyError

from database import engine


app = FastAPI(
    title="MediInsight API",
    description=(
        "Healthcare analytics API using synthetic data. "
        "Illustrative indicators are not clinical assessments."
    ),
    version="1.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATIENT INPUT MODEL
# ============================================================

class PatientCreate(BaseModel):
    patient_name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=0, le=120)

    sex: Literal["Male", "Female", "Not specified"]

    department: Literal[
        "Cardiology",
        "General Medicine",
        "Neurology",
        "Orthopedics",
        "Pediatrics",
    ]

    visit_date: date
    visit_type: Literal["Inpatient", "Outpatient"]

    length_of_stay_days: int = Field(default=0, ge=0, le=365)

    heart_rate_bpm: float = Field(ge=20, le=300)
    temperature_c: float = Field(ge=25, le=45)
    systolic_bp_mmhg: float = Field(ge=40, le=300)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

@app.on_event("startup")
def initialize_database():
    """Check whether the patient_name column exists."""

    try:
        with engine.begin() as connection:
            columns = connection.execute(
                text("SHOW COLUMNS FROM patients")
            ).fetchall()

            existing_columns = {
                column[0] for column in columns
            }

            if "patient_name" not in existing_columns:
                connection.execute(
                    text("""
                        ALTER TABLE patients
                        ADD COLUMN patient_name VARCHAR(100) NULL
                    """)
                )

    except Exception as error:
        raise RuntimeError(
            "Could not initialize the patient_name column."
        ) from error
# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "project": "MediInsight",
        "message": "Healthcare Analytics API is running!",
        "version": "1.2.0",
        "data_type": "Synthetic demonstration data",
        "documentation": "/docs",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        )


# ============================================================
# REUSABLE QUERY FUNCTION
# ============================================================

def fetch_records(query: str, params: Optional[dict] = None):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(query),
                params or {},
            )

            return [
                dict(row)
                for row in result.mappings().all()
            ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Database query failed",
        )


# ============================================================
# GET PATIENTS
# ============================================================

@app.get("/patients")
def get_patients(
    search: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = """
        SELECT
            patient_id,
            patient_name,
            age,
            sex,
            department
        FROM patients
        WHERE 1 = 1
    """

    params = {
        "limit": limit,
        "offset": offset,
    }

    if search:
        query += """
            AND (
                patient_id LIKE :search
                OR patient_name LIKE :search
            )
        """
        params["search"] = f"%{search}%"

    if department:
        query += " AND department = :department"
        params["department"] = department

    query += """
        ORDER BY patient_id
        LIMIT :limit OFFSET :offset
    """

    return {
        "data": fetch_records(query, params),
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# GET SINGLE PATIENT
# ============================================================

@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    records = fetch_records(
        """
        SELECT
            patient_id,
            patient_name,
            age,
            sex,
            department
        FROM patients
        WHERE patient_id = :patient_id
        """,
        {"patient_id": patient_id},
    )

    if not records:
        raise HTTPException(
            status_code=404,
            detail="Synthetic patient not found",
        )

    return records[0]


# ============================================================
# CREATE PATIENT AND ASSOCIATED RECORDS
# ============================================================

@app.post("/patients", status_code=201)
def create_patient(patient: PatientCreate):

    patient_id = f"SYN-P-{uuid4().hex[:12].upper()}"
    visit_id = f"VIS-{uuid4().hex[:12].upper()}"
    measurement_id = f"MEA-{uuid4().hex[:12].upper()}"

    indicators = [
        (
            "heart_rate",
            patient.heart_rate_bpm > 110,
            "Heart rate above illustrative threshold of 110 bpm.",
        ),
        (
            "temperature",
            patient.temperature_c > 38.5,
            "Temperature above illustrative threshold of 38.5 C.",
        ),
        (
            "systolic_bp",
            patient.systolic_bp_mmhg > 150,
            "Systolic blood pressure above illustrative threshold of 150 mmHg.",
        ),
    ]

    try:
        with engine.begin() as connection:

            # Patient record
            connection.execute(
                text("""
                    INSERT INTO patients
                        (
                            patient_id,
                            patient_name,
                            age,
                            sex,
                            department
                        )
                    VALUES
                        (
                            :patient_id,
                            :patient_name,
                            :age,
                            :sex,
                            :department
                        )
                """),
                {
                    "patient_id": patient_id,
                    "patient_name": patient.patient_name.strip(),
                    "age": patient.age,
                    "sex": patient.sex,
                    "department": patient.department,
                },
            )

            # Visit record
            connection.execute(
                text("""
                    INSERT INTO visits
                        (
                            visit_id,
                            patient_id,
                            visit_date,
                            department,
                            visit_type,
                            length_of_stay_days
                        )
                    VALUES
                        (
                            :visit_id,
                            :patient_id,
                            :visit_date,
                            :department,
                            :visit_type,
                            :length_of_stay_days
                        )
                """),
                {
                    "visit_id": visit_id,
                    "patient_id": patient_id,
                    "visit_date": patient.visit_date,
                    "department": patient.department,
                    "visit_type": patient.visit_type,
                    "length_of_stay_days": patient.length_of_stay_days,
                },
            )

            # Measurement record
            connection.execute(
                text("""
                    INSERT INTO measurements
                        (
                            measurement_id,
                            patient_id,
                            measurement_date,
                            heart_rate_bpm,
                            temperature_c,
                            systolic_bp_mmhg
                        )
                    VALUES
                        (
                            :measurement_id,
                            :patient_id,
                            :measurement_date,
                            :heart_rate_bpm,
                            :temperature_c,
                            :systolic_bp_mmhg
                        )
                """),
                {
                    "measurement_id": measurement_id,
                    "patient_id": patient_id,
                    "measurement_date": patient.visit_date,
                    "heart_rate_bpm": patient.heart_rate_bpm,
                    "temperature_c": patient.temperature_c,
                    "systolic_bp_mmhg": patient.systolic_bp_mmhg,
                },
            )

            # Illustrative indicator records
            for indicator_type, triggered, description in indicators:
                connection.execute(
                    text("""
                        INSERT INTO risk_indicators
                            (
                                measurement_id,
                                indicator_type,
                                rule_triggered,
                                rule_description
                            )
                        VALUES
                            (
                                :measurement_id,
                                :indicator_type,
                                :rule_triggered,
                                :rule_description
                            )
                    """),
                    {
                        "measurement_id": measurement_id,
                        "indicator_type": indicator_type,
                        "rule_triggered": int(triggered),
                        "rule_description": description,
                    },
                )

        return {
            "message": "Patient records created successfully.",
            "patient_id": patient_id,
            "patient_name": patient.patient_name.strip(),
            "visit_id": visit_id,
            "measurement_id": measurement_id,
            "indicator_records_created": len(indicators),
            "data_type": "Synthetic demonstration data",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save records. "
                "The database transaction was rolled back."
            ),
        )


# ============================================================
# GET VISITS
# ============================================================

@app.get("/visits")
def get_visits(
    department: Optional[str] = None,
    visit_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must not be after end_date",
        )

    query = """
        SELECT
            visit_id,
            patient_id,
            visit_date,
            department,
            visit_type,
            length_of_stay_days
        FROM visits
        WHERE 1 = 1
    """

    params = {
        "limit": limit,
        "offset": offset,
    }

    if department:
        query += " AND department = :department"
        params["department"] = department

    if visit_type:
        query += " AND visit_type = :visit_type"
        params["visit_type"] = visit_type

    if start_date:
        query += " AND visit_date >= :start_date"
        params["start_date"] = start_date

    if end_date:
        query += " AND visit_date <= :end_date"
        params["end_date"] = end_date

    query += """
        ORDER BY visit_date DESC, visit_id
        LIMIT :limit OFFSET :offset
    """

    return {
        "data": fetch_records(query, params),
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# GET MEASUREMENTS
# ============================================================

@app.get("/measurements")
def get_measurements(
    patient_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = """
        SELECT
            measurement_id,
            patient_id,
            measurement_date,
            heart_rate_bpm,
            temperature_c,
            systolic_bp_mmhg
        FROM measurements
        WHERE 1 = 1
    """

    params = {
        "limit": limit,
        "offset": offset,
    }

    if patient_id:
        query += " AND patient_id = :patient_id"
        params["patient_id"] = patient_id

    query += """
        ORDER BY measurement_date DESC, measurement_id
        LIMIT :limit OFFSET :offset
    """

    return {
        "data": fetch_records(query, params),
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# DEPARTMENT ANALYTICS
# ============================================================

@app.get("/analytics/departments")
def department_analytics():
    query = """
        SELECT
            department,
            COUNT(*) AS total_visits,
            COUNT(DISTINCT patient_id) AS unique_patients,
            SUM(
                CASE
                    WHEN visit_type = 'Inpatient' THEN 1
                    ELSE 0
                END
            ) AS inpatient_visits,
            SUM(
                CASE
                    WHEN visit_type = 'Outpatient' THEN 1
                    ELSE 0
                END
            ) AS outpatient_visits,
            ROUND(AVG(length_of_stay_days), 2)
                AS average_stay_days
        FROM visits
        GROUP BY department
        ORDER BY total_visits DESC
    """

    return {"data": fetch_records(query)}


# ============================================================
# MONTHLY VISIT ANALYTICS
# ============================================================

@app.get("/analytics/monthly-visits")
def monthly_visit_analytics():
    query = """
        SELECT
            DATE_FORMAT(visit_date, '%Y-%m') AS month,
            COUNT(*) AS total_visits
        FROM visits
        GROUP BY DATE_FORMAT(visit_date, '%Y-%m')
        ORDER BY month
    """

    return {"data": fetch_records(query)}


# ============================================================
# INDICATOR SUMMARY
# ============================================================

@app.get("/indicators/summary")
def indicator_summary():
    query = """
        SELECT
            indicator_type,
            COUNT(*) AS total_records,
            SUM(
                CASE
                    WHEN rule_triggered = 1 THEN 1
                    ELSE 0
                END
            ) AS triggered_count
        FROM risk_indicators
        GROUP BY indicator_type
        ORDER BY indicator_type
    """

    return {
        "description": (
            "Counts of illustrative software rules. "
            "Not clinically validated risk assessments."
        ),
        "data": fetch_records(query),
    }


# ============================================================
# DASHBOARD OVERVIEW
# ============================================================

@app.get("/analytics/overview")
def analytics_overview():
    query = """
        SELECT
            (SELECT COUNT(*) FROM patients)
                AS total_patients,
            (SELECT COUNT(*) FROM visits)
                AS total_visits,
            (SELECT COUNT(*) FROM measurements)
                AS total_measurements,
            (SELECT COUNT(*) FROM risk_indicators)
                AS total_indicator_records
    """

    records = fetch_records(query)

    return {
        "data": records[0] if records else {},
        "data_type": "Synthetic demonstration data",
    }