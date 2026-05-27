# DEC-001: Multi-Tenant Telegram Bot Backend Architecture

## Status
**Accepted**

## Date
2026-05-27

## Context
For the hackathon, we need a fast and efficient way to deploy and manage multiple Telegram bots without spinning up separate server instances, listeners, or isolated codebases for each bot identity. Managing multiple polling scripts or separate web server instances per bot would be difficult to manage, deploy, and scale in a condensed timeline. 

## Decision
We decided to use a **single FastAPI instance** as a unified control tower to handle webhooks for all configured bots. 

- **Routing**: The FastAPI application uses a single dynamic route `POST /telegram/{bot_token}`. 
- **Processing**: The route validates the token against a loaded list (`BOT_TOKENS`), and uses `aiogram`'s `Update.model_validate` and `dp.feed_update` to inject the webhook payload into a shared Dispatcher and Router.
- **Bot Context**: An ephemeral `Bot` instance is initialized per request using an `async with Bot(token=bot_token)` context manager.

## Consequences
- **Positive**: Extremely fast to deploy; code reuse is 100% since all bots use the `shared_router`; minimal memory footprint.
- **Negative**: Hard coupling means logic strictly needs to remain bot-agnostic; one crash in the backend affects all bots simultaneously. 
- **Rule Synced**: `AGENTS.md` updated to enforce preserving the multi-tenant flow and strict webhook validation.
