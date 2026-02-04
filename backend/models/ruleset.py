from sqlalchemy import Date, DateTime, JSON, String, func
from sqlalchemy.orm import mapped_column
from .base import Base, UUIDMixin


class RuleSetVersion(Base, UUIDMixin):
    __tablename__ = "ruleset_versions"

    version = mapped_column(String(32), nullable=False)
    effective_from = mapped_column(Date, nullable=False)
    rules_json = mapped_column(JSON, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
