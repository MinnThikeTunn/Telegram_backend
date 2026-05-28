# DEC-006: Persona Factory Prompt Stacking for SME Bots

## Status
**Accepted**

## Date
2026-05-27

## Context
The bot backend originally stored a small number of hardcoded persona slices in `bot_store.py`, and `ai_service.py` assembled the full prompt directly from global rules, bot-specific rules, and dynamic state. That approach worked for a few bots, but it did not scale well when we wanted each SME to behave differently by category and by operational traits such as perishability, customization, transaction risk, and logistics type.

We also needed a way to keep the AI prompt structure consistent while avoiding runtime prompt bloat and inconsistent persona switching across unrelated product types.

## Decision
We will use a compile-time Persona Factory pattern driven by a JSON profile file and a prompt stack with four layers:

1. **General Prompt**: universal safety and behavior guardrails.
2. **Specific Prompt**: category-specific persona baseline.
3. **Specific Rules**: operational rules derived from the four axes.
4. **Few-Shot Examples**: example dialogs selected by category.

The factory compiles those layers into a `BotStateSlice` at startup, and `bot_store.py` registers the resulting state per `bot_token`. `ai_service.py` continues to assemble the final instruction using `GENERAL_BASE_RULES` plus the registered bot slice.

## Consequences
- **Positive:** Persona behavior becomes deterministic per bot, easier to extend, and much more maintainable than embedding category logic directly inside the chat flow.
- **Positive:** The system can support different SME operating models within the same broad category, instead of treating all products in a category as identical.
- **Positive:** Few-shot examples remain centralized and reusable, which improves consistency in tone and response format.
- **Negative:** This adds another configuration layer, so updates now require keeping the JSON profile, factory mappings, and bot store registration in sync.
- **Negative:** Some behavior is still prompt-driven rather than code-enforced, so prompt design quality remains important.

## Implementation Notes
- Added `personas_config.json` as the source of truth for bot persona profiles.
- Added `persona_factory.py` to compile the prompt stack from category and axis inputs.
- Updated `bot_store.py` to load and register compiled bot state slices at startup.
- The AI service now applies a quota cooldown when Gemini returns `ResourceExhausted`, and it uses a normalized model id configured through `GEMINI_MODEL_NAME`.
