#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
fi

python - <<'PY'
from cryptography.fernet import Fernet
import secrets

print("FIELD_ENCRYPTION_KEY=", Fernet.generate_key().decode("utf-8"))
print("SECRET_KEY=", secrets.token_urlsafe(32))
PY
