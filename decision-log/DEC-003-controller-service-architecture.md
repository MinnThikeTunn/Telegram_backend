# DEC-003: Controller-Service Architecture for Multi-Platform Support

## Status
**Accepted**

## Date
2026-05-27

## Context
Originally, the project strictly relied on `aiogram.Router` to process incoming webhooks, which effectively locked all business and AI logic to the Telegram platform. To reach a wider audience, we need to support additional platforms like Viber concurrently from the same backend without duplicating our core AI processing logic.

## Decision
We decided to adopt a **Controller-Service Architecture**:

- **Core Service (`core_logic.py`)**: All platform-agnostic business logic (e.g., generating start replies, connecting to the Gemini AI models) was extracted here.
- **Platform Controllers (`telegram_router.py` & FastAPI routes)**: The old `router.py` was removed. We now use platform-specific controllers (e.g., an `aiogram.Router` for Telegram, and a FastAPI route for Viber) as ingress layers. They interpret platform-specific webhooks, extract generic variables (`user_id`, `text`), pass them to `core_logic`, and handle sending the final unified response back to their respective networks.
- **Data Standardization**: Modified internal components like `ai_service.py` to accept string-based `user_id` types, accommodating networks (like Viber/Messenger) that use alphanumeric IDs rather than purely integer IDs like Telegram.

## Consequences
- **Positive**: Complete logic decoupling. Adding a new channel (e.g., Discord or Slack) only requires creating a new ingress controller without touching AI or database logic.
- **Negative**: Adds slight boilerplate for each new platform as payloads must be explicitly mapped to generic parameters before calling `core_logic.py`. We also lose out on aiogram's domain-specific FSM (Finite State Machine) natively applying to other platforms.
- **Rule Synced**: No strict prompt updates required yet.