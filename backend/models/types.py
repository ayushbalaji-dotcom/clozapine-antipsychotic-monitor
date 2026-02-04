from sqlalchemy import String
from sqlalchemy.types import TypeDecorator
from ..services.encryption import encrypt_value, decrypt_value


class EncryptedString(TypeDecorator):
    impl = String(512)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_value(value)
