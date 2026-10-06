"""Security controls: SSRF-safe URL validation, upload validation, rate limiting."""
from __future__ import annotations

import ipaddress
import socket
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home", ".corp")
BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata", "instance-data"}
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF validation."""


def _ip_is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast
        or addr.is_reserved or addr.is_unspecified
        or (isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None
            and not _ip_is_public(str(addr.ipv4_mapped)))
    )


def validate_public_url(url: str, resolve: bool = True) -> str:
    """Reject anything that could reach internal infrastructure.

    Checks scheme, port, credentials-in-URL, literal IPs, blocked hostnames, and
    (when resolve=True) every DNS answer, which defeats hostnames that point at
    private ranges. The fetcher re-validates after every redirect.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"scheme not allowed: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise UnsafeURLError("credentials in URL are not allowed")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise UnsafeURLError("missing host")
    if parsed.port not in ALLOWED_PORTS:
        raise UnsafeURLError(f"port not allowed: {parsed.port}")
    if host in BLOCKED_HOSTNAMES or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise UnsafeURLError(f"host not allowed: {host}")
    try:
        ipaddress.ip_address(host)
        literal_ip = True
    except ValueError:
        literal_ip = False
    if literal_ip:
        if not _ip_is_public(host):
            raise UnsafeURLError("non-public IP address")
        return url
    if "." not in host:
        raise UnsafeURLError("single-label hostnames are not allowed")
    if resolve:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise UnsafeURLError(f"DNS resolution failed for {host}") from exc
        for info in infos:
            if not _ip_is_public(info[4][0]):
                raise UnsafeURLError(f"{host} resolves to a non-public address")
    return url


XLSX_MAGIC = b"PK\x03\x04"


def validate_xlsx_upload(filename: str, data: bytes, max_mb: int) -> None:
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise ValueError("Only .xlsx workbooks are accepted")
    if len(data) == 0:
        raise ValueError("Uploaded file is empty")
    if len(data) > max_mb * 1024 * 1024:
        raise ValueError(f"File exceeds the {max_mb} MB upload limit")
    if not data.startswith(XLSX_MAGIC):
        raise ValueError("File is not a valid Office Open XML workbook")


class RateLimiter:
    """Simple in-process sliding-window limiter keyed by client id."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True
