import hashlib
import secrets


def main() -> None:
    key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    print("API_KEY:", key)
    print("INTEGRATION_API_KEY_HASH:", key_hash)


if __name__ == "__main__":
    main()
