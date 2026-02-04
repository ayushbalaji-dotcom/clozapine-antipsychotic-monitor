import requests
import streamlit as st

from utils.api_client import BASE_URL
from utils.auth import get_token, require_login
from utils.banners import show_anonymised_banner

st.set_page_config(page_title="CSV Uploads", layout="wide")

if not require_login():
    st.stop()

show_anonymised_banner()

token = get_token()

st.title("CSV Uploads")
st.write("Upload pseudonymised CSV exports from your EPR.")

headers = {}
if token:
    headers["Authorization"] = f"Bearer {token}"

st.subheader("Templates")
template_resp = requests.get(f"{BASE_URL}/uploads/templates", headers=headers, timeout=10)
if template_resp.status_code == 200:
    st.download_button(
        "Download CSV templates",
        data=template_resp.content,
        file_name="csv_templates.zip",
        mime="application/zip",
    )
else:
    st.warning("Unable to download templates")

st.subheader("Upload Files")
patients_file = st.file_uploader("Patients CSV", type=["csv"])
medications_file = st.file_uploader("Medications CSV", type=["csv"])
events_file = st.file_uploader("Events CSV", type=["csv"])
validate_only = st.checkbox("Validate only (no import)", value=True)

if st.button("Run Upload"):
    files = {}
    if patients_file:
        files["patients"] = ("patients.csv", patients_file.getvalue(), "text/csv")
    if medications_file:
        files["medications"] = ("medications.csv", medications_file.getvalue(), "text/csv")
    if events_file:
        files["events"] = ("events.csv", events_file.getvalue(), "text/csv")

    if not files:
        st.warning("Select at least one CSV file to upload.")
    else:
        resp = requests.post(
            f"{BASE_URL}/uploads/csv",
            headers=headers,
            files=files,
            data={"validate_only": str(validate_only).lower()},
            timeout=60,
        )
        if resp.status_code != 200:
            st.error(f"Upload failed: {resp.text}")
        else:
            result = resp.json()
            st.subheader("Validation Report")
            st.json(result.get("validation_report", {}))
            if result.get("import_summary"):
                st.subheader("Import Summary")
                st.json(result.get("import_summary", {}))
            if result.get("errors"):
                st.subheader("Errors")
                st.json(result.get("errors", []))
