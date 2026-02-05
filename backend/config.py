from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/antipsych_tracker"
    DB_POOL_SIZE: int = 5

    # Encryption
    FIELD_ENCRYPTION_KEY: str = ""
    SECRET_KEY: str = ""
    ALLOW_IDENTIFIERS: bool = False

    # Auth
    AUTH_MODE: str = "dev_stub"
    DEV_ADMIN_USERNAME: str = "admin"
    DEV_ADMIN_PASSWORD: str = "ChangeMe_123!"
    DEV_ADMIN_FORCE_CHANGE: bool = True

    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""

    # Webhooks
    WEBHOOK_SECRET: str = ""
    WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS: int = 600
    IDEMPOTENCY_TTL_SECONDS: int = 86400
    REPLAY_TTL_SECONDS: int = 600
    RATE_LIMIT_MAX_PER_HOUR: int = 100
    RATE_LIMIT_BURST: int = 20

    # Notifications
    IN_APP_NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATIONS_ENABLED: bool = True
    EMAIL_ENABLED: bool = False
    EMAIL_SMTP_HOST: str = ""
    EMAIL_FROM: str = ""
    TEAMS_WEBHOOK_URL: str = ""
    TEAM_INBOX_ID: str = "TEAM_INBOX"
    TEAM_LEAD_INBOX_ID: str = "TEAM_LEAD_INBOX"

    # Monitoring
    TASK_WINDOW_DAYS: int = 14
    ESCALATION_THRESHOLD_DAYS: int = 30
    RETENTION_DAYS: int = 90
    SCHEDULING_HORIZON_YEARS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    AUDIT_EXPORT_PATH: str | None = None

    # Environment
    ENVIRONMENT: str = "dev"
    SYNTHETIC_DATA_MODE: bool = True

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_REQUIRED: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
