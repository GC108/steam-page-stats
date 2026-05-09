"""steam-page-stats — fetch Steam page stats + Boxleiter sanity-check.

The honest version of the rule of thumb: a heuristic with documented limits.
"""
from steam_page_stats.boxleiter import (
    BoxleiterResult,
    boxleiter_estimate,
    boxleiter_per_review,
)
from steam_page_stats.client import (
    PageStats,
    SteamPageStatsClient,
    fetch_page_stats,
)

__version__ = "0.1.1"
__all__ = [
    "BoxleiterResult",
    "PageStats",
    "SteamPageStatsClient",
    "boxleiter_estimate",
    "boxleiter_per_review",
    "fetch_page_stats",
]
