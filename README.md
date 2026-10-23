# MediInsight React Frontend

A premium React + TypeScript frontend for the existing MediInsight FastAPI + MySQL project. It uses synthetic/demo data only and labels threshold indicators as illustrative, not clinically validated.

## Requirements
- Node.js 20+ recommended
- Existing MediInsight FastAPI API running at `http://127.0.0.1:8000`

## Run locally (Windows PowerShell)
1. Extract this folder.
2. Open PowerShell in the `medinsight-react` folder.
3. Install dependencies:
   ```powershell
   npm install
   ```
4. Create your local environment file:
   ```powershell
   Copy-Item .env.example .env
   ```
5. Start the React development server:
   ```powershell
   npm run dev
   ```
6. Open the Local URL Vite prints, usually `http://localhost:5173`.

Keep the FastAPI server running separately:
```powershell
cd C:\Users\naras\MEDINSIGHT
.\venv\Scripts\Activate.ps1
$env:MEDINSIGHT_DB_PASSWORD = Read-Host "Enter your MySQL password"
python -m uvicorn api:app --reload
```

## API configuration
The frontend reads `VITE_API_BASE_URL`. Set it in `.env` before starting Vite. For a deployed frontend, set it to the public HTTPS URL of your deployed FastAPI service.

## Backend expectations
This frontend calls the existing endpoints:
- `GET /analytics/overview`
- `GET /patients`
- `GET /visits`
- `GET /measurements`
- `GET /analytics/departments`
- `GET /analytics/monthly-visits`
- `GET /indicators/summary`
- `POST /patients`

Responses are expected to use `{ "data": ... }` for list/overview endpoints, consistent with the current Streamlit frontend. The Add Patient form posts `patient_name`, `age`, `sex`, `department`, `visit_date`, `visit_type`, `length_of_stay_days`, `heart_rate_bpm`, `temperature_c`, and `systolic_bp_mmhg`.

If the browser console reports a CORS error, configure CORS in FastAPI to allow the Vite origin `http://localhost:5173` for local development and the deployed frontend domain for production. Do not use wildcard origins with credentials.

## Safety
All records in this prototype should remain synthetic. Do not use this demo as a clinical decision-support tool. The threshold flags are illustrative only.
