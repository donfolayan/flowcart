import json
import logging
import logging.config
from pathlib import Path
from typing import Any, Dict

from app.core.config import config


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request_id if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id  # type: ignore[attr-defined]

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)  # type: ignore[attr-defined]

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any other custom attributes from extra={}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "request_id",
                "extra_fields",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging():
    LOG_LEVEL = config.LOG_LEVEL
    LOG_FORMAT = config.LOG_FORMAT
    LOG_DIR = Path(config.LOG_DIR)
    LOG_FILE_APP = config.LOG_FILE_APP
    LOG_FILE_DB = config.LOG_FILE_DB

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path_app = LOG_DIR / LOG_FILE_APP
    log_path_db = LOG_DIR / LOG_FILE_DB

    formatters_config = {
        "console": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": JSONFormatter,
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    }

    handlers_config = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console" if LOG_FORMAT == "console" else "json",
            "stream": "ext://sys.stdout",
        },
        "error": {
            "class": "logging.StreamHandler",
            "formatter": "console" if LOG_FORMAT == "console" else "json",
            "level": "ERROR",
            "stream": "ext://sys.stderr",
        },
        "file_app": {
            "class": "logging.FileHandler",
            "filename": str(log_path_app),
            "mode": "a",
            "formatter": "console" if LOG_FORMAT == "console" else "json",
        },
        "file_db": {
            "class": "logging.FileHandler",
            "filename": str(log_path_db),
            "mode": "a",
            "formatter": "console" if LOG_FORMAT == "console" else "json",
        },
    }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters_config,
            "handlers": handlers_config,
            "root": {
                "level": LOG_LEVEL,
                "handlers": ["console", "error"],
            },
            "loggers": {
                "app": {
                    "level": LOG_LEVEL,
                    "handlers": ["console", "error", "file_app"],
                    "propagate": False,
                },
                "db": {
                    "level": "INFO",
                    "handlers": ["console", "error", "file_db"],
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": "INFO",
                },
                "uvicorn.access": {
                    "level": "INFO",
                },
                "sqlalchemy.engine": {
                    "level": "WARNING",
                },
                "sqlalchemy.pool": {
                    "level": "WARNING",
                },
                "sqlalchemy.orm": {
                    "level": "WARNING",
                },
            },
        }
    )
