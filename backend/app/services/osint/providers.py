"""Search-provider abstraction.

Live adapters (Tavily, Serper, Brave) and the cached snapshot provider share one
interface. Each hit carries its collection method so the UI and export can
always tell LIVE, CACHED and DEMO_MOCK material apart.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class SearchHit:
    url: str
    title: str | None = None
    snippet: str | None = None
    collection_method: str = "LIVE"          # LIVE | CACHED | DEMO_MOCK
    content: str | None = None               # pre-fetched content (cached provider only)
    published_date: str | None = None
    retrieved_at: str | None = None
    cache_origin: str | None = None
    extra: dict = field(default_factory=dict)


class SearchError(RuntimeError):
    pass


class SearchProvider(ABC):
    name: str = "abstract"
    collection_method: str = "LIVE"

    @abstractmethod
    def search(self, query: str, *, category: str, vendor_ref: str, max_results: int = 5) -> list[SearchHit]:
        ...


class _HttpProvider(SearchProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(timeout=settings.fetch_timeout_seconds,
                                   headers={"User-Agent": settings.user_agent})

    def _post(self, url: str, **kw) -> dict:
        last: Exception | None = None
        for attempt in range(self.settings.fetch_retries + 1):
            try:
                r = self.client.post(url, **kw) if "json" in kw else self.client.get(url, **kw)
                if r.status_code == 429 or r.status_code >= 500:
                    raise SearchError(f"{self.name} HTTP {r.status_code}")
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, SearchError, json.JSONDecodeError) as exc:
                last = exc
                time.sleep(0.5 * (2 ** attempt))
        raise SearchError(f"{self.name} search failed: {last}")


class TavilyProvider(_HttpProvider):
    name = "tavily"

    def search(self, query, *, category, vendor_ref, max_results=5):
        if not self.settings.tavily_api_key:
            raise SearchError("TAVILY_API_KEY not configured")
        data = self._post("https://api.tavily.com/search",
                          json={"query": query, "max_results": max_results, "search_depth": "basic"},
                          headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"})
        return [SearchHit(url=r["url"], title=r.get("title"), snippet=r.get("content"))
                for r in data.get("results", [])]


class SerperProvider(_HttpProvider):
    name = "serper"

    def search(self, query, *, category, vendor_ref, max_results=5):
        if not self.settings.serper_api_key:
            raise SearchError("SERPER_API_KEY not configured")
        data = self._post("https://google.serper.dev/search", json={"q": query, "num": max_results},
                          headers={"X-API-KEY": self.settings.serper_api_key})
        return [SearchHit(url=r["link"], title=r.get("title"), snippet=r.get("snippet"))
                for r in data.get("organic", [])[:max_results]]


class BraveProvider(_HttpProvider):
    name = "brave"

    def search(self, query, *, category, vendor_ref, max_results=5):
        if not self.settings.brave_api_key:
            raise SearchError("BRAVE_API_KEY not configured")
        data = self._post("https://api.search.brave.com/res/v1/web/search",
                          params={"q": query, "count": max_results},
                          headers={"X-Subscription-Token": self.settings.brave_api_key,
                                   "Accept": "application/json"})
        return [SearchHit(url=r["url"], title=r.get("title"), snippet=r.get("description"))
                for r in data.get("web", {}).get("results", [])[:max_results]]


@lru_cache
def _load_cache(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class CachedSnapshotProvider(SearchProvider):
    """Serves the OSINT snapshot shipped in app/demo_data/osint_cache.json.

    The snapshot holds verbatim passages retrieved from real public pages during
    an analyst session, labelled CACHED with their retrieval timestamp. A cached
    source is returned only for the query categories that originally surfaced
    it, so assessment depth still governs what a vendor's review sees.
    """

    name = "cached-snapshot"
    collection_method = "CACHED"

    def __init__(self, path: Path):
        self.path = str(path)

    def search(self, query, *, category, vendor_ref, max_results=5):
        data = _load_cache(self.path)
        hits = []
        for s in data["sources"]:
            if s["vendor_ref"] == vendor_ref and category in s.get("found_by", []):
                hits.append(SearchHit(url=s["url"], title=s.get("title"), collection_method=s.get("collection_method", "CACHED"),
                                      content=s["content"], published_date=s.get("published_date"),
                                      retrieved_at=s.get("retrieved_at"), cache_origin=s.get("cache_origin")))
        return hits[:max_results]

    def search_log(self, vendor_ref: str) -> list[dict]:
        return [e for e in _load_cache(self.path).get("search_log", []) if e["vendor_ref"] == vendor_ref]


class FixtureProvider(SearchProvider):
    """In-memory provider for tests and the fictional worked example (DEMO_MOCK)."""

    name = "fixture"
    collection_method = "DEMO_MOCK"

    def __init__(self, sources: list[dict]):
        self.sources = sources

    def search(self, query, *, category, vendor_ref, max_results=5):
        return [SearchHit(url=s["url"], title=s.get("title"), collection_method="DEMO_MOCK", content=s["content"],
                          published_date=s.get("published_date"), retrieved_at=s.get("retrieved_at"),
                          cache_origin="Fictional test fixture — not real evidence")
                for s in self.sources
                if s["vendor_ref"] == vendor_ref and category in s.get("found_by", [category])][:max_results]


def get_provider(settings: Settings | None = None) -> SearchProvider:
    s = settings or get_settings()
    if s.osint_mode.upper() != "LIVE":
        return CachedSnapshotProvider(s.demo_cache_path)
    provider = s.search_provider.lower()
    if provider == "tavily":
        return TavilyProvider(s)
    if provider == "serper":
        return SerperProvider(s)
    if provider == "brave":
        return BraveProvider(s)
    raise SearchError("OSINT_MODE=LIVE requires SEARCH_PROVIDER to be tavily, serper or brave")
