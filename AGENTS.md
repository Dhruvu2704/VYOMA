# AGENTS.md

## Status: working local stack

The repo is now a working Python (backend + `ai_agent`) and Next.js (frontend)
project. See `DEMO.md` for the one-line demo startup.

- `scripts/start_demo.ps1` — brings up the full stack reproducibly from one
  command (kills stale port-8000/3000 listeners, ensures Ollama on 11434,
  runs `scripts/seed_demo_user.py`, starts backend + built frontend, polls
  until healthy). Re-runnable; prints URLs + demo credentials.
- `scripts/seed_demo_user.py` — idempotent seeder for the `officer`
  `SAFETY_OFFICER` demo account (fixed password `pass`, demo-only).
- Verification baseline: `python -B -m unittest discover -s tests -p "test_*.py"`
  = 525 tests; frontend `pnpm exec tsc --noEmit` and `pnpm build` are clean.
- Runtime artifacts (`vyoma.db`, `uploads/`, `outputs/`, `frontend/.next`) are
  gitignored — a fresh run creates them from the demo script.

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
