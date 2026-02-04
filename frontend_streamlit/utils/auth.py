import streamlit as st
from .api_client import post


def require_login():
    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "force_password_change" not in st.session_state:
        st.session_state["force_password_change"] = False

    if st.session_state["token"]:
        return True

    st.title("Antipsychotic Monitoring Tracker")
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        resp = post("/auth/login", {"username": username, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["token"] = data["access_token"]
            st.session_state["force_password_change"] = data.get("force_password_change", False)
            st.success("Logged in")
            st.rerun()
        else:
            st.error("Login failed")
    return False


def get_token() -> str | None:
    return st.session_state.get("token")
