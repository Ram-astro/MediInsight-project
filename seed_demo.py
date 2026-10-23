import numpy as np
import pandas as pd

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine


def seed_database():
    rng = np.random.default_rng(42)

    departments = [
        "Cardiology",
        "General Medicine",
        "Neurology",
        "Orthopedics",
        "Pediatrics"
    ]

    start_date = pd.Timestamp("2026-01-01")
    end_date = pd.Timestamp("2026-10-15")
    total_days = (end_date - start_date).days

    # Avoid duplicate demo data if the script is rerun.
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT COUNT(*) FROM patients")
        ).scalar_one()

        if existing > 0:
            print("The patients table already contains data.")
            print("No records were inserted.")
            print("To avoid duplicates, seeding was skipped.")
            return

    print("Generating synthetic patients...")

    n_patients = 500
    n_visits = 1500
    n_measurements = 2500

    patients = pd.DataFrame({
        "patient_id": [
            f"SYN-P{i:04d}"
            for i in range(1, n_patients + 1)
        ],
        "age": rng.integers(1, 91, n_patients),
        "sex": rng.choice(
            ["Female", "Male", "Not specified"],
            n_patients,
            p=[0.48, 0.48, 0.04]
        ),
        "department": rng.choice(
            departments, n_patients
        )
    })

    print("Generating synthetic visits...")

    visit_dates = (
        start_date
        + pd.to_timedelta(
            rng.integers(0, total_days + 1, n_visits),
            unit="D"
        )
    )

    visits = pd.DataFrame({
        "visit_id": [
            f"VIS-{i:05d}"
            for i in range(1, n_visits + 1)
        ],
        "patient_id": rng.choice(
            patients["patient_id"], n_visits
        ),
        "visit_date": visit_dates,
        "department": rng.choice(
            departments, n_visits
        ),
        "visit_type": rng.choice(
            ["Outpatient", "Inpatient"],
            n_visits,
            p=[0.78, 0.22]
        ),
        "length_of_stay_days": rng.integers(
            0, 11, n_visits
        )
    })

    print("Generating synthetic measurements...")

    measurement_dates = (
        start_date
        + pd.to_timedelta(
            rng.integers(0, total_days + 1, n_measurements),
            unit="D"
        )
    )

    measurements = pd.DataFrame({
        "measurement_id": [
            f"MEA-{i:05d}"
            for i in range(1, n_measurements + 1)
        ],
        "patient_id": rng.choice(
            patients["patient_id"], n_measurements
        ),
        "measurement_date": measurement_dates,
        "heart_rate_bpm": np.clip(
            rng.normal(82, 17, n_measurements),
            35, 180
        ).round(1),
        "temperature_c": np.clip(
            rng.normal(37.0, 0.7, n_measurements),
            34.0, 42.0
        ).round(1),
        "systolic_bp_mmhg": np.clip(
            rng.normal(122, 20, n_measurements),
            70, 220
        ).round(1)
    })

    # Illustrative rules for a software demonstration.
    # These are not clinically validated thresholds.

    rule_definitions = [
        (
            "heart_rate",
            "heart_rate_bpm",
            110,
            "Heart rate greater than 110 bpm"
        ),
        (
            "temperature",
            "temperature_c",
            38.5,
            "Temperature greater than 38.5 C"
        ),
        (
            "systolic_bp",
            "systolic_bp_mmhg",
            150,
            "Systolic blood pressure greater than 150 mmHg"
        )
    ]

    print("Preparing illustrative indicator records...")

    indicator_rows = []

    for rule_name, column, threshold, description in rule_definitions:
        for _, row in measurements.iterrows():
            triggered = bool(row[column] > threshold)

            indicator_rows.append({
                "measurement_id": row["measurement_id"],
                "indicator_type": rule_name,
                "rule_triggered": triggered,
                "rule_description": description
            })

    indicators = pd.DataFrame(indicator_rows)

    print("Writing records to MySQL...")

    try:
        # A single transaction ensures the inserted dataset
        # is committed together.
        with engine.begin() as connection:
            patients.to_sql(
                "patients",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=500
            )

            visits.to_sql(
                "visits",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=500
            )

            measurements.to_sql(
                "measurements",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=500
            )

            indicators.to_sql(
                "risk_indicators",
                con=connection,
                if_exists="append",
                index=False,
                chunksize=1000
            )

        print("\nSUCCESS! Synthetic data inserted.")
        print(f"Patients: {len(patients):,}")
        print(f"Visits: {len(visits):,}")
        print(f"Measurements: {len(measurements):,}")
        print(f"Indicator records: {len(indicators):,}")

    except SQLAlchemyError as error:
        print("\nDatabase insertion failed.")
        print("Error:", error)
        raise


if __name__ == "__main__":
    seed_database()