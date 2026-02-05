import os
import requests
from requests import Response
from requests.exceptions import RequestException

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
DEFAULT_TIMEOUT = 30


def _auth_headers(token: str | None = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _error_response(error: Exception) -> Response:
    resp = Response()
    resp.status_code = 503
    resp._content = f"Backend unavailable: {error}".encode("utf-8")
    return resp


def post(path: str, json: dict, token: str | None = None):
    headers = {"Content-Type": "application/json", **_auth_headers(token)}
    try:
        return requests.post(
            f"{BASE_URL}{path}", json=json, headers=headers, timeout=DEFAULT_TIMEOUT
        )
    except RequestException as exc:
        return _error_response(exc)


def get(path: str, token: str | None = None, params: dict | None = None):
    try:
        return requests.get(
            f"{BASE_URL}{path}",
            headers=_auth_headers(token),
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
    except RequestException as exc:
        return _error_response(exc)


def put(path: str, json: dict, token: str | None = None):
    headers = {"Content-Type": "application/json", **_auth_headers(token)}
    try:
        return requests.put(
            f"{BASE_URL}{path}", json=json, headers=headers, timeout=DEFAULT_TIMEOUT
        )
    except RequestException as exc:
        return _error_response(exc)


def delete(path: str, token: str | None = None):
    try:
        return requests.delete(
            f"{BASE_URL}{path}", headers=_auth_headers(token), timeout=DEFAULT_TIMEOUT
        )
    except RequestException as exc:
        return _error_response(exc)


def post_file(path: str, upload_file, token: str | None = None):
    headers = _auth_headers(token)
    files = {"file": (upload_file.name, upload_file.getvalue(), "text/csv")}
    try:
        return requests.post(
            f"{BASE_URL}{path}", files=files, headers=headers, timeout=DEFAULT_TIMEOUT
        )
    except RequestException as exc:
        return _error_response(exc)
