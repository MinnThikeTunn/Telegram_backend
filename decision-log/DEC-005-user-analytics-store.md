# DEC-005: User Analytics Store (Sales Brain)

## Status
**Accepted**

## Date
2026-05-27

## Context
As the project evolved to support sales-oriented bot scenarios (e.g., product recommendations, order tracking), we needed a way to track user behavior, preferences, and order history across conversations. The existing `bot_store.py` handles bot-level configuration, but there's no mechanism to persist user-specific data (likes, dislikes, order history) across sessions.

## Decision
We implemented a **User Analytics Store** (`user_store.py`) that provides persistent, file-based storage for user profiles.

- **Storage**: JSON file (`sales_brain_state.json`) for simplicity and hackathon-friendly deployment
- **Data Model**: `UserProfile` dataclass with fields for `user_id`, `likes`, `dislikes`, `order_history`, and `predicted_interests`
- **Auto-save**: Profile changes automatically trigger a save to maintain state
- **Integration**: `core_logic.py` exposes hooks like `process_checkout()` that update the user store when orders complete

## Consequences
- **Positive**: Enables personalized AI responses based on user history; supports order tracking and preference learning
- **Negative**: JSON file storage has concurrency limitations; for production, consider Redis/PostgreSQL
- **Rule Synced**: Added to `AGENTS.md` and `product-design/architecture.md` documentation