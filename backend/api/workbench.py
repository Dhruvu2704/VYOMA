"""Read-only workbench status endpoint.

Purely introspective: reports the orchestrator pipeline stage names, the
configured reasoning provider, the *live* local-Ollama model list, and the
registered tool / deliverable-generator surface.

No fabrication: the model list probe lives in ``ai_agent`` (the only layer
allowed to talk to local Ollama — the backend stays zero-egress) and reports
``unreachable`` when the instance does not answer. Nothing here creates state,
writes DB rows, or changes auth requirements.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from ai_agent.config import OllamaConfig, load_ollama_config
from ai_agent.orchestrator.orchestrator import AgentOrchestrator
from ai_agent.router.model_router import ModelRouter, build_local_model_router
from ai_agent.router.ollama_provider import list_local_models
from ai_agent.tool_registry import CONCEPTUAL_TOOL_NAMES

router = APIRouter(prefix="/api/workbench", tags=["Workbench"])

# Static capability surface (word/excel/pdf/audit) with one-line purposes.
DELIVERABLE_GENERATORS: List[Dict[str, str]] = [
    {
        "name": "word",
        "file_type": "WORD_MEMO",
        "purpose": "Generates a Word (.docx) safety review memo from the final verdict.",
    },
    {
        "name": "excel",
        "file_type": "EXCEL_CONFLICT_MATRIX",
        "purpose": "Generates an Excel (.xlsx) matrix of the trigger rules and conflicting permits.",
    },
    {
        "name": "pdf",
        "file_type": "ANNOTATED_PDF",
        "purpose": "Annotates the original P&ID drawing (PDF) highlighting equipment and isolation tags.",
    },
    {
        "name": "audit",
        "file_type": "AUDIT_CHAIN",
        "purpose": "Persists every processing stage into a tamper-evident SHA-256 hash-chained ledger.",
    },
]


@router.get("/status")
def workbench_status() -> Dict[str, Any]:
    config: OllamaConfig = load_ollama_config()
    ollama = list_local_models(config)

    # Same factory the request path executes (fixture_run -> build_provider_orchestrator
    # -> build_local_model_router): reflects the real registered provider mapping.
    model_router: ModelRouter = build_local_model_router(config=config)
    routing = []
    for entry in model_router.list_capabilities():
        capability = entry["capability"]
        provider = entry["provider"]
        if provider is not None:
            logic = (
                f"select_provider('{capability}') returns the first registered provider "
                f"(registration order) whose capabilities include '{capability}': "
                f"{provider}."
            )
        else:
            logic = (
                f"No registered provider advertises '{capability}'; "
                f"select_provider('{capability}') raises ModelRouterError, so routing "
                f"to this capability is unavailable."
            )
        routing.append({"capability": capability, "provider": provider, "logic": logic})

    return {
        "application": {"name": "VYOMA", "components": ["KAVACH"]},
        "orchestrator": {
            "stages": list(AgentOrchestrator.PIPELINE_STAGES),
            "reasoning_provider": f"ollama:{config.model}",
            "provider_base_url": config.base_url,
            "provider_timeout_s": config.timeout,
        },
        "router": {
            "categories": list(model_router.capabilities()),
            "registered_providers": list(model_router.registered_providers()),
            "routing": routing,
        },
        "ollama": {
            "status": ollama["status"],
            "base_url": config.base_url,
            "model_count": len(ollama["models"]),
            "models": ollama["models"],
            "detail": ollama["detail"],
        },
        "tools": {
            "registered": sorted(CONCEPTUAL_TOOL_NAMES),
            "deliverable_generators": DELIVERABLE_GENERATORS,
        },
    }