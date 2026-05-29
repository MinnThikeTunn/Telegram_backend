"""
Async HTTP client for fetching delivery zone data from the Delivery Matrix API.

Provides a cached fetch_all_zones() coroutine that paginates through the
GET /api/v1/delivery-matrix endpoint and returns a normalised list of zones.

Cache TTL is configurable via DELIVERY_CACHE_TTL_SECONDS env var (default: 300s / 5 min).
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DELIVERY_API_BASE: str = os.getenv("DELIVERY_API_BASE", "http://localhost:8000")
CACHE_TTL: int = int(os.getenv("DELIVERY_CACHE_TTL_SECONDS", "300"))  # 5 minutes
_PAGE_SIZE: int = 100  # Fetch in bulk to minimise round-trips

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------
_cache: List[Dict[str, Any]] = []
_cache_timestamp: float = 0.0


async def fetch_all_zones(
    fallback_zones: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Fetch all delivery zones from the Delivery Matrix API with caching.

    Args:
        fallback_zones: Optional static zones to return if the API call fails.
                        Each dict should contain at minimum ``township_name``,
                        ``rate``, and ``estimated_transit_timeline`` keys.

    Returns:
        A list of zone dicts with keys:
        ``township_name``, ``region``, ``division``, ``rate``,
        ``estimated_transit_timeline``.
    """
    global _cache, _cache_timestamp

    # Return cached data if still fresh
    if _cache and (time.time() - _cache_timestamp) < CACHE_TTL:
        logger.debug("Returning %d cached delivery zones (age=%.0fs)", len(_cache), time.time() - _cache_timestamp)
        return _cache

    try:
        all_zones: List[Dict[str, Any]] = []
        page = 1

        # Use shorter timeout - fail fast if API is unreachable
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
            while True:
                url = f"{DELIVERY_API_BASE}/api/v1/delivery-matrix"
                resp = await client.get(url, params={"page": page, "limit": _PAGE_SIZE})
                resp.raise_for_status()

                payload = resp.json()
                data = payload.get("data", [])
                pagination = payload.get("pagination", {})

                all_zones.extend(data)

                if not pagination.get("has_next", False):
                    break
                page += 1

        _cache = all_zones
        _cache_timestamp = time.time()
        logger.info("Fetched %d delivery zones from API (%d pages)", len(all_zones), page)
        return _cache

    except Exception as exc:
        logger.warning(
            "Failed to fetch delivery zones from %s: %s. Returning fallback (%d zones).",
            DELIVERY_API_BASE,
            exc,
            len(fallback_zones) if fallback_zones else 0,
        )
        # Return fallback if provided, otherwise return whatever was previously cached (possibly empty)
        if fallback_zones:
            return fallback_zones
        if _cache:
            logger.info("Using stale cached zones (%d entries) as fallback.", len(_cache))
            return _cache
        return []



async def fetch_single_zone(
    township_name: str,
    fallback_zones: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch a single delivery zone by name from the Delivery Matrix API.

    Args:
        township_name: Name of the township to fetch.
        fallback_zones: Optional static zones to search if the API call fails.

    Returns:
        The zone dict if found, or None.
    """
    global _cache, _cache_timestamp

    # Check in active cache first to avoid network call entirely
    if _cache and (time.time() - _cache_timestamp) < CACHE_TTL:
        for zone in _cache:
            if zone.get("township_name") == township_name:
                return zone

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
            url = f"{DELIVERY_API_BASE}/api/v1/delivery-matrix"
            resp = await client.get(url, params={"search": township_name, "limit": 1})
            resp.raise_for_status()

            payload = resp.json()
            data = payload.get("data", [])
            if data:
                # Find exact match or use the first result if it contains it
                for z in data:
                    if z.get("township_name") == township_name:
                        return z
                return data[0]
    except Exception as exc:
        logger.warning(
            "Failed to fetch single zone '%s' from %s: %s. Searching fallback.",
            township_name,
            DELIVERY_API_BASE,
            exc,
        )

    # Fallback to cache or fallback_zones
    if fallback_zones:
        for z in fallback_zones:
            if z.get("township_name") == township_name:
                return z
    if _cache:
        for z in _cache:
            if z.get("township_name") == township_name:
                return z
    return None


def invalidate_cache() -> None:
    """Force the next call to ``fetch_all_zones`` to re-fetch from the API."""
    global _cache, _cache_timestamp
    _cache = []
    _cache_timestamp = 0.0
    logger.debug("Delivery zone cache invalidated.")
