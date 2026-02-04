# Integration Guide

## Webhook Endpoints
- `POST /api/v1/webhooks/medication`
- `POST /api/v1/webhooks/monitoring-event`

## Required Headers
- `X-Signature: sha256=...`
- `X-Timestamp: <unix seconds>`
- `X-Nonce: <unique nonce>`
- `X-Source-System: <system id>`
- `Idempotency-Key: <unique per request>`

## HMAC
Signature is computed over the raw request body using HMAC-SHA256 and `WEBHOOK_SECRET`.

## Replay Protection
Requests must be within `WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS` and provide a unique nonce.
