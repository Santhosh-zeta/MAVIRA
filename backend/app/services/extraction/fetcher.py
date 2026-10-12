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
from app.core.security import SSRFBlockedError, UnsafeURLError, create_ssrf_safe_transport, validate_public_url

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
        self.client = httpx.Client(
            timeout=self.s.fetch_timeout_seconds,
            follow_redirects=False,
            transport=create_ssrf_safe_transport(retries=0),
            headers={"User-Agent": self.s.user_agent, "Accept": "text/html,application/xhtml+xml,application/pdf"},
        )
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
                        ctype = r.headers.get("content-type", "").lower()
                        is_pdf = "pdf" in ctype or current.lower().split("?")[0].endswith(".pdf")
                        if not is_pdf and "html" not in ctype and "text/plain" not in ctype:
                            return FetchResult(url, "UNSUPPORTED", r.status_code, error=f"content-type {ctype}",
                                               retries=retries, latency_ms=_ms(t0))

                        body = bytearray()
                        for chunk in r.iter_bytes():
                            body.extend(chunk)
                            if len(body) > self.s.fetch_max_bytes:
                                break

                        if is_pdf:
                            title, text, pub = extract_pdf(bytes(body), current)
                        else:
                            html = body.decode(r.encoding or "utf-8", errors="replace")
                            title, text, pub = extract_html(html, current)
                            # JavaScript-heavy SPA fallback: if text extracted is thin, attempt Playwright rendering
                            if len(text.strip()) < 150:
                                pw_title, pw_text, pw_pub = render_with_playwright(current, timeout_seconds=self.s.fetch_timeout_seconds)
                                if pw_text and len(pw_text.strip()) > len(text.strip()):
                                    title, text = pw_title or title, pw_text
                                    pub = pw_pub or pub

                        return FetchResult(current, "OK", r.status_code, title=title, text=text,
                                           etag=r.headers.get("etag"), last_modified=r.headers.get("last-modified"),
                                           published_date=pub, retries=retries, latency_ms=_ms(t0))
                return FetchResult(url, "ERROR", error="too many redirects", retries=retries, latency_ms=_ms(t0))
            except (UnsafeURLError, SSRFBlockedError) as exc:
                return FetchResult(url, "BLOCKED_URL", error=f"SSRF blocked: {exc}", latency_ms=_ms(t0))
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


def extract_pdf(data: bytes, url: str) -> tuple[str | None, str, str | None]:
    """Extract text and metadata from PDF bytes using pypdf."""
    title, text, published = None, "", None
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.metadata:
            if reader.metadata.title:
                title = str(reader.metadata.title).strip()
            if reader.metadata.creation_date:
                try:
                    published = str(reader.metadata.creation_date.date())
                except Exception:
                    published = None
        pages_text = []
        for page in reader.pages[:50]:  # safety cap at 50 pages
            t = page.extract_text() or ""
            if t.strip():
                pages_text.append(t.strip())
        text = "\n\n".join(pages_text)
    except Exception as exc:  # noqa: BLE001
        log.warning("pdf extraction failed", extra={"url": url, "error": str(exc)})
    return title, text, published


def render_with_playwright(url: str, timeout_seconds: float = 10.0) -> tuple[str | None, str, str | None]:
    """Fallback headless browser rendering for JavaScript-heavy single-page applications."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(int(timeout_seconds * 1000))
            page.goto(url, wait_until="domcontentloaded")
            html = page.content()
            title = page.title()
            browser.close()
            _, text, published = extract_html(html, url)
            return title or None, text, published
    except Exception as exc:  # noqa: BLE001 - graceful fallback if playwright/browser unavailable
        log.debug("playwright fallback skipped or unavailable", extra={"url": url, "error": str(exc)})
        return None, "", None


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
