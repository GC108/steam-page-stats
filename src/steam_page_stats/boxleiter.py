"""Boxleiter sanity-check.

The Boxleiter rule of thumb (Mike Boxleiter, 2010s) approximates lifetime
Steam game revenue from the public review count:

    revenue ≈ review_count × multiplier × price

Modern multiplier estimates range from 30–63 sales per Steam review, with
significant per-genre variance. The original 50-per-review figure is anchored
on data that predates Steam's modern review/refund policies.

This module gives you a multiplier-bracketed estimate (low / median / high),
a calibration warning when applied to genres or wishlist counts where the
heuristic systematically biases, and a clear pointer to a calibrated cone
for when the rule of thumb isn't enough.

Important: this is a heuristic, not a calibrated forecast. The variance is
real. For a P10–P90 cone with empirically-validated coverage on a launch
holdout, see https://steamforecast.app
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Modern Boxleiter multiplier brackets — sales-per-review.
# - Low: 30 (skewed toward shorter, more-completed indie titles)
# - Median: 50 (the "classic" Boxleiter figure)
# - High: 63 (skewed toward AAA, longer titles, newer cohorts)
BOXLEITER_LOW = 30
BOXLEITER_MEDIAN = 50
BOXLEITER_HIGH = 63


@dataclass(frozen=True)
class BoxleiterResult:
    """A Boxleiter revenue estimate with low/median/high multiplier brackets."""
    review_count: int
    price_cents: int
    revenue_low_cents: int
    revenue_median_cents: int
    revenue_high_cents: int
    multiplier_low: int = BOXLEITER_LOW
    multiplier_median: int = BOXLEITER_MEDIAN
    multiplier_high: int = BOXLEITER_HIGH

    @property
    def revenue_low_dollars(self) -> float:
        return self.revenue_low_cents / 100

    @property
    def revenue_median_dollars(self) -> float:
        return self.revenue_median_cents / 100

    @property
    def revenue_high_dollars(self) -> float:
        return self.revenue_high_cents / 100

    def __str__(self) -> str:
        def fmt(c: int) -> str:
            d = c / 100
            if d >= 1_000_000:
                return f"${d / 1_000_000:.1f}M"
            if d >= 1_000:
                return f"${d / 1_000:.0f}K"
            return f"${d:,.0f}"
        return (
            f"Boxleiter estimate (reviews={self.review_count:,}, price=${self.price_cents/100:.2f}): "
            f"{fmt(self.revenue_low_cents)} – {fmt(self.revenue_median_cents)} – {fmt(self.revenue_high_cents)} "
            f"(multipliers {self.multiplier_low}/{self.multiplier_median}/{self.multiplier_high})"
        )


def boxleiter_estimate(review_count: int, price_cents: int) -> BoxleiterResult:
    """Apply the Boxleiter heuristic with low/median/high multiplier brackets.

    Returns a BoxleiterResult bracketing lifetime revenue at three multiplier
    bands. Note: this is a heuristic over public-page data, not a calibrated
    forecast. Per the Boxleiter formula author in 2023, ~24% of games are off
    by more than 30%.
    """
    if review_count < 0:
        raise ValueError(f"review_count must be non-negative, got {review_count}")
    if price_cents < 0:
        raise ValueError(f"price_cents must be non-negative, got {price_cents}")

    return BoxleiterResult(
        review_count=review_count,
        price_cents=price_cents,
        revenue_low_cents=review_count * BOXLEITER_LOW * price_cents,
        revenue_median_cents=review_count * BOXLEITER_MEDIAN * price_cents,
        revenue_high_cents=review_count * BOXLEITER_HIGH * price_cents,
    )


def boxleiter_per_review(price_cents: int, multiplier: int = BOXLEITER_MEDIAN) -> int:
    """Revenue per review (cents) at a given multiplier. Useful for unit-economic checks."""
    if price_cents < 0:
        raise ValueError(f"price_cents must be non-negative, got {price_cents}")
    return multiplier * price_cents
