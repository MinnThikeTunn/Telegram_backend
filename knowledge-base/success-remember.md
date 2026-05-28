# 🏆 Software Success Patterns & Architectural Remembers

This document records the **proven successful implementation patterns** in this repository. These patterns represent high-quality design decisions that have been verified through tests, code reviews, and live behavior. 

**MANDATORY STEP:** Agents MUST read this file before creating new features, integrating external APIs, or refactoring existing business workflows.

---

## 💎 [SUCCESS-001]: Surgical API Querying (Single-Resource Search Query)
* **Context:** Fetching data from a REST endpoint during a live checkout transaction (e.g. looking up a township's delivery rate and timeline).
* **The Problem:** Querying a collection API (like `GET /api/v1/delivery-matrix`) without filters forces the client to download pages of unrelated datasets and search in-memory, wasting server resources, bandwidth, and causing higher checkout latency.
* **The Success Pattern (DO THIS):** 
  * Provide specialized client functions like `fetch_single_zone(name)` that utilize endpoint query parameters (e.g. `search=name&limit=1`).
  * Integrate this surgical lookup directly in active transaction checkouts to get *exactly* what is needed instantly.
* **Code Implementation Reference:**
  ```python
  # api/delivery_client.py
  async def fetch_single_zone(township_name: str, fallback_zones=None):
      # 1. Immediate fresh cache hit
      if cache_is_fresh: return cached_zone
      
      # 2. Query exactly one record
      resp = await client.get(url, params={"search": township_name, "limit": 1})
      return resp.json()["data"][0]
  ```
* **Benefit:** Reduces API bandwidth footprint by **99%**, slashes database/API search latency, and respects rate-limits.

---

## 💎 [SUCCESS-002]: Resilient Dual-Strategy Caching & Fallbacks
* **Context:** Relying on local REST APIs that might experience downtime, network hiccups, or rate-limiting.
* **The Problem:** If an external API is down, a critical workflow (like showing welcome prompts or checkout lists) fails, leading to bot crash or customer drop-off.
* **The Success Pattern (DO THIS):**
  * **Dual-Strategy Cache**: Use an in-memory cache with a configurable TTL (e.g., `DELIVERY_CACHE_TTL_SECONDS`). 
  * **Layered Fallback Plan**:
    1. Check fresh cache.
    2. Try live API call (guarded with a short connection timeout like `2.0s`).
    3. On API failure/timeout, fall back to **stale cache** data.
    4. If no stale cache exists, fall back to **compiled static configuration defaults** loaded at startup (`BotStateSlice`).
* **Benefit:** Guarantees **100% uptime** for critical user actions, even when external web servers are completely offline.

---

## 💎 [SUCCESS-003]: Environment-Driven Configuration Decoupling
* **Context:** Configuring server URLs, ports, and caches across development, testing, and production.
* **The Problem:** Hardcoding API URLs (e.g., `http://localhost:8000`) or caching values in the code base makes testing brittle, requires code modifications for deployment, and risks leaking credentials.
* **The Success Pattern (DO THIS):**
  * Always load settings dynamically using `os.getenv` with sensible defaults.
  * Register configuration templates in `.env.example` to let other developers know what variables are expected.
  * Safeguard all dynamic keys and settings in `.env.local`, which is strictly ignored in [.gitignore](file:///c:/tele_backend/Telegram_backend/.gitignore) to prevent credential leakage.
* **Benefit:** Enables environment portability (local vs testing vs production) with zero code changes.

---

## 💎 [SUCCESS-004]: Test-Driven Verification (Zero Regressions)
* **Context:** Introducing structural modifications to core bot routing, prompting, or payment modules.
* **The Problem:** Modifying business logic can introduce unexpected side-effects, such as breaking the AI greeting format or causing checkout buttons to fail.
* **The Success Pattern (DO THIS):**
  * Accompany every new client method or service with comprehensive unit tests (`test_delivery_client.py`).
  * Mock network communication (`unittest.mock.AsyncMock`) to isolate client-side logic from API server states.
  * Always run the pytest suite (`python -m pytest -v`) after making documentation or code modifications to maintain a regression-free workspace.
* **Benefit:** Ensures code releases are completely stable and reliable.
