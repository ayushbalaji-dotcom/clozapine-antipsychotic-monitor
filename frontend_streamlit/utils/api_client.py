import os
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")


def _headers(token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def post(path: str, json: dict, token: str | None = None):
    return requests.post(f"{BASE_URL}{path}", json=json, headers=_headers(token), timeout=10)


def get(path: str, token: str | None = None, params: dict | None = None):
    return requests.get(f"{BASE_URL}{path}", headers=_headers(token), params=params, timeout=10)
