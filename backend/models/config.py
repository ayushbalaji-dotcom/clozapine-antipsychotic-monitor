from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin


class SystemConfig(Base, UUIDMixin):
    __tablename__ = "system_config"

    key = mapped_column(String(64), unique=True, nullable=False)
    value = mapped_column(JSON, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
