import os
import streamlit as st


def show_anonymised_banner() -> None:
    allow_identifiers = os.getenv("ALLOW_IDENTIFIERS", "false").lower() == "true"
    if not allow_identifiers:
        st.warning("ANONYMISED MODE: Identifiers are disabled (pseudonymised data only).")
