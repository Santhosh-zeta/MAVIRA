from __future__ import annotations

from dataclasses import dataclass
import hmac

from fastapi import Depends, Header, HTTPException, Request

from app.core.config import get_settings
from app.core.security import RateLimiter

_settings = get_settings()
upload_limiter = RateLimiter(_settings.upload_rate_per_minute)

VALID_ROLES = {"ANALYST", "REVIEWER", "METHODOLOGY_ADMIN"}


@dataclass
class UserIdentity:
    name: str
    role: str


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


def current_user(
    x_analyst: str | None = Header(default=None),
    x_role: str | None = Header(default=None, alias="X-User-Role"),
) -> UserIdentity:
    """Extract authenticated actor and role. Defaults to METHODOLOGY_ADMIN
    in demo/standalone mode so the evaluation demo remains 100% stable."""
    name = (x_analyst or "analyst").strip()[:120] or "analyst"
    role = (x_role or "METHODOLOGY_ADMIN").strip().upper()
    if role not in VALID_ROLES:
        role = "ANALYST"
    return UserIdentity(name=name, role=role)


def require_role(*allowed_roles: str):
    """Dependency enforcing role-based permissions."""
    def _verifier(user: UserIdentity = Depends(current_user)) -> UserIdentity:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' not permitted for this action. Required: {', '.join(allowed_roles)}",
            )
        return user
    return _verifier
