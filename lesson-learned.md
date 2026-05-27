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
