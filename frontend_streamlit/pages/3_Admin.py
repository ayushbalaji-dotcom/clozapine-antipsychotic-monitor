import streamlit as st
import json
from utils.auth import require_login, get_token
from utils.api_client import get, post, put, delete, post_file
from utils.banners import show_anonymised_banner

st.set_page_config(page_title="Admin", layout="wide")

if not require_login():
    st.stop()

show_anonymised_banner()

token = get_token()

st.title("Admin")

st.subheader("Current Ruleset")
resp = get("/admin/ruleset", token=token)
if resp.status_code == 200:
    st.json(resp.json())
else:
    st.warning("Unable to load ruleset")

st.subheader("Update Config")
config_key = st.text_input("Config key")
config_value = st.text_area("Config JSON value")

if st.button("Update Config") and config_key and config_value:
    try:
        value = json.loads(config_value)
        resp = post("/admin/config", {"values": {config_key: value}}, token=token)
        if resp.status_code == 200:
            st.success("Config updated")
        else:
            st.error("Config update failed")
    except Exception:
        st.error("Invalid JSON")

st.divider()
st.subheader("Reference Thresholds")
st.info("Thresholds are configuration, not medical advice; must be Trust-approved.")

thresholds_resp = get("/admin/thresholds", token=token)
if thresholds_resp.status_code == 200:
    thresholds = thresholds_resp.json()
    st.dataframe(thresholds, use_container_width=True)
else:
    st.warning("Unable to load thresholds")

st.markdown("**Import thresholds (CSV)**")
upload_file = st.file_uploader("Upload thresholds CSV", type=["csv"])
if upload_file is not None and st.button("Import Thresholds"):
    resp = post_file("/admin/thresholds/import", upload_file, token=token)
    if resp.status_code == 200:
        st.success("Thresholds imported")
    else:
        st.error("Import failed")

st.markdown("**Export thresholds**")
export_resp = get("/admin/thresholds/export", token=token, params={"format": "csv"})
if export_resp.status_code == 200:
    csv_payload = export_resp.json().get("csv", "")
    st.download_button(
        "Download CSV",
        data=csv_payload,
        file_name="reference_thresholds.csv",
        mime="text/csv",
    )

st.markdown("**Create threshold**")
with st.form("create_threshold"):
    monitoring_type = st.text_input("Monitoring type")
    unit = st.text_input("Unit")
    comparator_type = st.selectbox("Comparator type", ["numeric", "coded"])
    low_critical = st.text_input("Low critical")
    low_warning = st.text_input("Low warning")
    high_warning = st.text_input("High warning")
    high_critical = st.text_input("High critical")
    coded_values = st.text_input("Coded abnormal values (semicolon-separated)")
    enabled = st.checkbox("Enabled", value=True)
    version = st.text_input("Version", value="v1")
    if st.form_submit_button("Create"):
        try:
            payload = {
                "monitoring_type": monitoring_type,
                "unit": unit,
                "comparator_type": comparator_type,
                "low_critical": float(low_critical) if low_critical else None,
                "low_warning": float(low_warning) if low_warning else None,
                "high_warning": float(high_warning) if high_warning else None,
                "high_critical": float(high_critical) if high_critical else None,
                "coded_abnormal_values": [
                    v.strip() for v in coded_values.split(";") if v.strip()
                ]
                if coded_values
                else None,
                "enabled": enabled,
                "version": version,
            }
            resp = post("/admin/thresholds", payload, token=token)
            if resp.status_code == 200:
                st.success("Threshold created")
            else:
                st.error("Create failed")
        except ValueError:
            st.error("Invalid numeric value")

st.markdown("**Update/Delete threshold**")
threshold_id = st.text_input("Threshold ID")
threshold_json = st.text_area("Threshold JSON (same schema as create)")
col1, col2 = st.columns(2)
with col1:
    if st.button("Update Threshold") and threshold_id and threshold_json:
        try:
            payload = json.loads(threshold_json)
            resp = put(f"/admin/thresholds/{threshold_id}", payload, token=token)
            if resp.status_code == 200:
                st.success("Threshold updated")
            else:
                st.error("Update failed")
        except Exception:
            st.error("Invalid JSON")
with col2:
    if st.button("Delete Threshold") and threshold_id:
        resp = delete(f"/admin/thresholds/{threshold_id}", token=token)
        if resp.status_code == 200:
            st.success("Threshold deleted")
        else:
            st.error("Delete failed")
