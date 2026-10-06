"""Structured JSON logging with assessment_run_id context and secret redaction."""
from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone

run_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)

_SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|authorization|token|secret)(\"?\s*[:=]\s*\"?)([^\s\",]+)", re.I),
    re.compile(r"sk-[A-Za-z0-9_\-]{10,}"),
]


def redact(text: str) -> str:
    for p in _SECRET_PATTERNS:
        if p.groups >= 3:
            text = p.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
        else:
            text = p.sub("***", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        rid = run_id_ctx.get()
        if rid:
            payload["assessment_run_id"] = rid
        for key in ("vendor", "stage", "source", "status", "latency_ms", "retry", "model", "error"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = redact(str(val)) if isinstance(val, str) else val
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "urllib3", "trafilatura"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
