# Webhook Setup

## Required Headers
- `X-Signature`
- `X-Timestamp`
- `X-Nonce`
- `X-Source-System`
- `Idempotency-Key`

## Example Signature (Python)
```python
import hmac, hashlib
body = b"{...}"
secret = b"shared-secret"
signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
```
