"""Structured logging configuration."""
import json
import logging
import sys
import time

from app.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str | None = None, mode: str = "human") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    if mode == "json":
        fmt: logging.Formatter = JsonFormatter()
    else:
        fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    root.addHandler(handler)
    root.setLevel((level or settings.log_level).upper())
    logging.getLogger("uvicorn.access").setLevel("WARNING")
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("httpcore").setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
