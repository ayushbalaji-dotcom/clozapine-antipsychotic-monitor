import os
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")


def _auth_headers(token: str | None = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def post(path: str, json: dict, token: str | None = None):
    headers = {"Content-Type": "application/json", **_auth_headers(token)}
    return requests.post(f"{BASE_URL}{path}", json=json, headers=headers, timeout=10)


def get(path: str, token: str | None = None, params: dict | None = None):
    return requests.get(f"{BASE_URL}{path}", headers=_auth_headers(token), params=params, timeout=10)


def put(path: str, json: dict, token: str | None = None):
    headers = {"Content-Type": "application/json", **_auth_headers(token)}
    return requests.put(f"{BASE_URL}{path}", json=json, headers=headers, timeout=10)


def delete(path: str, token: str | None = None):
    return requests.delete(f"{BASE_URL}{path}", headers=_auth_headers(token), timeout=10)


def post_file(path: str, upload_file, token: str | None = None):
    headers = _auth_headers(token)
    files = {"file": (upload_file.name, upload_file.getvalue(), "text/csv")}
    return requests.post(f"{BASE_URL}{path}", files=files, headers=headers, timeout=30)
