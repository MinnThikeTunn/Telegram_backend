# 🤖 Agent Guardrails & Architectural Lessons

## [ISSUE-001]: Resource Leak in aiogram.Bot Instantiation
* **Context:** handling multiple Telegram bots in a single FastAPI application.
* **Anti-Pattern (DO NOT DO):** Instantiating `Bot(token=...)` without an explicit session or outside of an `async with` block for every request. This creates a new `AiohttpSession` that is never closed, leading to memory leaks and socket exhaustion.
* **The Error Triggered:** Gradual memory increase and potential application crash over time due to unclosed sessions.
* **The Correct Pattern (DO THIS):** Use the `async with Bot(token=token) as bot:` context manager for ephemeral bot instances in webhook handlers, or manage a shared session. Also, ensure any temporary bot instances created during startup (e.g., to set webhooks) have their sessions closed with `await bot.session.close()`.
* **Enforcement Rule:** Every time a `Bot` instance is created, it MUST be either within an `async with` block or followed by an explicit `session.close()` call.

---

## [ISSUE-002]: Deprecated FastAPI Startup Events
* **Context:** Performing initialization tasks like registering webhooks when the server starts.
* **Anti-Pattern (DO NOT DO):** Using the `@app.on_event("startup")` or `@app.on_event("shutdown")` decorators.
* **The Error Triggered:** Deprecation warnings and potential future incompatibility with FastAPI/Starlette.
* **The Correct Pattern (DO THIS):** Use the modern `lifespan` context manager with `FastAPI(lifespan=lifespan_handler)`.
* **Enforcement Rule:** Use `lifespan` for all startup and shutdown logic.

---

## [ISSUE-003]: Pollution of Repository with Build Artifacts
* **Context:** Running tests and compiling Python code.
* **Anti-Pattern (DO NOT DO):** Committing `__pycache__/` directories, `.pytest_cache/`, or log files (e.g., `server.log`) to the repository.
* **The Error Triggered:** Bloated repository, potential security risks from opaque binaries, and cross-platform issues.
* **The Correct Pattern (DO THIS):** Ensure a proper `.gitignore` is in place and always clean up build artifacts before submission.
* **Enforcement Rule:** NEVER include binary files or local logs in a patch or commit.

---

## [ISSUE-004]: Placeholder Token Handling
* **Context:** Bootstrapping the application with example tokens.
* **Anti-Pattern (DO NOT DO):** Allowing the application to attempt to register invalid placeholder tokens with Telegram API during startup.
* **The Error Triggered:** Application fails to start or logs errors when trying to connect to Telegram with "YOUR_FIRST_BOT_TOKEN_HERE".
* **The Correct Pattern (DO THIS):** Add logic to skip placeholder tokens (e.g., `if token.startswith("YOUR_"): continue`) in the startup/lifespan sequence.
* **Enforcement Rule:** Always include safety checks when iterating over configuration lists that might contain placeholder values.

---

## [ISSUE-005]: Google Generative AI SDK Function Calling & Proto Handling
* **Context:** Processing tool calls emitted by Gemini and returning the execution result using the `google-generativeai` SDK.
* **Anti-Pattern (DO NOT DO):** Checking for top-level `response.function_call` on `AsyncGenerateContentResponse`, or attempting to use `genai.types.Part.from_function_response(...)`. 
* **The Error Triggered:** `AttributeError` for missing `function_call` on response objects, and `AttributeError` stating module `google.generativeai.types` has no attribute `Part`.
* **The Correct Pattern (DO THIS):** 
  1. Access parts recursively via `response.candidates[0].content.parts` and use `getattr(part, "function_call", None)` to inspect emitted tools.
  2. To send function execution results back to the model, instantiate raw protobufs using `genai.protos.Part(function_response=genai.protos.FunctionResponse(name="tool_name", response={"key": "value"}))`.
* **Enforcement Rule:** Always use `genai.protos` types for constructing content parts or function responses manually, rather than relying on non-existent `genai.types.Part` mappings.

---

## [ISSUE-006]: Runtime Persona Switching Instead of Compile-Time Persona Factory
* **Context:** Managing multiple SME bot personas with category-specific behavior and operational traits.
* **Anti-Pattern (DO NOT DO):** Building category rules, axis logic, and few-shot selection ad hoc inside the chat handler or LLM prompt at request time.
* **The Error Triggered:** Prompt drift, inconsistent persona behavior across bots, and brittle branching logic that becomes hard to debug or extend.
* **The Correct Pattern (DO THIS):** Compile persona data at startup from `personas_config.json` using `persona_factory.py`, then register the resulting `BotStateSlice` in `bot_store.py`.
* **Enforcement Rule:** Keep persona selection deterministic and configuration-driven; runtime code should only read the compiled slice and assemble the final prompt.

---

## [ISSUE-007]: Gemini Model Identifier Drift
* **Context:** Switching or upgrading Gemini models during deployment and testing.
* **Anti-Pattern (DO NOT DO):** Hardcoding a loosely formatted model string or assuming the SDK will normalize it automatically.
* **The Error Triggered:** `InvalidArgument` errors such as unexpected model name formats.
* **The Correct Pattern (DO THIS):** Normalize the model id in one place and allow controlled overrides through `GEMINI_MODEL_NAME`.
* **Enforcement Rule:** Any new Gemini model target must be validated as a concrete, SDK-accepted model id before deployment.
