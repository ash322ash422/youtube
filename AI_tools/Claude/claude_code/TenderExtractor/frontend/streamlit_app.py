"""
Streamlit front-end for TenderExtractor.

    streamlit run frontend/streamlit_app.py

Talks to the FastAPI backend (backend/app/api/main.py) over HTTP - log in
to get a JWT, then upload/poll/download using that token. No backend code
is imported directly (unlike the old version of this file), so this can
run against a backend on a different host/process/deployment entirely.

The JWT lives only in st.session_state (server-side, tied to this
Streamlit session) - it's never sent to or stored in the user's browser,
unlike a typical SPA's localStorage token.
"""
import os
import time
from pathlib import Path
from typing import Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("TENDEREXTRACTOR_API_URL", "http://127.0.0.1:8000").rstrip("/")
POLL_INTERVAL_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 30

st.set_page_config(page_title="TenderExtractor", page_icon="📄")


def _login(username: str, password: str) -> Optional[str]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            data={"username": username, "password": password},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.ConnectionError:
        st.error(f"Could not reach the API at {API_BASE_URL}. Is it running?")
        return None

    if response.status_code != 200:
        st.error("Invalid username or password.")
        return None

    return response.json()["access_token"]


def _authed_request(method: str, path: str, **kwargs) -> requests.Response:
    """
    Wraps requests.request() with the bearer token, timeout, and shared
    error handling: a dead API halts the script with a clear message, and
    an expired/invalid token drops the session back to the login form.
    """
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)

    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", headers=headers, **kwargs)
    except requests.ConnectionError:
        st.error(f"Could not reach the API at {API_BASE_URL}. Is it running?")
        st.stop()

    if response.status_code == 401:
        st.session_state.pop("access_token", None)
        st.error("Your session expired. Please log in again.")
        st.rerun()

    return response


def _show_login_form() -> None:
    st.title("TenderExtractor")
    st.subheader("Log in")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        token = _login(username, password)
        if token:
            st.session_state.access_token = token
            st.rerun()


def _run_extraction(uploaded_file) -> None:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    response = _authed_request("POST", "/tenders", files=files)

    if response.status_code != 202:
        st.error(f"Upload failed: {response.json().get('detail', response.text)}")
        return

    job_id = response.json()["job_id"]
    status_box = st.empty()
    start_time = time.time()

    while True:
        job = _authed_request("GET", f"/tenders/{job_id}").json()
        status = job["status"]
        elapsed = int(time.time() - start_time)

        if status == "COMPLETED":
            status_box.empty()
            st.success(f"Extraction complete for '{job['blob_name']}'.")
            download = _authed_request("GET", f"/tenders/{job_id}/download")
            if download.status_code == 200:
                st.download_button(
                    "Download Excel",
                    data=download.content,
                    file_name=f"{Path(job['blob_name']).stem}.xlsx",
                    use_container_width=True,
                )
            else:
                st.error("Job completed, but the file could not be downloaded from the API.")
            return

        if status == "FAILED":
            status_box.empty()
            st.error(f"Extraction failed at stage '{job.get('failed_stage')}': {job.get('error')}")
            return

        status_box.info(f"⏳ {status} ({elapsed}s elapsed) — this can take 2-3 minutes, please wait.")
        time.sleep(POLL_INTERVAL_SECONDS)


def _show_app() -> None:
    header_col, logout_col = st.columns([5, 1])
    with header_col:
        st.title("TenderExtractor")
    with logout_col:
        if st.button("Log out"):
            st.session_state.pop("access_token", None)
            st.rerun()

    uploaded_file = st.file_uploader("Choose a tender PDF", type=["pdf"])

    if st.button("Upload & Extract", disabled=uploaded_file is None, use_container_width=True):
        _run_extraction(uploaded_file)


if "access_token" not in st.session_state:
    _show_login_form()
else:
    _show_app()
