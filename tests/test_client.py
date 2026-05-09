"""Tests for the Steam Storefront API client.

Uses respx to mock httpx calls; no live network requests.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from steam_page_stats.client import (
    REVIEWS_URL,
    STORE_URL,
    SteamPageStatsClient,
    fetch_page_stats,
)


HADES_APPID = 1145360
HADES_STORE_RESPONSE = {
    str(HADES_APPID): {
        "success": True,
        "data": {
            "name": "Hades",
            "is_free": False,
            "price_overview": {"final": 2499, "currency": "USD"},
            "release_date": {"coming_soon": False, "date": "17 Sep, 2020"},
            "genres": [
                {"id": "1", "description": "Action"},
                {"id": "23", "description": "Indie"},
                {"id": "3", "description": "RPG"},
            ],
            "developers": ["Supergiant Games"],
            "publishers": ["Supergiant Games"],
        },
    }
}
HADES_REVIEWS_RESPONSE = {
    "success": 1,
    "query_summary": {
        "num_reviews": 0,
        "review_score": 9,
        "review_score_desc": "Overwhelmingly Positive",
        "total_positive": 200_000,
        "total_negative": 5_000,
        "total_reviews": 205_000,
    },
}


@respx.mock
async def test_fetch_hades_basic():
    respx.get(STORE_URL).mock(return_value=httpx.Response(200, json=HADES_STORE_RESPONSE))
    respx.get(REVIEWS_URL.format(appid=HADES_APPID)).mock(
        return_value=httpx.Response(200, json=HADES_REVIEWS_RESPONSE)
    )

    stats = await fetch_page_stats(HADES_APPID, throttle_s=0)
    assert stats.appid == HADES_APPID
    assert stats.name == "Hades"
    assert stats.is_free is False
    assert stats.price_cents == 2499
    assert stats.review_count_total == 205_000
    # Score is positive/total_reviews
    assert stats.review_score_pct == round(100.0 * 200_000 / 205_000, 2)
    assert "Action" in stats.genres
    assert "Indie" in stats.genres
    assert stats.developer == "Supergiant Games"
    assert stats.publisher == "Supergiant Games"
    assert stats.coming_soon is False


@respx.mock
async def test_fetch_unsuccessful_appid_raises():
    """Steam returns success=false for invalid appids."""
    respx.get(STORE_URL).mock(
        return_value=httpx.Response(200, json={"99999999": {"success": False}})
    )
    respx.get(REVIEWS_URL.format(appid=99999999)).mock(
        return_value=httpx.Response(200, json={"success": 1, "query_summary": {}})
    )
    with pytest.raises(ValueError, match="no data for appid"):
        await fetch_page_stats(99999999, throttle_s=0)


@respx.mock
async def test_fetch_free_game_has_no_price():
    free_resp = {
        "440": {
            "success": True,
            "data": {
                "name": "Team Fortress 2",
                "is_free": True,
                "release_date": {"coming_soon": False, "date": "10 Oct, 2007"},
                "genres": [{"id": "1", "description": "Action"}],
                "developers": ["Valve"],
                "publishers": ["Valve"],
            },
        }
    }
    respx.get(STORE_URL).mock(return_value=httpx.Response(200, json=free_resp))
    respx.get(REVIEWS_URL.format(appid=440)).mock(
        return_value=httpx.Response(200, json={"query_summary": {"total_reviews": 1_000_000, "total_positive": 880_000}})
    )

    stats = await fetch_page_stats(440, throttle_s=0)
    assert stats.is_free is True
    assert stats.price_cents is None


@respx.mock
async def test_client_used_outside_context_manager_raises():
    c = SteamPageStatsClient(throttle_s=0)
    with pytest.raises(RuntimeError, match="async context manager"):
        await c.fetch(HADES_APPID)


@respx.mock
async def test_429_retries_then_succeeds():
    """First 429 retries; second 429 retries; third call succeeds."""
    route_store = respx.get(STORE_URL).mock(
        side_effect=[
            httpx.Response(429),
            httpx.Response(429),
            httpx.Response(200, json=HADES_STORE_RESPONSE),
        ]
    )
    respx.get(REVIEWS_URL.format(appid=HADES_APPID)).mock(
        return_value=httpx.Response(200, json=HADES_REVIEWS_RESPONSE)
    )

    stats = await fetch_page_stats(HADES_APPID, throttle_s=0)
    assert stats.name == "Hades"
    assert route_store.call_count == 3
