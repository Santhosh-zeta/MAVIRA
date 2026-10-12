"""Security controls: SSRF-safe URL validation, upload validation, rate limiting."""
from __future__ import annotations

import ipaddress
import socket
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

import httpcore
import httpcore._backends.sync as _sync_backend
import httpx

BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home", ".corp")
BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata", "instance-data"}
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF validation."""


class SSRFBlockedError(httpcore.ConnectError, UnsafeURLError):
    """Raised when an active socket connection is attempted to a non-public IP."""
    pass


class SSRFSafeSyncBackend(_sync_backend.SyncBackend):
    """Network backend that eliminates DNS rebinding / TOCTOU vulnerabilities.

    Resolves the hostname immediately before TCP connection, validates every
    resolved address against public IP rules, and connects directly to the
    verified IP address. This guarantees that no secondary DNS lookup occurs
    between validation and TCP connection establishment.
    """

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        try:
            ipaddress.ip_address(host)
            literal_ip = True
        except ValueError:
            literal_ip = False

        if literal_ip:
            if not _ip_is_public(host):
                raise SSRFBlockedError(f"SSRF blocked: connection to non-public IP {host}")
            target_ip = host
        else:
            try:
                infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise httpcore.ConnectError(f"DNS resolution failed for {host}") from exc

            for info in infos:
                ip = info[4][0]
                if not _ip_is_public(ip):
                    raise SSRFBlockedError(f"SSRF blocked: {host} resolves to non-public IP {ip}")

            target_ip = infos[0][4][0]

        return super().connect_tcp(
            target_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


def create_ssrf_safe_transport(verify: bool = True, retries: int = 0) -> httpx.HTTPTransport:
    """Create an HTTPX transport with socket-level SSRF defense and IP pinning."""
    pool = httpcore.ConnectionPool(
        network_backend=SSRFSafeSyncBackend(),
        retries=retries,
    )
    transport = httpx.HTTPTransport(verify=verify, retries=retries)
    transport._pool = pool
    return transport


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
