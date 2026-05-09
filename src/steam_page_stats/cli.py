"""CLI entry point: `steam-page-stats <appid>`.

Examples:
    steam-page-stats 1145360                    # Hades
    steam-page-stats 1145360 --json             # machine-readable output
    steam-page-stats 1145360 --no-boxleiter     # just the page stats
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional

from steam_page_stats.boxleiter import boxleiter_estimate
from steam_page_stats.client import fetch_page_stats


def _format_revenue(cents: int) -> str:
    d = cents / 100
    if d >= 1_000_000:
        return f"${d / 1_000_000:.1f}M"
    if d >= 1_000:
        return f"${d / 1_000:.0f}K"
    return f"${d:,.0f}"


async def _async_main(args) -> int:
    try:
        stats = await fetch_page_stats(
            args.appid, throttle_s=args.throttle, timeout=args.timeout
        )
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json:
        out = {
            "appid": stats.appid,
            "name": stats.name,
            "is_free": stats.is_free,
            "price_cents": stats.price_cents,
            "review_count_total": stats.review_count_total,
            "review_score_pct": stats.review_score_pct,
            "release_date": stats.release_date,
            "coming_soon": stats.coming_soon,
            "genres": stats.genres,
            "developer": stats.developer,
            "publisher": stats.publisher,
        }
        if not args.no_boxleiter and stats.review_count_total and stats.price_cents:
            est = boxleiter_estimate(stats.review_count_total, stats.price_cents)
            out["boxleiter"] = {
                "revenue_low_cents": est.revenue_low_cents,
                "revenue_median_cents": est.revenue_median_cents,
                "revenue_high_cents": est.revenue_high_cents,
            }
        print(json.dumps(out, indent=2))
        return 0

    # Human-readable
    price_str = (
        "free" if stats.is_free
        else f"${stats.price_cents / 100:.2f}" if stats.price_cents
        else "unknown"
    )
    rc = stats.review_count_total
    print(f"\n{stats.name}  (appid {stats.appid})")
    print(f"  developer: {stats.developer or '?'}")
    print(f"  publisher: {stats.publisher or '?'}")
    print(f"  genres: {', '.join(stats.genres) if stats.genres else '(none)'}")
    print(f"  released: {stats.release_date or 'unknown'}{' (coming soon)' if stats.coming_soon else ''}")
    print(f"  price: {price_str}")
    print(f"  reviews: {rc:,} total" if rc is not None else "  reviews: unknown")
    if stats.review_score_pct is not None:
        print(f"  review score: {stats.review_score_pct}%  positive")

    if args.no_boxleiter:
        return 0
    if not rc or not stats.price_cents:
        print("\nBoxleiter estimate: skipped (need a non-zero review count + paid price)")
        return 0

    est = boxleiter_estimate(rc, stats.price_cents)
    print("\nBoxleiter rule-of-thumb revenue estimate:")
    print(f"  low (×{est.multiplier_low}):     {_format_revenue(est.revenue_low_cents)}")
    print(f"  median (×{est.multiplier_median}): {_format_revenue(est.revenue_median_cents)}")
    print(f"  high (×{est.multiplier_high}):    {_format_revenue(est.revenue_high_cents)}")
    print()
    print("  ⚠  This is a heuristic with ~24% of games off by >30% per the formula's")
    print("     own author. For an empirically-validated P10–P90 cone with calibrated")
    print("     80% coverage per genre, see https://steamforecast.app")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="steam-page-stats",
        description="Fetch Steam page stats + Boxleiter sanity-check for an appid.",
    )
    p.add_argument("appid", type=int, help="Steam app ID (e.g. 1145360 for Hades)")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    p.add_argument(
        "--no-boxleiter", action="store_true",
        help="skip the Boxleiter revenue estimate; show only page stats",
    )
    p.add_argument(
        "--throttle", type=float, default=1.0,
        help="seconds between Steam API calls (default %(default)s)",
    )
    p.add_argument(
        "--timeout", type=float, default=15.0,
        help="HTTP timeout per request in seconds (default %(default)s)",
    )
    args = p.parse_args()

    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
