import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from datetime import date

from requests.exceptions import RequestException

# ==========================================
# MEDINSIGHT: DATABASE-BACKED DASHBOARD
# Streamlit -> FastAPI -> MySQL
# ==========================================

API_BASE_URL = "http://127.0.0.1:8000"
PAGE_SIZE = 500

st.set_page_config(
    page_title="MediInsight | Healthcare Analytics",
    page_icon="ðŸ¥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- PROFESSIONAL MEDICAL THEME ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #F5F8FA; }
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E5ECEF;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: #263F49 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #173B45 !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p { color: #263F49; }
.main-title {
    font-size: 32px; font-weight: 800; color: #173B45; margin-bottom: 3px;
}
.subtitle { color: #70838B; font-size: 14px; margin-bottom: 25px; }
.metric-card {
    background: #FFFFFF; border: 1px solid #E4ECEF; border-radius: 14px;
    padding: 20px; min-height: 125px;
    box-shadow: 0 3px 12px rgba(25, 65, 75, 0.035);
}
.metric-label { color: #71838B; font-size: 13px; font-weight: 600; }
.metric-value { color: #173B45; font-size: 29px; font-weight: 800; margin-top: 8px; }
.metric-note { color: #128477; font-size: 12px; margin-top: 5px; }
.section-title { font-size: 19px; font-weight: 700; color: #173B45; margin: 18px 0 12px; }
.notice {
    background: #E9F6F4; border-left: 4px solid #159B8A; padding: 13px 16px;
    border-radius: 7px; color: #245D59; font-size: 13px; margin-bottom: 20px;
}
div[data-testid="stDataFrame"] { border: 1px solid #E4ECEF; border-radius: 10px; }
.stButton button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


def api_get(path, params=None, timeout=15):
    """Fetch JSON from the local FastAPI backend."""
    response = requests.get(
        f"{API_BASE_URL}{path}",
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def fetch_all_records(path, extra_params=None):
    """Fetch all pages from endpoints that support limit/offset."""
    rows = []
    offset = 0
    while True:
        params = {"limit": PAGE_SIZE, "offset": offset}
        if extra_params:
            params.update(extra_params)
        payload = api_get(path, params=params)
        batch = payload.get("data", [])
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += len(batch)
    return rows


@st.cache_data(ttl=30, show_spinner=False)
def load_dashboard_data():
    """Load database-backed records; cache briefly to reduce API calls."""
    overview_payload = api_get("/analytics/overview")
    overview = overview_payload.get("data", {})

    patients = pd.DataFrame(fetch_all_records("/patients"))
    visits = pd.DataFrame(fetch_all_records("/visits"))
    measurements = pd.DataFrame(fetch_all_records("/measurements"))

    departments_payload = api_get("/analytics/departments")
    departments = pd.DataFrame(departments_payload.get("data", []))

    monthly_payload = api_get("/analytics/monthly-visits")
    monthly = pd.DataFrame(monthly_payload.get("data", []))

    indicator_payload = api_get("/indicators/summary")
    indicators = pd.DataFrame(indicator_payload.get("data", []))

    # Ensure expected columns exist even when a table is empty.
    patient_cols = ["patient_id", "patient_name", "age", "sex", "department"]
    visit_cols = [
        "visit_id", "patient_id", "visit_date", "department",
        "visit_type", "length_of_stay_days"
    ]
    measurement_cols = [
        "measurement_id", "patient_id", "measurement_date",
        "heart_rate_bpm", "temperature_c", "systolic_bp_mmhg"
    ]
    for frame, cols in [
        (patients, patient_cols), (visits, visit_cols),
        (measurements, measurement_cols)
    ]:
        for col in cols:
            if col not in frame.columns:
                frame[col] = pd.Series(dtype="object")

    if not visits.empty:
        visits["visit_date"] = pd.to_datetime(visits["visit_date"], errors="coerce")
        visits["length_of_stay_days"] = pd.to_numeric(
            visits["length_of_stay_days"], errors="coerce"
        )
    if not measurements.empty:
        measurements["measurement_date"] = pd.to_datetime(
            measurements["measurement_date"], errors="coerce"
        )
        for col in ["heart_rate_bpm", "temperature_c", "systolic_bp_mmhg"]:
            measurements[col] = pd.to_numeric(measurements[col], errors="coerce")

        # Educational-only illustrative rules, evaluated on stored measurements.
        measurements["heart_rate_flag"] = measurements["heart_rate_bpm"] > 110
        measurements["temperature_flag"] = measurements["temperature_c"] > 38.5
        measurements["blood_pressure_flag"] = measurements["systolic_bp_mmhg"] > 150
        measurements["indicator_count"] = (
            measurements["heart_rate_flag"].fillna(False).astype(int)
            + measurements["temperature_flag"].fillna(False).astype(int)
            + measurements["blood_pressure_flag"].fillna(False).astype(int)
        )
        measurements["illustrative_indicator"] = measurements["indicator_count"].map(
            lambda n: "Rule triggered" if n > 0 else "No rule triggered"
        )

    if not monthly.empty and "month" in monthly.columns:
        monthly["total_visits"] = pd.to_numeric(
            monthly["total_visits"], errors="coerce"
        )

    return overview, patients, visits, measurements, departments, monthly, indicators


def metric_card(label, value, note):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)


def chart_layout():
    plt.tight_layout()
    st.pyplot(plt.gcf(), use_container_width=True)
    plt.close()


def show_table(frame):
    st.dataframe(frame, use_container_width=True, hide_index=True)


def safe_count(value):
    try:
        return f"{int(value or 0):,}"
    except (TypeError, ValueError):
        return "0"


# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("## ðŸ¥ MediInsight")
    st.caption("Healthcare Analytics Platform")
    st.divider()
    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard Overview",
             "Add Patient",
            "Patient Records",
            "Department Analytics",
            "Measurement Analytics",
            "Rule Indicators",
            "Methodology & Limitations",
        ],
    )
    st.divider()
    st.markdown("**Environment**")
    st.success("Synthetic database records")
    st.caption("Source: FastAPI + MySQL")
    st.caption("Version 1.1 | Educational prototype")
    if st.button("ðŸ”„ Refresh database data", use_container_width=True):
        load_dashboard_data.clear()
        st.rerun()

# ---------- LOAD DATABASE DATA ----------
try:
    (
        overview, patients, visits, measurements,
        departments, monthly, indicators
    ) = load_dashboard_data()
except RequestException as exc:
    st.error("Cannot reach the MediInsight API.")
    st.markdown(
        "Make sure the FastAPI server is running in another terminal, "
        "then refresh this page."
    )
    st.code("python -m uvicorn api:app --reload")
    st.caption(f"Connection detail: {exc}")
    st.stop()
except (ValueError, KeyError) as exc:
    st.error("The API response could not be processed.")
    st.caption(f"Details: {exc}")
    st.stop()

# ---------- HEADER ----------
st.markdown('<div class="main-title">MediInsight</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Healthcare Analytics and Patient Risk Indicator System</div>',
    unsafe_allow_html=True,
)
st.markdown("""
<div class="notice">
<b>Demonstration environment:</b> This application uses synthetic data only.
Its rule indicators are illustrative software outputs, not clinically validated
risk assessments. Do not use them for patient care or treatment decisions.
</div>
""", unsafe_allow_html=True)
# ============================================================
# ADD PATIENT PAGE
# ============================================================

if page == "Add Patient":

    st.title("Add New Patient")
    st.write(
        "Enter patient details, visit information, "
        "and measurements."
    )

    with st.form("add_patient_form"):

        st.subheader("Patient Information")

        patient_name = st.text_input(
            "Patient Name",
            placeholder="Enter patient name",
            max_chars=100,
        )

        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input(
                "Age",
                min_value=0,
                max_value=120,
                value=25,
                step=1,
            )

            sex = st.selectbox(
                "Sex",
                ["Male", "Female", "Not specified"],
            )

        with col2:
            department = st.selectbox(
                "Department",
                [
                    "Cardiology",
                    "General Medicine",
                    "Neurology",
                    "Orthopedics",
                    "Pediatrics",
                ],
            )

        st.subheader("Visit Information")

        col3, col4 = st.columns(2)

        with col3:
            visit_date = st.date_input(
                "Visit Date",
                value=date.today(),
            )

            visit_type = st.selectbox(
                "Visit Type",
                ["Outpatient", "Inpatient"],
            )

        with col4:
            length_of_stay_days = st.number_input(
                "Length of Stay (Days)",
                min_value=0,
                max_value=365,
                value=0,
                step=1,
            )

        st.subheader("Measurement Information")

        col5, col6, col7 = st.columns(3)

        with col5:
            heart_rate_bpm = st.number_input(
                "Heart Rate (BPM)",
                min_value=20.0,
                max_value=300.0,
                value=80.0,
                step=1.0,
            )

        with col6:
            temperature_c = st.number_input(
                "Temperature (Â°C)",
                min_value=25.0,
                max_value=45.0,
                value=36.8,
                step=0.1,
            )

        with col7:
            systolic_bp_mmhg = st.number_input(
                "Systolic BP (mmHg)",
                min_value=40.0,
                max_value=300.0,
                value=120.0,
                step=1.0,
            )

        submitted = st.form_submit_button(
            "Save Patient",
            use_container_width=True,
            type="primary",
        )

    if submitted:

        if len(patient_name.strip()) < 2:
            st.error("Please enter a patient name with at least 2 characters.")
            st.stop()

        payload = {
            "patient_name": patient_name.strip(),
            "age": int(age),
            "sex": sex,
            "department": department,
            "visit_date": visit_date.isoformat(),
            "visit_type": visit_type,
            "length_of_stay_days": int(length_of_stay_days),
            "heart_rate_bpm": float(heart_rate_bpm),
            "temperature_c": float(temperature_c),
            "systolic_bp_mmhg": float(systolic_bp_mmhg),
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/patients",
                json=payload,
                timeout=20,
            )

            if response.status_code == 201:

                result = response.json()

                st.success(
                    "Patient records saved successfully!"
                )

                st.write("Patient ID")
                st.code(result["patient_id"])

                st.write("Visit ID")
                st.code(result["visit_id"])

                st.write("Measurement ID")
                st.code(result["measurement_id"])

                st.info(
                    "Three illustrative indicator records were created. "
                    "These are not clinically validated medical assessments."
                )

                st.session_state["patient_created"] = True

            else:
                try:
                    error_detail = response.json().get(
                        "detail",
                        response.text,
                    )
                except ValueError:
                    error_detail = response.text

                st.error(
                    f"Unable to save patient: {error_detail}"
                )

        except requests.RequestException as error:
            st.error(
                "Could not connect to the MediInsight API. "
                f"Details: {error}"
            )

    if st.session_state.pop("patient_created", False):
        load_dashboard_data.clear()

    st.stop()

# ---------- PAGE 1: OVERVIEW ----------
if page == "Dashboard Overview":
    st.markdown("### Overview")
    st.write("A consolidated view of records stored in the MediInsight MySQL database.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Synthetic Patients", safe_count(overview.get("total_patients", len(patients))), "Database records")
    with c2:
        metric_card("Total Visits", safe_count(overview.get("total_visits", len(visits))), "Database records")
    with c3:
        metric_card("Measurements", safe_count(overview.get("total_measurements", len(measurements))), "Database records")
    with c4:
        triggered = int(measurements["indicator_count"].gt(0).sum()) if not measurements.empty else 0
        metric_card("Measurements with a Rule", safe_count(triggered), "Illustrative rules only")

    st.markdown('<div class="section-title">Visit Activity</div>', unsafe_allow_html=True)
    if not monthly.empty:
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(monthly["month"], monthly["total_visits"], marker="o", linewidth=2.5)
        ax.set_title("Monthly Visit Volume")
        ax.set_xlabel("Month")
        ax.set_ylabel("Visits")
        ax.grid(axis="y", alpha=0.2)
        plt.xticks(rotation=35)
        chart_layout()
    elif not visits.empty:
        monthly_local = visits.dropna(subset=["visit_date"]).copy()
        monthly_local["month"] = monthly_local["visit_date"].dt.to_period("M").astype(str)
        monthly_local = monthly_local.groupby("month").size().reset_index(name="total_visits")
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(monthly_local["month"], monthly_local["total_visits"], marker="o", linewidth=2.5)
        ax.set_title("Monthly Visit Volume")
        ax.grid(axis="y", alpha=0.2)
        plt.xticks(rotation=35)
        chart_layout()
    else:
        st.info("No visit records are available yet.")

    left, right = st.columns(2)
    with left:
        st.markdown("#### Visits by Department")
        if not departments.empty and {"department", "total_visits"}.issubset(departments.columns):
            plot_data = departments.set_index("department")["total_visits"].sort_values()
            fig, ax = plt.subplots(figsize=(7, 4))
            plot_data.plot(kind="barh", ax=ax)
            ax.set_xlabel("Visits")
            ax.grid(axis="x", alpha=0.2)
            chart_layout()
        elif not visits.empty:
            counts = visits["department"].value_counts().sort_values()
            fig, ax = plt.subplots(figsize=(7, 4))
            counts.plot(kind="barh", ax=ax)
            ax.set_xlabel("Visits")
            chart_layout()
        else:
            st.info("No department data available.")
    with right:
        st.markdown("#### Visit Type Distribution")
        if not visits.empty and "visit_type" in visits.columns:
            visit_types = visits["visit_type"].value_counts()
            fig, ax = plt.subplots(figsize=(6, 4))
            if not visit_types.empty:
                ax.pie(visit_types.values, labels=visit_types.index, autopct="%1.1f%%", startangle=90)
                ax.set_title("Stored Visit Types")
                chart_layout()
        else:
            st.info("No visit records available.")
    st.markdown("#### Recent Visits")
    if not visits.empty:
        show_table(visits.sort_values("visit_date", ascending=False).head(10))
    else:
        st.info("No visits found in the database.")

# ---------- PAGE 2: PATIENT RECORDS ----------
elif page == "Patient Records":
    st.markdown("### Patient Records")
    st.caption("All identifiers and patient records are synthetic.")
    search = st.text_input("Search by patient name or synthetic patient ID", placeholder="Enter a name or ID")
    depts = sorted(patients["department"].dropna().astype(str).unique()) if not patients.empty else []
    department_filter = st.selectbox("Filter by department", ["All"] + depts)
    filtered = patients.copy()
    if search:
        id_matches = filtered["patient_id"].astype(str).str.contains(search, case=False, na=False)
        if "patient_name" in filtered.columns:
            name_matches = filtered["patient_name"].astype(str).str.contains(search, case=False, na=False)
            filtered = filtered[id_matches | name_matches]
        else:
            filtered = filtered[id_matches]
    if department_filter != "All":
        filtered = filtered[filtered["department"] == department_filter]
    st.write(f"Records displayed: **{len(filtered):,}**")
    show_table(filtered)
    st.download_button(
        "Download filtered patient records",
        data=filtered.to_csv(index=False),
        file_name="synthetic_patient_records.csv",
        mime="text/csv",
    )
    st.markdown("#### Patient Visit History")
    patient_ids = patients["patient_id"].dropna().astype(str).tolist() if not patients.empty else []
    if patient_ids:
        selected_patient = st.selectbox("Select a synthetic patient", patient_ids)
        patient_visits = visits[visits["patient_id"].astype(str) == selected_patient].copy()
        if not patient_visits.empty:
            show_table(patient_visits.sort_values("visit_date", ascending=False))
        else:
            st.info("No visits found for this patient.")
    else:
        st.info("No patient records available.")

# ---------- PAGE 3: DEPARTMENT ANALYTICS ----------
elif page == "Department Analytics":
    st.markdown("### Department Analytics")
    st.caption("Summaries are calculated from stored synthetic visit records.")
    if not departments.empty:
        show_table(departments)
        if {"department", "inpatient_visits", "outpatient_visits"}.issubset(departments.columns):
            plot_df = departments.sort_values("total_visits").set_index("department")[
                ["inpatient_visits", "outpatient_visits"]
            ]
            fig, ax = plt.subplots(figsize=(9, 4))
            plot_df.plot(kind="barh", ax=ax)
            ax.set_xlabel("Number of visits")
            ax.set_ylabel("Department")
            ax.set_title("Visit Categories by Department")
            ax.grid(axis="x", alpha=0.2)
            chart_layout()
    elif not visits.empty:
        summary = visits.groupby("department").agg(
            total_visits=("visit_id", "count"),
            unique_patients=("patient_id", "nunique"),
            inpatient_visits=("visit_type", lambda s: (s == "Inpatient").sum()),
            outpatient_visits=("visit_type", lambda s: (s == "Outpatient").sum()),
            average_stay=("length_of_stay_days", "mean"),
        ).reset_index()
        summary["average_stay"] = summary["average_stay"].round(2)
        show_table(summary)
    else:
        st.info("No visit data available.")
    st.markdown("#### Monthly Department Trends")
    dept_options = sorted(visits["department"].dropna().astype(str).unique()) if not visits.empty else []
    if dept_options:
        selected_dept = st.selectbox("Choose a department", dept_options)
        dept_visits = visits[visits["department"] == selected_dept].dropna(subset=["visit_date"]).copy()
        if not dept_visits.empty:
            dept_visits["month"] = dept_visits["visit_date"].dt.to_period("M").astype(str)
            trend = dept_visits.groupby("month").size()
            fig, ax = plt.subplots(figsize=(9, 3.5))
            ax.plot(trend.index, trend.values, marker="o", linewidth=2)
            ax.set_title(f"{selected_dept}: Monthly Visit Counts")
            ax.set_xlabel("Month")
            ax.set_ylabel("Visits")
            ax.grid(alpha=0.2)
            plt.xticks(rotation=35)
            chart_layout()
        else:
            st.info("No visits for the selected department.")
    else:
        st.info("No department visit trends available.")

# ---------- PAGE 4: MEASUREMENT ANALYTICS ----------
elif page == "Measurement Analytics":
    st.markdown("### Measurement Analytics")
    st.caption("Charts describe simulated measurements, not actual patient observations.")
    metric_options = ["heart_rate_bpm", "temperature_c", "systolic_bp_mmhg"]
    labels = {
        "heart_rate_bpm": "Heart Rate (bpm)",
        "temperature_c": "Temperature (Â°C)",
        "systolic_bp_mmhg": "Systolic Blood Pressure (mmHg)",
    }
    metric = st.selectbox("Choose measurement", metric_options, format_func=lambda x: labels[x])
    if measurements.empty:
        st.info("No measurements available.")
    else:
        data = measurements[metric].dropna()
        a, b, c = st.columns(3)
        with a:
            metric_card("Mean", f"{data.mean():.2f}" if not data.empty else "N/A", "Synthetic data")
        with b:
            metric_card("Median", f"{data.median():.2f}" if not data.empty else "N/A", "Synthetic data")
        with c:
            metric_card("Standard Deviation", f"{data.std():.2f}" if len(data) > 1 else "N/A", "Synthetic data")
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.hist(data, bins=25, edgecolor="white")
        ax.set_title(f"Distribution: {labels[metric]}")
        ax.set_xlabel(labels[metric])
        ax.set_ylabel("Frequency")
        ax.grid(axis="y", alpha=0.2)
        chart_layout()

        st.markdown("#### Measurement Trends Over Time")
        trend_data = measurements.dropna(subset=["measurement_date"]).copy()
        if not trend_data.empty:
            trend_data["month"] = trend_data["measurement_date"].dt.to_period("M").astype(str)
            trend = trend_data.groupby("month")[metric].mean()
            fig, ax = plt.subplots(figsize=(9, 3.5))
            ax.plot(trend.index, trend.values, marker="o", linewidth=2)
            ax.set_title(f"Monthly Mean: {labels[metric]}")
            ax.set_xlabel("Month")
            ax.set_ylabel(labels[metric])
            ax.grid(alpha=0.2)
            plt.xticks(rotation=35)
            chart_layout()

        st.markdown("#### Measurement Records")
        show_cols = [
            "measurement_id", "patient_id", "measurement_date",
            "heart_rate_bpm", "temperature_c", "systolic_bp_mmhg"
        ]
        show_table(measurements[show_cols].head(100))
        st.download_button(
            "Download measurement dataset",
            data=measurements.to_csv(index=False),
            file_name="synthetic_measurements.csv",
            mime="text/csv",
        )

# ---------- PAGE 5: RULE INDICATORS ----------
elif page == "Rule Indicators":
    st.markdown("### Illustrative Rule Indicators")
    st.warning(
        "These are demonstration rules only. They are not validated clinical thresholds, "
        "diagnostic criteria, or a clinically validated risk prediction system."
    )
    rules = pd.DataFrame({
        "Measurement": ["Heart rate", "Temperature", "Systolic blood pressure"],
        "Illustrative rule": ["> 110 bpm", "> 38.5 Â°C", "> 150 mmHg"],
        "Purpose": ["Demonstrate a threshold flag"] * 3,
    })
    st.markdown("#### Rules used in this prototype")
    show_table(rules)

    # The API summary is read from risk_indicators in MySQL.
    st.markdown("#### Indicator Summary from MySQL")
    if not indicators.empty:
        show_table(indicators)
        if {"indicator_type", "triggered_count"}.issubset(indicators.columns):
            counts = indicators.set_index("indicator_type")["triggered_count"]
            fig, ax = plt.subplots(figsize=(8, 3.5))
            counts.plot(kind="bar", ax=ax)
            ax.set_ylabel("Triggered records")
            ax.set_xlabel("Illustrative rule")
            ax.set_title("Triggered Rule Counts from Database")
            ax.grid(axis="y", alpha=0.2)
            plt.xticks(rotation=15)
            chart_layout()
    else:
        st.info("The API returned no indicator summary records.")
    st.markdown("#### Inspect measurements with illustrative rules")
    only_flagged = st.checkbox("Show only records with at least one triggered rule", value=True)
    display_data = measurements.copy()
    if only_flagged and not display_data.empty:
        display_data = display_data[display_data["indicator_count"] > 0]
    if not display_data.empty:
        show_table(display_data)
        st.download_button(
            "Download illustrative indicator results",
            data=display_data.to_csv(index=False),
            file_name="illustrative_indicator_results.csv",
            mime="text/csv",
        )
    else:
        st.info("No matching measurements are available.")

# ---------- PAGE 6: METHODOLOGY & LIMITATIONS ----------
elif page == "Methodology & Limitations":
    st.markdown("### Methodology & Limitations")
    st.markdown("#### 1. Dataset")
    st.write("""
    The application reads synthetic records stored in MySQL through a local FastAPI service.
    No real patient records are used.
    """)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Patients", safe_count(overview.get("total_patients", len(patients))), "Stored records")
    with m2:
        metric_card("Visits", safe_count(overview.get("total_visits", len(visits))), "Stored records")
    with m3:
        metric_card("Measurements", safe_count(overview.get("total_measurements", len(measurements))), "Stored records")
    with m4:
        metric_card("Indicator Rows", safe_count(overview.get("total_indicator_records", 0)), "Stored rule records")

    st.markdown("#### 2. Technologies")
    st.write("""
    - Python: application logic
    - Streamlit: interactive dashboard
    - FastAPI: REST API
    - MySQL: persistent storage
    - Pandas: data manipulation and summaries
    - Matplotlib: analytical charts
    """)
    st.markdown("#### 3. Measurement assumptions")
    st.write("""
    The synthetic data-generation assumptions use these software ranges:
    - Heart rate: 35â€“180 bpm
    - Temperature: 34â€“42 Â°C
    - Systolic blood pressure: 70â€“220 mmHg

    These are software-generation assumptions, not clinical reference ranges or statements of safety.
    """)
    st.markdown("#### 4. Indicator logic")
    st.code("""if heart_rate_bpm > 110:
    heart_rate_flag = True

if temperature_c > 38.5:
    temperature_flag = True

if systolic_bp_mmhg > 150:
    blood_pressure_flag = True""")
    st.write("""
    Each rule is evaluated independently. A measurement may trigger more than one rule.
    The count describes triggered software rules, not the severity or probability of a medical condition.
    """)
    st.markdown("#### 5. Important limitations")
    st.warning("""
    1. All data are synthetic and do not represent real patients.
    2. Indicator thresholds are illustrative and have not been clinically validated.
    3. The application does not diagnose disease, estimate clinically validated risk, or recommend treatment.
    4. Synthetic trends and distributions should not be interpreted as real-world hospital statistics.
    5. This dashboard reads data through a local API; it does not implement user authentication or role-based access control.
    6. This educational prototype should not be used for patient care.
    """)
    st.markdown("#### 6. Project status")
    st.info("The Streamlit dashboard is now designed to read database-backed data through FastAPI.")

# ---------- FOOTER ----------
st.divider()
st.caption(
    "MediInsight | Healthcare Analytics and Patient Risk Indicator System | "
    "Synthetic data only | Educational demonstration, not for clinical use."
)
