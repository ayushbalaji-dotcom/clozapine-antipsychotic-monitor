from __future__ import annotations

import hmac
import hashlib
import json
import time
from typing import Any

from fastapi import HTTPException, Request, status

from ..config import get_settings
from .security_store import security_store


class WebhookSecurity:
    def __init__(self):
        self.settings = get_settings()

    def verify_hmac(self, body: bytes, signature: str) -> None:
        if not self.settings.WEBHOOK_SECRET:
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        if signature.startswith("sha256="):
            signature = signature.split("=", 1)[1]
        computed = hmac.new(
            self.settings.WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(computed, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    def verify_timestamp_and_nonce(self, timestamp: int, nonce: str) -> None:
        now = int(time.time())
        if abs(now - timestamp) > self.settings.WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
            raise HTTPException(status_code=401, detail="Stale request")
        key = f"nonce:{nonce}"
        if not security_store.set_if_not_exists(key, "1", self.settings.REPLAY_TTL_SECONDS):
            raise HTTPException(status_code=409, detail="Replay detected")

    def enforce_rate_limit(self, source: str) -> None:
        now = int(time.time())
        hour_bucket = now // 3600
        key = f"rl:{source}:{hour_bucket}"
        count = security_store.incr(key, 3600)
        if count > self.settings.RATE_LIMIT_MAX_PER_HOUR + self.settings.RATE_LIMIT_BURST:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    def enforce_idempotency(self, idempotency_key: str) -> bool:
        key = f"idem:{idempotency_key}"
        return security_store.set_if_not_exists(key, "1", self.settings.IDEMPOTENCY_TTL_SECONDS)

    async def validate_request(self, request: Request) -> bytes:
        signature = request.headers.get("X-Signature", "")
        timestamp = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")
        source = request.headers.get("X-Source-System", "unknown")
        idempotency_key = request.headers.get("Idempotency-Key", "")

        body = await request.body()

        self.verify_hmac(body, signature)
        if not timestamp or not nonce:
            raise HTTPException(status_code=400, detail="Missing timestamp/nonce")
        self.verify_timestamp_and_nonce(int(timestamp), nonce)
        self.enforce_rate_limit(source)

        if not idempotency_key:
            raise HTTPException(status_code=400, detail="Missing idempotency key")
        if not self.enforce_idempotency(idempotency_key):
            raise HTTPException(status_code=202, detail="Duplicate request")

        return body
