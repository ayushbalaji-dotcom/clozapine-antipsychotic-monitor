from __future__ import annotations


class NotesAdapter:
    """
    Prompted-only notes stub.

    Notes are not stored or ingested in v1. This adapter exists to
    provide a future extension point for prompted summaries without
    persisting free-text notes.
    """

    def fetch_notes(self, pseudonym: str, prompt: str | None = None) -> dict:
        return {
            "status": "unsupported",
            "message": "Notes storage is disabled in anonymised mode",
            "pseudonym": pseudonym,
            "prompt": prompt,
            "notes": None,
        }
