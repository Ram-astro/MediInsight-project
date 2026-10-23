# MediInsight Backend

FastAPI backend for the MediInsight healthcare analytics prototype. Uses SQLAlchemy and MySQL, and includes a synthetic data seed script plus optional Streamlit dashboard files.

## Requirements

- Python 3.10+ recommended
- MySQL Server

## Install and run (Windows CMD)

```cmd
cd path\to\MediInsight\backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
set MEDINSIGHT_DB_PASSWORD=YOUR_MYSQL_PASSWORD
python -m uvicorn api:app --reload
```

Configure `MEDINSIGHT_DB_USER`, `MEDINSIGHT_DB_HOST`, and `MEDINSIGHT_DB_PORT` in the same CMD window if needed. The configured database name is `medinsight_db`.

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive docs: http://127.0.0.1:8000/docs

## Main endpoints

`GET /health`, `GET /patients`, `GET /patients/{patient_id}`, `POST /patients`, `GET /visits`, `GET /measurements`, `GET /analytics/overview`, `GET /analytics/departments`, `GET /analytics/monthly-visits`, `GET /indicators/summary`.

## Seed synthetic demo data

Only use a demo database. Review the schema first.

```cmd
set MEDINSIGHT_DB_PASSWORD=YOUR_MYSQL_PASSWORD
python seed_demo.py
```

The indicator thresholds are illustrative only, not clinical assessments. Do not use real patient data.

## Optional Streamlit dashboards

`app.py`, `app_integrated.py`, and `test_streamlit.py` are included as optional Streamlit files. Their API/database configuration may need adjustment depending on how you run them.

## Security

Never commit database passwords, `.env` files, API tokens, private keys, database dumps, or real patient data. Add authentication and authorization before exposing patient-related endpoints publicly.
