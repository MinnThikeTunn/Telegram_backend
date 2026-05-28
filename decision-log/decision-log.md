# Architectural Decision Log

This document serves as the quick-view index and workflow guide for all architectural and system records in this project. By keeping this closely tied to the codebase, decisions change alongside the code via Git.

## The Workflow

1. **Propose & Draft**: Before coding, create a new `DEC-00X-name.md` file (or add an entry here) with the status set to `Proposed`.
2. **Discuss & Refine**: Discuss the decision during the Pull Request phase to align on alternatives.
3. **Accept & Merge**: Once approved, change the status to `Accepted` and merge. It becomes a permanent historical marker.
4. **Sync System Instructions**: If the decision enforces a strict constraint, copy that rule into `AGENTS.md` or other system prompts/linting configurations.

> **The Golden Rule**: Never delete or overwrite an `Accepted` decision if requirements change later. Instead, create a new decision, mark it as `Accepted`, and update the old decision's status to `Superseded by DEC-XXX`.

---

## Quick-View Index

| ID | Date | Decision Summary | Status | Rule Synced |
| --- | --- | --- | --- | --- |
| **DEC-001** | 2026-05-27 | Multi-Tenant Telegram Bot Backend Architecture | `Accepted` | `AGENTS.md` |
| **DEC-002** | 2026-05-27 | Upgrade to newer Gemini 2.5 Flash model for AI Service (defaults to `gemini-2.5-flash-lite`) | `Accepted` | No |
| **DEC-003** | 2026-05-27 | Controller-Service Architecture for Multi-Platform Support | `Accepted` | No |
| **DEC-004** | 2026-05-27 | Centralized Redux-style Bot Context Store (`bot_store.py`) | `Accepted` | No |
| **DEC-005** | 2026-05-27 | User Analytics Store for Customer Profiling (`user_store.py`, `sales_brain_state.json`) | `Accepted` | Yes (`AGENTS.md`, `architecture.md`) |
| **DEC-006** | 2026-05-27 | Persona Factory Prompt Stacking for SME Bots | `Accepted` | No |

