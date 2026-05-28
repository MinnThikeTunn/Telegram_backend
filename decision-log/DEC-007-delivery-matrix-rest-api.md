# DEC-007: Delivery Matrix REST API

## Status
**Accepted**

## Date
2026-05-28

## Context
We need a public, standardized endpoint to dynamically expose shipping rates and estimated transit timelines for Myanmar townships based on the shop's Latha location.

## Decision
Implement a new FastAPI router under `api/routes/delivery.py` providing `GET /api/v1/delivery-matrix` with pagination (`page`, `limit`) and partial matching (`search`) query parameters. The underlying business logic lives in `api/delivery_service.py` and uses a rule engine with an optional Google Gemini AI fallback for dynamic calculations of uncached townships. Results are serialized and cached in a JSON file `delivery_matrix_cache.json`.

## Consequences
- **Positive:** Standardizes shipping rates calculation under a unified backend API.
- **Positive:** Implements dynamic local cache matching which minimizes expensive model calculations.
- **Negative:** Gemini API call traffic can result in rate limit/quota exhaustion under free tier, requiring resilient fallback calculations.

## Implementation Notes
- Created `api/routes/delivery.py` and registered the endpoint in `main.py`.
- Implemented core logistics and AI routing in `api/delivery_service.py`.
- Formulated the persistent caching schema in `delivery_matrix_cache.json`.
