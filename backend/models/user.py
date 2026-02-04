from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username = mapped_column(String(64), unique=True, nullable=False)
    role = mapped_column(String(32), nullable=False, default="admin")
    password_hash = mapped_column(String(256), nullable=False)
    force_password_change = mapped_column(Boolean, default=True, nullable=False)
    last_login_at = mapped_column(DateTime(timezone=True), nullable=True)
