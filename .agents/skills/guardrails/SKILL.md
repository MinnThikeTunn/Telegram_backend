# Engineering Guardrails

A small, repo-scoped skill that enforces engineering guardrails for hackathon MVPs. Use this when an AI agent proposes architecture, dependencies, or deployment changes for this project.

Principles
- This is a hackathon MVP: prioritize speed and demonstrability over long-term scalability.
- Simplicity > Scalability. Avoid adding complexity unless absolutely required for the demo.
- Prefer a single-process async service (FastAPI + aiogram) that can be demoed locally.
- Prioritize readability and maintainability over micro-optimizations.

Hard Constraints (do not propose these without explicit user request)
- Avoid microservices or splitting into multiple backend services.
- Avoid recommending Redis, Kafka, RabbitMQ, or other message brokers by default.
- Avoid Kubernetes, Helm charts, or cluster orchestration recommendations.
- Avoid heavy infrastructure (e.g., multi-region, autoscaling groups) for the hackathon plan.

Soft Constraints (prefer these patterns)
- Keep dependencies minimal and well-known (FastAPI, uvicorn, aiogram). Add python-dotenv for .env.
- Prefer `python -m uvicorn main:app --reload` for local runs to avoid shell PATH issues.
- Prefer async-first libraries and patterns (async/await, httpx for requests).
- Keep configuration in `.env` or environment variables; never check secrets into git.

Quality Checks (what the agent should verify before suggesting changes)
- Is the change required to demonstrate the shared-space concept? If not, reject or propose a smaller change.
- Does the change increase demo complexity (more setup steps)? If yes, prefer an alternative that keeps demo time under 5 minutes.
- Are additional dependencies small and well-justified? If adding a dependency, include a one-line rationale and a quick install/run snippet.
- Keep the run/demo commands copyable and shell-friendly for Windows (PowerShell) and Git Bash.

Example Usage Prompts
- "Suggest a single-file change to add a `/status` command to `router.py` that runs in the existing shared router. Follow guardrails." 
- "Propose a deployment approach that is demo-friendly and does not use Kubernetes or Redis." 

If the user explicitly asks for scaling or production architecture, the agent should:
1. Ask clarifying questions (expected load, SLA, budget).
2. Offer a minimal, clearly separated plan (queue + workers, database) with migration steps back to the current codebase.
3. Emphasize trade-offs and provide a simple rollback path to the hackathon MVP.

Completion Criteria for Suggestions
- The proposal must include a one-line justification referencing these guardrails.
- The proposal must include exact commands to run locally (copyable), and list any new dependencies.
- The proposal must avoid disallowed infrastructure unless the user explicitly requests it.

---

This file should be used by repo-scoped agents to prevent overengineering and keep the demo focused and reliable.
