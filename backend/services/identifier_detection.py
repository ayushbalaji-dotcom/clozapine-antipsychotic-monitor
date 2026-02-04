from __future__ import annotations

import re
from typing import Any, Iterable

# Banned column names (case-insensitive) for ingestion payloads
BANNED_COLUMNS = {
    "nhs_number",
    "nhs_no",
    "nhs",
    "chi_number",
    "mrn",
    "hospital_number",
    "patient_id",
    "name",
    "first_name",
    "last_name",
    "surname",
    "forename",
    "dob",
    "date_of_birth",
    "birth_date",
    "address",
    "postcode",
    "zip",
    "phone",
    "telephone",
    "mobile",
    "email",
    "notes",
    "comment",
    "free_text",
}


IDENTIFIER_PATTERNS: dict[str, re.Pattern[str]] = {
    "nhs_number": re.compile(r"\b\d{10}\b"),
    "dob": re.compile(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+44|0)\d{9,10}\b"),
    "postcode": re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b", re.IGNORECASE),
    "mrn": re.compile(r"\bMRN[0-9A-Za-z]{4,}\b", re.IGNORECASE),
}


def banned_columns_found(columns: Iterable[str]) -> list[str]:
    return [col for col in columns if col.lower() in BANNED_COLUMNS]


def find_identifier_matches(value: str) -> list[str]:
    if not value:
        return []
    matches: list[str] = []
    for name, pattern in IDENTIFIER_PATTERNS.items():
        if pattern.search(value):
            matches.append(name)
    return matches


def scan_payload_for_identifiers(payload: Any) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []

    def _scan(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                _scan(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, (list, tuple, set)):
            for idx, child in enumerate(value):
                _scan(child, f"{path}[{idx}]")
            return
        if isinstance(value, str):
            matches = find_identifier_matches(value)
            for match in matches:
                risks.append({"path": path, "pattern": match})

    _scan(payload, "")
    return risks


def redact_identifiers(text: str) -> tuple[str, list[str]]:
    if not text:
        return text, []
    redacted = text
    hits: list[str] = []
    for name, pattern in IDENTIFIER_PATTERNS.items():
        if pattern.search(redacted):
            hits.append(name)
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, hits
