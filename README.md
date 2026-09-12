# VYOMA + KAVACH

**VYOMA** is a sovereign, on-prem agentic AI workbench for confidential
industrial AI. **KAVACH** is its flagship application: automated
Permit-to-Work (PTW) conflict detection for industrial plants, combining
plant topology, deterministic safety rules, local AI reasoning, local RAG,
mandatory human review, and full auditability — with no cloud dependency.

Built for Smart India Hackathon 2026.

## Why it exists

Industrial permit-to-work approval is safety-critical and today largely
manual. KAVACH cross-checks a submitted permit against live plant topology
and deterministic safety rules, gets an independent second opinion from a
local LLM, and requires a human Safety Officer to review anything the two
don't agree on — before any permit can be approved. No permit is ever
auto-approved on a rule/model disagreement, and no AI call ever leaves the
local machine.

## Architecture

| Layer | Tech |
|---|---|
| Backend API | FastAPI, SQLAlchemy, SQLite, JWT auth + RBAC |
| Frontend | Next.js, React, Tailwind |
| AI Agent | Model-agnostic orchestrator, local Ollama inference, local RAG (BM25 over plain-text SOPs, no embeddings/vector DB) |
| Safety engine | Deterministic plant-topology + rule evaluation (`plant_safety/`) — independent of any LLM |
| OCR | Local Tesseract (`pytesseract`) for image → structured PTW extraction |
| Deliverables | Word (`python-docx`), Excel (`openpyxl`), PDF (`PyMuPDF`) |

```
Frontend (Next.js)
   │  upload PTW envelope / image
   ▼
Backend API (FastAPI)
   │  task creation & persistence (SQLite)
   ▼
KAVACH connector
   │
   ▼
AI Agent orchestrator  (ai_agent/)
   PERCEIVE → UNDERSTAND → PLAN → RETRIEVE → USE TOOL → REASON → VERIFY → ACT → LOG
   │              │                  │            │         │
   │              │                  │            │         └─ local Ollama model (independent reasoning)
   │              │                  │            └─ deterministic plant-safety rules (plant_safety/)
   │              │                  └─ local RAG over SOP knowledge base
   │              └─ rule-based task classification (no LLM)
   └─ agreement verification (rule vs. LLM) → final verdict → human review if required
   ▼
Audit hash-chain + execution trace + Word/Excel deliverables
```

See `ai_agent/README.md` for the AI agent module in detail.

## Getting started

Prerequisites: Python 3.14+, `pnpm`, and a local [Ollama](https://ollama.com)
install with a model pulled (default `llama3`).

```powershell
# One command brings up backend + frontend + Ollama check + demo seed data
powershell -ExecutionPolicy Bypass -File scripts\start_demo.ps1
```

If the frontend has never been built:

```powershell
cd frontend; pnpm build; cd ..
```

**Demo login:** username `officer`, password `pass` (fixed demo-only
credential — not a real security control). Accounts created from the sign-in
modal are plain `USER` accounts and cannot start analyses.

Full startup details, fixtures, and known runtime behavior (a live analysis
takes ~2 minutes on CPU while the local model reasons — the UI intentionally
holds at ~45% during that phase) are documented in `DEMO.md`.

## Running a scenario

Log in → **New Inspection** → upload one of the fixture envelopes below →
**Start Safety Analysis**:

| Fixture | Expected result |
|---|---|
| `ai_agent/fixtures/safe_case.json` | PASS, no human review |
| `ai_agent/fixtures/conflict_case.json` | FLAGGED_FOR_REVIEW, human review required |
| `ai_agent/fixtures/isolation_conflict_case.json` | FLAGGED_FOR_REVIEW |
| `ai_agent/fixtures/multiple_conflicts_case.json` | FLAGGED_FOR_REVIEW |
| `ai_agent/fixtures/unknown_tag_case.json` | FLAGGED_FOR_REVIEW |
| `ai_agent/fixtures/ambiguous_case.json` | FLAGGED_FOR_REVIEW |
| `ai_agent/fixtures/llm_rule_disagreement_case.json` | REVIEW_REQUIRED (rule/LLM disagreement) |
| `ai_agent/fixtures/invalid_input_case.json` | Fails before verdict, with a meaningful error |

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI app: routes (`api/`), auth/RBAC/DB config, task processing service, audit logger, egress monitor |
| `frontend/` | Next.js app: login, dashboard, New Inspection, processing view, review panel, annotated deliverable viewer, security/workbench pages |
| `ai_agent/` | The Role-1 agent: orchestrator, planner, task classifier, reasoning engines, model router + local Ollama provider, RAG/knowledge retriever, tool registry, deliverable generators, vision/OCR pipeline, fixtures |
| `plant_safety/` | Deterministic plant topology graph, tag resolution, and safety rule evaluation — independent of any LLM |
| `shared/` | Shared data contracts/types used across backend and agent |
| `scripts/` | `start_demo.ps1` (full-stack launcher), `seed_demo_user.py`, `make_synthetic_ptw_image.py` |
| `tests/` | 25 test modules covering backend integration, KAVACH scenarios, plant safety rules/topology, the local model provider, DB schema upgrades, OCR, deliverables, and the frontend integration surface |

## Testing

```bash
python -B -m unittest discover -s tests -p "test_*.py"
```

Frontend:

```bash
cd frontend
pnpm exec tsc --noEmit
pnpm build
```

## Design principles

- **No cloud AI.** The only model calls are to a local Ollama endpoint
  (`127.0.0.1` by default); nothing is ever sent to a remote inference API.
- **No silent approval.** A rule/LLM disagreement always escalates to human
  review — the model can never override the deterministic safety verdict.
- **No fabricated verdicts.** Invalid input or an unreachable local model
  fails the task with a real error; it never produces a fake PASS/FLAGGED.
- **Closed tool surface.** The agent's tool registry only resolves
  pre-registered tool names; document content can never register or invoke
  a tool.
- **Full auditability.** Every decision is written to a SHA-256 hash-chained
  audit log alongside the execution trace.

## Known limitations (current state, not aspirational)

- Full computer-vision extraction of P&ID topology from images is not
  implemented; the OCR path (Tesseract → `StructuredPTW`) produces a minimal
  `structured_pid`, not full visual topology understanding.
- The generated `ANNOTATED_PDF` deliverable exists as tested code
  (`ai_agent/deliverables/pdf_annotator.py`) but is not yet invoked by the
  live task-processing pipeline — no source P&ID PDF is provided in the
  current fixtures.
- `AGENTS.md` in this repo predates the current implementation and describes
  an earlier greenfield state; `DEMO.md` and this README reflect the current,
  working state.
