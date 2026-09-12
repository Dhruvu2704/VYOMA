# VYOMA + KAVACH demo runner

## One-line startup

From a PowerShell terminal in the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_demo.ps1
```

That one command: kills any stale listeners on ports 8000/3000, checks (and if
needed starts) local Ollama on `http://127.0.0.1:11434`, seeds the demo
account (idempotent), bootstraps the backend DB, and starts backend +
frontend as background processes, polling both until they answer. Re-run it at
any time — it is safe to run repeatedly.

Pre-reqs (already on this machine): Python 3.14 on PATH with uvicorn +
SQLAlchemy, pnpm 11, a frontend build. If the frontend was never built, run once:

```powershell
cd frontend; pnpm build; cd ..
```

## Demo login

- **Username:** `officer`
- **Password:** `pass` (fixed demo-only credential; not a security control)

UI accounts registered from the sign-in modal are plain `USER` accounts and
cannot start analyses — the seeded `officer` account is the one to demo with.

## Fixtures

- Conflict scenario: `ai_agent\fixtures\conflict_case.json`
- Safe scenario: `ai_agent\fixtures\safe_case.json`

On New Inspection, upload one of these JSON envelopes and click
**Start Safety Analysis**.

## Two things to expect during a live run

1. **One analysis takes ~2 minutes.** Rule validation and knowledge retrieval
   are fast; the local Ollama model (`llama3`) runs full reasoning on CPU, so
   expect roughly 2 min per inspection (a bit longer the first time, when the
   model is cold-loaded).
2. **The progress bar plateaus at ~45% during that phase.** The page keeps
   showing live activity (animated ring, running clock, blinking cursor, live
   log), but the numeric percent holds until the LLM stage finishes, then
   jumps to 100. That is expected display behavior, not a hang.