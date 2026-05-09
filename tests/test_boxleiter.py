"""Tests for the Boxleiter heuristic."""
from __future__ import annotations

import pytest

from steam_page_stats.boxleiter import (
    BOXLEITER_HIGH,
    BOXLEITER_LOW,
    BOXLEITER_MEDIAN,
    boxleiter_estimate,
    boxleiter_per_review,
)


def test_basic_estimate():
    # 1000 reviews × $20 game
    est = boxleiter_estimate(review_count=1000, price_cents=2000)
    assert est.review_count == 1000
    assert est.price_cents == 2000
    assert est.revenue_low_cents == 1000 * BOXLEITER_LOW * 2000
    assert est.revenue_median_cents == 1000 * BOXLEITER_MEDIAN * 2000
    assert est.revenue_high_cents == 1000 * BOXLEITER_HIGH * 2000
    # Brackets are properly ordered
    assert est.revenue_low_cents < est.revenue_median_cents < est.revenue_high_cents


def test_zero_reviews():
    est = boxleiter_estimate(review_count=0, price_cents=2000)
    assert est.revenue_low_cents == 0
    assert est.revenue_median_cents == 0
    assert est.revenue_high_cents == 0


def test_free_game_returns_zero():
    est = boxleiter_estimate(review_count=10000, price_cents=0)
    assert est.revenue_median_cents == 0


def test_negative_reviews_rejected():
    with pytest.raises(ValueError):
        boxleiter_estimate(review_count=-1, price_cents=2000)


def test_negative_price_rejected():
    with pytest.raises(ValueError):
        boxleiter_estimate(review_count=1000, price_cents=-100)


def test_per_review():
    # $20 game at median multiplier = 50 × $20 = $1000 per review
    assert boxleiter_per_review(price_cents=2000) == 50 * 2000

    # Custom multiplier
    assert boxleiter_per_review(price_cents=2000, multiplier=42) == 42 * 2000


def test_dollar_helpers():
    # 100 reviews × $10 × median 50 = $50,000
    est = boxleiter_estimate(review_count=100, price_cents=1000)
    assert est.revenue_median_dollars == 5_000_000 / 100  # cents → dollars
    assert est.revenue_low_dollars == est.revenue_low_cents / 100
    assert est.revenue_high_dollars == est.revenue_high_cents / 100


def test_string_representation_contains_revenue_range():
    est = boxleiter_estimate(review_count=10000, price_cents=2000)
    s = str(est)
    assert "Boxleiter estimate" in s
    assert "reviews=10,000" in s
    assert "$20.00" in s
