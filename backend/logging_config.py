import logging
import re
from .config import Settings

try:
    from pythonjsonlogger import jsonlogger  # type: ignore
    _HAS_JSONLOGGER = True
except Exception:
    jsonlogger = None
    _HAS_JSONLOGGER = False


class PIIRedactingFilter(logging.Filter):
    _nhs_re = re.compile(r"\b\d{10}\b")
    _mrn_re = re.compile(r"\bMRN[0-9A-Za-z]{4,}\b", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        msg = self._nhs_re.sub("[REDACTED_NHS]", msg)
        msg = self._mrn_re.sub("[REDACTED_MRN]", msg)
        record.msg = msg
        record.args = ()
        return True


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler()

    if settings.LOG_JSON and _HAS_JSONLOGGER:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
        )

    handler.setFormatter(formatter)
    handler.addFilter(PIIRedactingFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Reduce noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
