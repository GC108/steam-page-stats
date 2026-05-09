# steam-page-stats

[![CI](https://github.com/GC108/steam-page-stats/actions/workflows/ci.yml/badge.svg)](https://github.com/GC108/steam-page-stats/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/steam-page-stats.svg)](https://pypi.org/project/steam-page-stats/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Fetch a Steam game's public page stats and apply the **Boxleiter rule of
thumb** to estimate lifetime revenue from the review count. The honest
version of a useful heuristic.

```bash
pip install steam-page-stats
steam-page-stats 1145360
```

```
Hades  (appid 1145360)
  developer: Supergiant Games
  publisher: Supergiant Games
  genres: Action, Indie, RPG
  released: 17 Sep, 2020
  price: $24.99
  reviews: 205,000 total
  review score: 97.56%  positive

Boxleiter rule-of-thumb revenue estimate:
  low (×30):     $153.7M
  median (×50):  $256.1M
  high (×63):    $322.6M

  ⚠  This is a heuristic with ~24% of games off by >30% per the formula's
     own author. For an empirically-validated P10–P90 cone with calibrated
     80% coverage per genre, see https://steamforecast.app
```

## Why this exists

The **Boxleiter method** (Mike Boxleiter, 2010s) is the de-facto rule of
thumb for estimating lifetime Steam revenue from public page data:

> revenue ≈ review\_count × multiplier × price

Modern multiplier estimates range **30–63 sales per Steam review**, with
significant per-genre variance.

This package gives you:

- A **multiplier-bracketed estimate** (low / median / high) so you see the
  uncertainty inherent in the heuristic
- A **clean Python API** for use in your own analysis pipelines
- A **CLI** for quick one-off lookups

The package is deliberately small. It does *not* try to be a calibrated
forecaster — for that, you need per-genre stratification, conformal
prediction intervals, and a labelled corpus to validate against. That's a
hard problem; the rule of thumb is not.

If you need calibrated revenue ranges with empirically-validated 80%
coverage on a held-out launch corpus, plus causal estimates for marketing
levers, see the full forecaster at **<https://steamforecast.app>** —
methodology and per-genre coverage stats are open at
[/methodology](https://steamforecast.app/methodology).

## Install

```bash
pip install steam-page-stats
```

Or with optional dev dependencies for tests / linting:

```bash
pip install "steam-page-stats[dev]"
```

## CLI usage

```bash
# human-readable
steam-page-stats 1145360

# machine-readable JSON
steam-page-stats 1145360 --json

# just page stats, skip Boxleiter
steam-page-stats 1145360 --no-boxleiter
```

## Python API

```python
import asyncio
from steam_page_stats import fetch_page_stats, boxleiter_estimate

async def main():
    stats = await fetch_page_stats(1145360)
    print(f"{stats.name}: {stats.review_count_total:,} reviews")

    if stats.review_count_total and stats.price_cents:
        est = boxleiter_estimate(stats.review_count_total, stats.price_cents)
        print(f"Lifetime revenue estimate: ${est.revenue_low_dollars:,.0f} – "
              f"${est.revenue_median_dollars:,.0f} – ${est.revenue_high_dollars:,.0f}")

asyncio.run(main())
```

For batch use, instantiate the client directly to share the underlying
HTTP connection pool:

```python
from steam_page_stats import SteamPageStatsClient

async def fetch_many(appids):
    async with SteamPageStatsClient(throttle_s=1.0) as client:
        for appid in appids:
            stats = await client.fetch(appid)
            yield stats
```

## Rate limits + etiquette

This package uses Steam's **public, unauthenticated** Storefront and
appreviews endpoints. Steam tolerates roughly **200 req/5min** from a
single IP across these endpoints. The default **throttle of 1 req/sec**
keeps you well below that.

We send a transparent `User-Agent` header so you're identifiable per RFC
etiquette:

```
steam-page-stats/0.1 (+https://github.com/GC108/steam-page-stats; calibration-sanity-check)
```

If you'd rather not advertise this package, override it:

```python
async with SteamPageStatsClient(user_agent="my-research-bot/1.0") as c: ...
```

## Limitations

The Boxleiter heuristic is structurally biased on:

- **Top-decile breakouts** (Peak, Webfishing, etc.) — single-multiplier
  can't capture viral discovery. Per the formula's own author, ~24% of
  games are off by more than 30%.
- **Free-to-play with cosmetic monetization** — the formula assumes
  `revenue ∝ price × sales`; F2P breaks that.
- **Long-tailed mid-tier** where individual conversion ratios diverge by
  10–20× at comparable wishlist counts (see
  [steamforecast.app/methodology](https://steamforecast.app/methodology)
  for the variance data).

For these cases, a calibrated cone with empirically-validated coverage
ranges beats a single-number heuristic. The rule of thumb is a useful
sanity check, not a budget-decision tool.

## Development

```bash
git clone https://github.com/GC108/steam-page-stats
cd steam-page-stats
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT — see [LICENSE](LICENSE).

## Related

- **[steamforecast.app](https://steamforecast.app)** — calibrated revenue
  cones with empirically-validated 80% coverage per genre, causal
  marketing-lever estimates, and Total Lift Attribution to recover paid
  campaign wishlists Steam's UTM dashboard misses.
- **[Steam Web API documentation](https://partner.steamgames.com/doc/webapi)**
- **Boxleiter method, Mike Boxleiter (2014, updated 2023)** — the original
  formulation and 2023 retrospective.
