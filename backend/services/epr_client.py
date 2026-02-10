from __future__ import annotations

from datetime import date, datetime
from typing import Any

import requests

from ..config import get_settings


class EPRClient:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.EPR_MODE == "OFF":
            raise RuntimeError("EPR integration is disabled")
        if not settings.EPR_BASE_URL:
            raise RuntimeError("EPR_BASE_URL is not configured")
        self.base_url = settings.EPR_BASE_URL.rstrip("/")
        self.timeout = settings.EPR_TIMEOUT_SECONDS
        self.headers: dict[str, str] = {}
        if settings.EPR_API_KEY:
            if settings.EPR_API_KEY.startswith("Bearer "):
                self.headers["Authorization"] = settings.EPR_API_KEY
            else:
                self.headers["X-API-Key"] = settings.EPR_API_KEY

    def fetch_patient(self, nhs_number: str) -> dict[str, Any] | None:
        response = requests.get(
            f"{self.base_url}/Patient",
            params={"identifier": nhs_number},
            headers=self.headers,
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return _unwrap_single_resource(data)

    def fetch_observations(self, patient_id: str) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/Observation",
            params={"patient": patient_id},
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return _unwrap_list(data=response.json())

    def fetch_medications(self, patient_id: str) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/MedicationRequest",
            params={"patient": patient_id},
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return _unwrap_list(data=response.json())


def _unwrap_single_resource(data: Any) -> dict[str, Any] | None:
    if data is None:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict) and "entry" in data:
        entries = data.get("entry") or []
        if not entries:
            return None
        resource = entries[0].get("resource")
        return resource or entries[0]
    return data if isinstance(data, dict) else None


def _unwrap_list(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and "entry" in data:
        items = []
        for entry in data.get("entry") or []:
            resource = entry.get("resource")
            items.append(resource or entry)
        return [item for item in items if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def get_field(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None
