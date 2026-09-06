# AGENTS.md

## Status: empty scaffold

This repository has **no commits yet** and **no working code**. Every tracked
source file is currently empty (0 bytes). There is no README, no manifest
(`pyproject.toml`, `package.json`, etc.), no lockfile, no build/test/lint config,
and no CI.

Do not assume any package, dependency, or command exists. Verify before relying
on anything; it almost certainly does not exist yet.

## Intended layout (from directory structure only)

- `ai_agent/` — the agent package
  - `orchestrator/` — top-level agent orchestration
  - `router/model_router.py` — model routing
  - `reasoning/reasoning_engine.py`
  - `rag/retriever.py` — retrieval
  - `tool_registry.py`
  - `verification.py`
  - `fixtures/*.json` — the four fixture cases (`safe`, `conflict`,
    `ambiguous`, `diagreement`) are all empty placeholders
- `shared/contracts.py` — shared data contracts/types

These names suggest the shape of the system, but none of it is implemented.
Work is greenfield: define contracts and behavior before building on assumptions.
