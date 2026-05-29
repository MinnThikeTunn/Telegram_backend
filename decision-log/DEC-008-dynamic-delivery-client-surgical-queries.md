# DEC-008: Dynamic Delivery Client with Surgical Queries

## Status
**Accepted**

## Date
2026-05-28

## Context
The Telegram bot checkout and greeting logic requires real-time delivery zone pricing and transit timeline information from the dynamic Delivery Matrix REST API (`GET /api/v1/delivery-matrix`) rather than using static hardcoded township rules. However, loading the entire dynamic delivery matrix page-by-page every time the bot needs to verify a single township during checkout is bandwidth-heavy, raises API query count unnecessarily, and increases latency.

## Decision
Introduce a dynamic API client in `api/delivery_client.py` using `httpx.AsyncClient` with in-memory TTL caching. Additionally, implement a highly optimized `fetch_single_zone(township_name)` search function that targets the API with `search=<township_name>&limit=1`. Integrate this surgical lookup directly into the checkout rate and timeline confirmation phase inside `core_logic.py` while keeping full-list pagination caching for state/prompt updates. Include robust fallbacks that revert to static persona values or stale cache if the API goes offline.

## Consequences
- **Positive:** Prevents pulling unneeded data (such as hundreds of unrelated townships) during checkout confirmations, significantly speeding up response times.
- **Positive:** Lowers bandwidth and network query volume, and minimizes local server memory usage.
- **Positive:** Adds caching with custom TTL defaults, allowing easy control over traffic frequency to the dynamic matrix host.
- **Negative:** Adds external API dependencies during active checkouts, which requires resilient fallback routing (which is handled nicely by reverting to static values).

## Implementation Notes
- Created `api/delivery_client.py` containing `fetch_all_zones()`, `fetch_single_zone()`, and cache TTL configurations.
- Modified `core_logic.py` to use `fetch_single_zone()` during township confirmation callback.
- Modified `ai/ai_service.py` to fetch dynamic zones asynchronously with safety timeouts.
- Added comprehensive test coverage in `test_delivery_client.py` for dynamic cached lookups, single query operations, and failures.
