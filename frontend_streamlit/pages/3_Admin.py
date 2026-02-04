import streamlit as st
from utils.auth import require_login, get_token
from utils.api_client import get, post
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
        import json

        value = json.loads(config_value)
        resp = post("/admin/config", {"values": {config_key: value}}, token=token)
        if resp.status_code == 200:
            st.success("Config updated")
        else:
            st.error("Config update failed")
    except Exception:
        st.error("Invalid JSON")
