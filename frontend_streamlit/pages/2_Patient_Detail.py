import streamlit as st
from utils.auth import require_login, get_token
from utils.api_client import get
from utils.banners import show_anonymised_banner

st.set_page_config(page_title="Patient Detail", layout="wide")

if not require_login():
    st.stop()

show_anonymised_banner()

token = get_token()

st.title("Patient Detail")
patient_id = st.text_input("Patient ID")

if st.button("Load") and patient_id:
    resp = get(f"/patients/{patient_id}/monitoring-timeline", token=token)
    if resp.status_code != 200:
        st.error("Failed to load patient timeline")
        st.stop()

    data = resp.json()
    st.subheader("Patient")
    st.json(data.get("patient", {}))

    st.subheader("Medications")
    st.dataframe(data.get("medications", []), use_container_width=True)

    st.subheader("Tasks")
    st.dataframe(data.get("tasks", []), use_container_width=True)

    st.subheader("Events")
    st.dataframe(data.get("events", []), use_container_width=True)
