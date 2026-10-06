from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request

from app.core.config import get_settings
from app.core.security import RateLimiter

_settings = get_settings()
upload_limiter = RateLimiter(_settings.upload_rate_per_minute)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optional shared-key protection. When API_KEY is unset the API is open
    (local single-analyst deployment); set it for any shared environment."""
    expected = get_settings().api_key
    if expected and not (x_api_key and hmac.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def actor(x_analyst: str | None = Header(default=None)) -> str:
    return (x_analyst or "analyst").strip()[:120] or "analyst"
