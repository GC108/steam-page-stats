"""Steam Storefront + appreviews API client. Polite + cached.

This module ONLY hits Steam's public, undocumented-but-widely-used Storefront
API and the appreviews endpoint. No login, no Steamworks. Useful for
calibration sanity checks; NOT for licensable commercial intelligence.

Rate limit: Steam tolerates ~200 req/5min from a single IP for these
endpoints. We default to 1 req/sec with retries on 429.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import httpx


STORE_URL = "https://store.steampowered.com/api/appdetails"
REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"

DEFAULT_USER_AGENT = (
    "steam-page-stats/0.1 (+https://github.com/GC108/steam-page-stats; "
    "calibration-sanity-check)"
)
DEFAULT_TIMEOUT = 15.0
DEFAULT_THROTTLE_S = 1.0


@dataclass(frozen=True)
class PageStats:
    """A snapshot of a Steam game's public page stats."""
    appid: int
    name: str
    is_free: bool
    price_cents: Optional[int]  # None for free games
    review_count_total: Optional[int]
    review_score_pct: Optional[float]  # 0–100
    release_date: Optional[str]  # ISO-ish; Steam returns various formats
    coming_soon: bool
    genres: list[str]
    developer: Optional[str]
    publisher: Optional[str]
    raw: dict  # for debugging / future fields


class SteamPageStatsClient:
    """Async client for Steam's public Storefront + appreviews APIs."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
        throttle_s: float = DEFAULT_THROTTLE_S,
    ):
        self._user_agent = user_agent
        self._timeout = timeout
        self._throttle = throttle_s
        self._last_request_at: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "SteamPageStatsClient":
        self._client = httpx.AsyncClient(
            headers={"User-Agent": self._user_agent},
            timeout=self._timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _throttle_wait(self) -> None:
        if self._throttle <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self._throttle - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_at = time.monotonic()

    async def _get_json(self, url: str, params: dict) -> dict:
        if self._client is None:
            raise RuntimeError(
                "Use SteamPageStatsClient as an async context manager: "
                "`async with SteamPageStatsClient() as c: ...`"
            )
        await self._throttle_wait()
        for attempt in range(3):
            r = await self._client.get(url, params=params)
            if r.status_code == 429 and attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        # Last attempt failure handled by raise_for_status above
        raise RuntimeError(f"unreachable: {url}")

    async def fetch(self, appid: int) -> PageStats:
        """Fetch combined Storefront + reviews data for a single appid."""
        # No `filters=` param: Steam excludes developers/publishers under the
        # `basic` filter, and the full payload is still only ~5-10KB.
        store_resp = await self._get_json(STORE_URL, {"appids": appid})
        reviews_resp = await self._get_json(
            REVIEWS_URL.format(appid=appid),
            {"json": 1, "language": "all", "purchase_type": "all", "num_per_page": 0},
        )

        # Storefront returns {appid: {success: bool, data: {...}}} keyed by appid str
        wrapper = store_resp.get(str(appid), {})
        if not wrapper.get("success"):
            raise ValueError(f"Steam returned no data for appid={appid}")
        data = wrapper.get("data", {})

        price_cents = None
        is_free = bool(data.get("is_free"))
        if not is_free and "price_overview" in data:
            price_cents = data["price_overview"].get("final")

        summary = reviews_resp.get("query_summary", {}) or {}
        review_count = summary.get("total_reviews")
        review_score_pct = None
        if review_count and review_count > 0:
            pos = summary.get("total_positive", 0)
            review_score_pct = round(100.0 * pos / review_count, 2)

        release_date = (data.get("release_date") or {}).get("date")
        coming_soon = bool((data.get("release_date") or {}).get("coming_soon"))

        genres = [g.get("description", "") for g in (data.get("genres") or [])]
        genres = [g for g in genres if g]

        return PageStats(
            appid=appid,
            name=data.get("name", ""),
            is_free=is_free,
            price_cents=price_cents,
            review_count_total=review_count,
            review_score_pct=review_score_pct,
            release_date=release_date,
            coming_soon=coming_soon,
            genres=genres,
            developer=(data.get("developers") or [None])[0],
            publisher=(data.get("publishers") or [None])[0],
            raw=data,
        )


async def fetch_page_stats(appid: int, **kwargs) -> PageStats:
    """One-shot convenience: fetch stats for a single appid + close the client."""
    async with SteamPageStatsClient(**kwargs) as c:
        return await c.fetch(appid)
