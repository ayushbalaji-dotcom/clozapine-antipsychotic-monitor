import streamlit as st
from utils.auth import require_login, get_token
from utils.api_client import get, post
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

    tabs = st.tabs(["Tasks", "Medications", "Events", "Alerts"])

    with tabs[0]:
        st.dataframe(data.get("tasks", []), use_container_width=True)

    with tabs[1]:
        st.dataframe(data.get("medications", []), use_container_width=True)

    with tabs[2]:
        st.dataframe(data.get("events", []), use_container_width=True)

    with tabs[3]:
        notif_resp = get("/notifications", token=token, params={"patient_id": patient_id})
        if notif_resp.status_code != 200:
            st.error("Failed to load alerts")
        else:
            alerts = notif_resp.json().get("items", [])
            if not alerts:
                st.info("No alerts for this patient")
            else:
                for alert in alerts:
                    title = f"{alert['priority']} | {alert['title']}"
                    with st.expander(title):
                        st.write(alert.get("message", ""))
                        meta = alert.get("metadata", {})
                        st.write(
                            f"Patient: {meta.get('pseudonym')} | Test: {meta.get('test_type')} | "
                            f"Date: {meta.get('performed_date') or meta.get('due_date')}"
                        )
                        value = meta.get("value")
                        unit = meta.get("unit")
                        if value:
                            st.write(f"Value: {value} {unit or ''}")
                        st.write(f"Status: {alert.get('status')}")

                        if alert.get("status") != "ACKED":
                            if st.button("Mark reviewed", key=f"ack-{alert['id']}"):
                                ack_resp = post(
                                    f"/notifications/{alert['id']}/ack",
                                    {},
                                    token=token,
                                )
                                if ack_resp.status_code == 200:
                                    st.success("Marked reviewed")
                                else:
                                    st.error("Failed to acknowledge alert")
