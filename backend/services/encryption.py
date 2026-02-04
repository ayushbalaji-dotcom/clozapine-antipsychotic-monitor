from functools import lru_cache
from cryptography.fernet import Fernet, InvalidToken
from ..config import get_settings


@lru_cache
def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.FIELD_ENCRYPTION_KEY:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not set")
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt_value(value: str) -> str:
    if value == "":
        return value
    f = _get_fernet()
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    if value == "":
        return value
    f = _get_fernet()
    try:
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise RuntimeError("Decryption failed: invalid token")
