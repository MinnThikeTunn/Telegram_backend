# DEC-004: Bot-Specific Context Store (Redux-Style)

## Status
**Accepted**

## Date
2026-05-27

## Context
As the project scaled to handle multiple specific chatbots (e.g., Fashion bot vs. Digital Code bot), mapping personas and rules directly inside the `ai_service.py` became messy and coupled the AI logic too tightly to hardcoded bot configurations. We needed a clean way to isolate specific rules, few-shot examples, and dynamic states per bot.

## Decision
We implemented a centralized, Redux-style state registry named `BotStore` in a new file `bot_store.py`. 
- Each bot registers a `BotStateSlice` mapped to its `bot_token`.
- `ai_service.py` acts as a "reducer", pulling the target bot's state from the store and assembling the prompt (`Global Rules` + `Bot Specific Rules` + `Dynamic State`).

## Consequences
- **Positive:** Clear separation of concerns. `ai_service.py` is now strictly an AI processing engine, while `bot_store.py` acts as the global knowledge base for bot identities.
- **Negative:** Configurations are currently hardcoded in runtime memory. Future implementations may require hydrating this store from a database or JSON file.