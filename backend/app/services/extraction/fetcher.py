"""Polite, SSRF-safe page fetcher for LIVE mode.

- validates every URL (and every redirect hop) against private networks
- honours robots.txt for our user agent
- per-domain minimum interval, timeouts, bounded retries with backoff
- conditional requests with ETag / Last-Modified, response size cap
- HTML via trafilatura (fallback BeautifulSoup); PDFs are not parsed in v1

JavaScript rendering (Playwright) is intentionally not bundled; pages that need
it return thin content and are recorded as such rather than guessed at.
"""
from __future__ import annotations

import threading
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.security import UnsafeURLError, validate_public_url

log = get_logger(__name__)


@dataclass
class FetchResult:
    url: str
    status: str                   # OK | NOT_MODIFIED | ROBOTS_DENIED | BLOCKED_URL | HTTP_ERROR | TIMEOUT | UNSUPPORTED | ERROR
    http_status: int | None = None
    title: str | None = None
    text: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    published_date: str | None = None
    error: str | None = None
    retries: int = 0
    latency_ms: int | None = None


class Fetcher:
    MAX_REDIRECTS = 5

    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        self.client = httpx.Client(timeout=self.s.fetch_timeout_seconds, follow_redirects=False,
                                   headers={"User-Agent": self.s.user_agent, "Accept": "text/html,application/xhtml+xml"})
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}
        self._lock = threading.Lock()

    # -- politeness -------------------------------------------------------
    def _throttle(self, host: str) -> None:
        with self._lock:
            wait = self._last_hit.get(host, 0) + self.s.per_domain_min_interval_seconds - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_hit[host] = time.monotonic()

    def robots_allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                validate_public_url(base + "/robots.txt")
                r = self.client.get(base + "/robots.txt")
                if r.status_code >= 400:
                    rp = None                      # no robots file -> allowed
                else:
                    rp.parse(r.text.splitlines())
            except (httpx.HTTPError, UnsafeURLError):
                rp = None
            self._robots[base] = rp
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(self.s.user_agent, url)

    # -- fetch ------------------------------------------------------------
    def fetch(self, url: str, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        t0 = time.monotonic()
        try:
            validate_public_url(url)
        except UnsafeURLError as exc:
            return FetchResult(url, "BLOCKED_URL", error=str(exc))
        if not self.robots_allowed(url):
            return FetchResult(url, "ROBOTS_DENIED", error="Disallowed by robots.txt")

        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        retries, current = 0, url
        while True:
            try:
                self._throttle(urlparse(current).hostname or "")
                for _ in range(self.MAX_REDIRECTS + 1):
                    with self.client.stream("GET", current, headers=headers) as r:
                        if r.is_redirect:
                            nxt = urljoin(current, r.headers.get("location", ""))
                            validate_public_url(nxt)            # re-check every hop
                            current = nxt
                            continue
                        if r.status_code == 304:
                            return FetchResult(url, "NOT_MODIFIED", 304, etag=etag, last_modified=last_modified,
                                               retries=retries, latency_ms=_ms(t0))
                        if r.status_code in (429,) or r.status_code >= 500:
                            raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
                        if r.status_code >= 400:
                            return FetchResult(url, "HTTP_ERROR", r.status_code, error=f"HTTP {r.status_code}",
                                               retries=retries, latency_ms=_ms(t0))
                        ctype = r.headers.get("content-type", "")
                        if "html" not in ctype and "text/plain" not in ctype:
                            return FetchResult(url, "UNSUPPORTED", r.status_code, error=f"content-type {ctype}",
                                               retries=retries, latency_ms=_ms(t0))
                        body = bytearray()
                        for chunk in r.iter_bytes():
                            body.extend(chunk)
                            if len(body) > self.s.fetch_max_bytes:
                                break
                        html = body.decode(r.encoding or "utf-8", errors="replace")
                        title, text, pub = extract_html(html, current)
                        return FetchResult(current, "OK", r.status_code, title=title, text=text,
                                           etag=r.headers.get("etag"), last_modified=r.headers.get("last-modified"),
                                           published_date=pub, retries=retries, latency_ms=_ms(t0))
                return FetchResult(url, "ERROR", error="too many redirects", retries=retries, latency_ms=_ms(t0))
            except UnsafeURLError as exc:
                return FetchResult(url, "BLOCKED_URL", error=f"redirect blocked: {exc}", latency_ms=_ms(t0))
            except httpx.TimeoutException:
                status, err = "TIMEOUT", "request timed out"
            except httpx.HTTPError as exc:
                status, err = "ERROR", type(exc).__name__
            if retries >= self.s.fetch_retries:
                return FetchResult(url, status, error=err, retries=retries, latency_ms=_ms(t0))
            retries += 1
            time.sleep(0.75 * (2 ** retries))


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def extract_html(html: str, url: str) -> tuple[str | None, str, str | None]:
    title, text, published = None, "", None
    try:
        import trafilatura
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=True,
                                   favor_precision=True) or ""
        meta = trafilatura.extract_metadata(html)
        if meta:
            title, published = meta.title, meta.date
    except Exception:  # noqa: BLE001 - extractor failures fall back to bs4
        text = ""
    if not text:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
            tag.decompose()
        title = title or (soup.title.string.strip() if soup.title and soup.title.string else None)
        text = "\n\n".join(p.get_text(" ", strip=True) for p in soup.find_all(["h1", "h2", "h3", "p", "li"]))
    return title, text, published
