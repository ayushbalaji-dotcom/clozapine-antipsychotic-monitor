import streamlit as st
from utils.auth import require_login
from utils.banners import show_anonymised_banner

st.set_page_config(page_title="Antipsychotic Monitoring Tracker", layout="wide")

if not require_login():
    st.stop()

show_anonymised_banner()

st.sidebar.title("Navigation")
st.sidebar.info("Use the pages in the sidebar")

st.title("Dashboard")
st.write("Select a page from the sidebar.")
