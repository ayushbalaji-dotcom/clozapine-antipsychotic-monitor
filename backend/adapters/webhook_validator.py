import hmac
import hashlib
from . import fhir_adapter  # noqa: F401


def verify_hmac(payload: bytes, signature: str, secret: str) -> bool:
    if signature.startswith("sha256="):
        signature = signature.split("=", 1)[1]
    computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)
