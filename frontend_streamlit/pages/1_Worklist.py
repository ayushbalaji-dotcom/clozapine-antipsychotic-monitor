import streamlit as st
from utils.auth import require_login, get_token
from utils.api_client import get
from utils.banners import show_anonymised_banner

st.set_page_config(page_title="Worklist", layout="wide")

if not require_login():
    st.stop()

show_anonymised_banner()

token = get_token()

st.title("Active Worklist")

status = st.selectbox("Status", ["", "DUE", "OVERDUE", "DONE", "WAIVED"], index=0)
category = st.selectbox("Drug Category", ["", "STANDARD", "SPECIAL_GROUP", "HDAT"], index=0)
urgent_only = st.checkbox("Has urgent alerts")

params = {}
if status:
    params["status"] = status
if category:
    params["drug_category"] = category
if urgent_only:
    params["has_urgent_alerts"] = "true"

resp = get("/worklist", token=token, params=params)
if resp.status_code != 200:
    st.error("Failed to load worklist")
    st.stop()

items = resp.json().get("items", [])
if not items:
    st.info("No tasks found")
else:
    st.caption("Urgent alerts are based on unacknowledged critical notifications.")
    st.dataframe(items, use_container_width=True)
