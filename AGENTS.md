# AGENTS.md

## Status: Active Implementation (Milestone 1 Core Pipeline & Data Deliverable Generators)

This repository contains the working implementation for the VYOMA AI Agent safety reasoning pipeline and dataset/deliverable generator test suites.

## Repository Layout

- `ai_agent/` — Core agent package
  - `orchestrator/orchestrator.py` — Top-level agent orchestration (`PERCEIVE` -> `UNDERSTAND` -> `PLAN` -> `RETRIEVE` -> `REASON` -> `VERIFY` -> `FINAL VERDICT` -> `LOG`)
  - `router/model_router.py` — Model routing for agent stages
  - `reasoning/reasoning_engine.py` — Deterministic reasoning engine
  - `rag/retriever.py` — Knowledge retriever
  - `tool_registry.py` — Controlled registry for tool permissions and execution
  - `verification.py` — Verification engine comparing deterministic rule verdicts against LLM reasoning
  - `audit.py` — In-memory audit event logger implementing shared `AuditLogger` contract
  - `fixtures/` — Fixture scenarios: `safe_case.json`, `conflict_case.json`, `ambiguous_case.json`, `disagreement_case.json`
- `shared/contracts.py` — Authoritative type contracts (`StructuredPTW`, `StructuredPID`, `RuleVerdict`, `LLMReasoningResult`, `VerificationResult`, `FinalVerdict`, `AuditEvent`, `AuditLogger`)
- `data-testing/` — Deliverable generators & dataset testing
  - `generators/`
    - `word_gen.py` — Safety review Word memo generator (`generate_word`)
    - `excel_gen.py` — Permit conflict matrix Excel generator (`generate_excel`)
    - `pdf_annotator.py` — PyMuPDF-based P&ID visual annotator (`annotate_pdf`)
  - `tests/`
    - `test_dataset_consistency.py` — Integration & consistency validation across sample dataset (PTWs, equipment, pipes, P&ID PDF, permit register, ground truth)
    - `test_word_gen.py` — Unit tests for Word generator
    - `test_excel_gen.py` — Unit tests for Excel generator
    - `test_pdf_annotator.py` — Unit tests for P&ID PDF annotator
- `sample-data/` — Plant dataset files (`ptws.json`, `equipment.json`, `pipes.json`, `permit-register.json`, `ground-truth.json`, `pid-unit-01.pdf`, `sops.json`)
- `tests/` — Core AI Agent test suites
  - `test_ai_agent.py` — Pipeline step, scenario, and safety invariant tests
  - `test_contracts.py` — Shared data contract compatibility & schema tests

## Running Tests

Run all tests via pytest:

```bash
python -m pytest
```

Or run via standard Python unittest:

```bash
python -m unittest discover -s tests -v
```
