import hashlib
import hmac
from fastapi import Header, HTTPException, status
from .config import get_settings


def _hash_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_api_key(x_api_key: str | None = Header(default=None)) -> dict:
    settings = get_settings()
    if not settings.INTEGRATION_API_KEY_HASH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration API key not configured",
        )
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    expected = settings.INTEGRATION_API_KEY_HASH.strip()
    provided = _hash_key(x_api_key)
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    return {"actor": "INTEGRATION_API_KEY"}
