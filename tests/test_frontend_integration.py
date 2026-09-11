"""Frontend integration tests for the recovered Next.js frontend.

The original v0.app Next.js frontend in ``frontend/`` is a client of the local
FastAPI backend. These tests verify:

- the API client contract in ``frontend/lib/api.ts`` targets the real backend
  endpoints and sends the JWT bearer token
- the result model in ``frontend/lib/result-model.ts`` only reshapes backend
  payloads and never hard-codes fixture outcomes
- no cloud service, secret, or fabricated verdict value exists in the Next
  source tree (app/components/lib)
- the vanilla Phase-4 static pages are gone (the backend root is the JSON
  heartbeat, the UI is served by Next itself)
- the full upload -> process -> fetch workflow through the API returns the
  exact payload the result model consumes (deterministic orchestrator)
- audit / deliverable endpoints behave with real permissions
- the result-model + API-client logic passes under Node (native TS stripping)
"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

_TEST_BASE = Path(tempfile.mkdtemp(prefix="vyoma_frontend_test_"))
_REPO = Path(__file__).resolve().parent.parent
os.environ["VYOMA_DB_URL"] = (
    "sqlite:///" + (_TEST_BASE / "test.db").as_posix().replace("\\", "/")
)
os.environ["VYOMA_UPLOAD_DIR"] = str(_TEST_BASE / "uploads")
os.environ["VYOMA_OUTPUT_DIR"] = str(_TEST_BASE / "outputs")
os.environ["VYOMA_FRONTEND_DIR"] = str(_REPO / "frontend")
os.environ.setdefault("VYOMA_SECRET_KEY", "test-secret-key-0123456789abcdef")

from fastapi.testclient import TestClient  # noqa: E402

from backend.db.database import Base, SessionLocal, engine  # noqa: E402
from backend.db.models import User  # noqa: E402
from backend.main import create_app  # noqa: E402
from backend.services.kavach import KavachConnector  # noqa: E402
from backend.services.password import hash_password  # noqa: E402

from ai_agent.config import load_ollama_config  # noqa: E402
from ai_agent.orchestrator.orchestrator import AgentOrchestrator  # noqa: E402
from ai_agent.plant_safety_integration import evaluate_plant_safety  # noqa: E402
from ai_agent.router.model_router import build_local_model_router  # noqa: E402

FRONTEND = _REPO / "frontend"
FIXTURES = _REPO / "ai_agent" / "fixtures"

# Outcome-specific values of the project fixtures. If any of these appear in
# frontend source the UI is hard-coding results instead of rendering the
# backend payload.
HARDCODED_RESULT_VALUES = (
    "ollama:llama3",
    "MR-0003-CONF",
    "hot-work-overlap",
    "isolation-overlap-time-window",
    "permit-conflict",
    "FLAGGED_FOR_REVIEW",
    "f0a4c61de8",
    "OFFICER-07",
    "audit-2026-0512",
    "task-2026-0512",
)
FORBIDDEN_CLOUD_TOKENS = (
    "openai",
    "anthropic",
    "gemini",
    "googleapis",
    "bedrock",
    "vertexai",
    "https://",
)
SECRET_PATTERN = re.compile(r"sk-(?:proj|ant)-[A-Za-z0-9]{8,}")

FABRICATED_EGRESS_CLAIM_TOKENS = (
    "securityStatus",
    "securityEvents",
    "externalConnections",
    "packetMonitoring",
    "0 external",
    "0 KB",
)

RESULT_CONTRACT_KEYS = (
    "final_decision",
    "rule_result",
    "rules_triggered",
    "conflicting_permit_ids",
    "reasoning_provider",
    "llm_result",
    "agreement",
    "requires_human_review",
    "explanation",
    "execution_trace",
)


def _source_files():
    """All Next.js source files that ship to the browser."""
    for root in ("app", "components", "lib"):
        base = FRONTEND / root
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".ts", ".tsx"):
                yield path
    for name in ("next.config.mjs",):
        path = FRONTEND / name
        if path.is_file():
            yield path


class FrontendSourceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(create_app())

    def test_api_client_uses_backend_endpoints_only(self):
        src = (FRONTEND / "lib" / "api.ts").read_text(encoding="utf-8")
        for endpoint in (
            "/api/health",
            "/api/auth/register",
            "/api/auth/login",
            "/api/tasks/upload",
            "/api/tasks?limit=",
            "/api/tasks/",
            "/process",
            "/api/audit/",
            "/api/audit/verify",
        ):
            self.assertIn(endpoint, src)
        self.assertIn("Authorization", src)
        self.assertIn("Bearer", src)

    def test_result_model_maps_backend_payload_shape(self):
        src = (FRONTEND / "lib" / "result-model.ts").read_text(encoding="utf-8")
        for key in (
            "task_id",
            "status",
            "permit_id",
            "scenario",
            "audit_ref",
            "rule_result",
            "rules_triggered",
            "conflicting_permit_ids",
            "llm_result",
            "reasoning_provider",
            "reasoning_explanation",
            "agreement",
            "final_decision",
            "requires_human_review",
            "execution_trace",
            "step.stage",
        ):
            self.assertIn(key, src)

    def test_no_hardcoded_analysis_results_in_ui(self):
        offenders = []
        for path in _source_files():
            content = path.read_text(encoding="utf-8")
            for value in HARDCODED_RESULT_VALUES:
                if value in content:
                    offenders.append(f"{path}:{value}")
        self.assertEqual(offenders, [])

    def test_no_fabricated_zero_egress_claims_in_ui(self):
        # Zero-egress must come from the live /api/workbench/security payload,
        # never from a static decorative scene or hardcoded label.
        offenders = []
        for path in _source_files():
            content = path.read_text(encoding="utf-8")
            for token in FABRICATED_EGRESS_CLAIM_TOKENS:
                if token in content:
                    offenders.append(f"{path}:{token}")
        self.assertEqual(offenders, [])

    def test_agent_execution_trace_renders_from_payload_only(self):
        # The verdict page must render the per-stage trace from the backend
        # execution_trace payload (step.stage), never from a hardcoded stage list.
        verdict = (FRONTEND / "app" / "verdict" / "page.tsx").read_text(encoding="utf-8")
        self.assertIn("v.executionTrace", verdict)
        self.assertIn("step.stage", verdict)
        hardcoded = ",".join(AgentOrchestrator.PIPELINE_STAGES)
        for path in _source_files():
            self.assertNotIn(
                hardcoded, path.read_text(encoding="utf-8"), msg=f"{path}"
            )

    def test_no_cloud_services_or_secrets_in_frontend(self):
        offenders = []
        for path in _source_files():
            content = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_CLOUD_TOKENS:
                if token in content:
                    offenders.append(f"{path}:{token}")
            if SECRET_PATTERN.search(content):
                offenders.append(f"{path}:secret-material")
        # Vercel analytics shipped no code once the layout stopped importing it.
        layout = (FRONTEND / "app" / "layout.tsx").read_text(encoding="utf-8")
        if "@vercel/analytics" in layout:
            offenders.append("app/layout.tsx:@vercel/analytics")
        self.assertEqual(offenders, [])

    def test_no_vanilla_phase4_static_files(self):
        for stale in (
            "index.html",
            "analysis.html",
            "result.html",
            "audit.html",
            "css/industrial.css",
            "js/api.js",
            "js/render.js",
            "fixtures/conflict_case.json",
        ):
            self.assertFalse(
                (FRONTEND / stale).exists(), f"vanilla static file still present: {stale}"
            )

    def test_backend_root_is_json_heartbeat_without_frontend_index(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("VYOMA", resp.text)
        self.assertFalse((FRONTEND / "index.html").exists())

    def test_next_config_has_no_external_rewrites(self):
        src = (FRONTEND / "next.config.mjs").read_text(encoding="utf-8")
        self.assertNotIn("https://", src)
        self.assertNotIn("rewrites", src)


class FrontendWorkflowTest(unittest.TestCase):
    """Workflow the frontend drives: auth -> upload -> process -> fetch,
    audit, deliverable downloads. Uses the deterministic orchestrator."""

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )
        self.app = create_app()
        self.app.state.kavach_connector = KavachConnector(execute=orchestrator.run)
        self.client = TestClient(self.app)
        with SessionLocal() as db:
            db.add(User(
                username="officer",
                password_hash=hash_password("pass"),
                role="SAFETY_OFFICER",
            ))
            db.add(User(
                username="worker",
                password_hash=hash_password("pass"),
                role="USER",
            ))
            db.commit()

    def _token(self, username: str = "officer") -> str:
        return self.client.post(
            "/api/auth/login",
            json={"username": username, "password": "pass"},
        ).json()["access_token"]

    def _upload(self, headers, name: str = "conflict_case.json"):
        with open(FIXTURES / name, "rb") as fh:
            return self.client.post(
                "/api/tasks/upload",
                files={"file": (name, fh.read(), "application/json")},
                headers=headers,
            )

    def test_workflow_upload_process_fetch(self):
        headers = {"Authorization": f"Bearer {self._token()}"}

        upload = self._upload(headers)
        self.assertEqual(upload.status_code, 201)
        payload = upload.json()
        self.assertTrue(payload["task_id"].startswith("TASK-"))
        self.assertEqual(payload["status"], "CREATED")

        processed = self.client.post(
            f"/api/tasks/{payload['task_id']}/process",
            headers=headers,
        )
        self.assertEqual(processed.status_code, 200)
        self.assertEqual(processed.json()["status"], "COMPLETED")

        fetched = self.client.get(
            f"/api/tasks/{payload['task_id']}",
            headers=headers,
        )
        self.assertEqual(fetched.status_code, 200)
        task = fetched.json()

        result = task["result"]
        self.assertEqual(result["rule_result"], "FLAGGED")
        self.assertEqual(result["final_decision"], "FLAGGED_FOR_REVIEW")
        self.assertEqual(result["agreement"], "AGREE")
        self.assertTrue(result["requires_human_review"])
        self.assertIn("permit-conflict", result["rules_triggered"])
        self.assertIn("hot-work-overlap", result["rules_triggered"])
        self.assertIn("MR-0003-CONF", result["conflicting_permit_ids"])
        self.assertIn(
            result["reasoning_provider"],
            ("DeterministicReasoningEngine", "ollama:llama3"),
        )
        self.assertTrue(task["audit_ref"].startswith("AUD-"))
        for key in RESULT_CONTRACT_KEYS:
            self.assertIn(key, result)
        # The persisted agent execution trace must reflect the real orchestrator
        # stage progression, never a fabricated placeholder list.
        trace = result["execution_trace"]
        self.assertEqual(
            [step["stage"] for step in trace],
            AgentOrchestrator.PIPELINE_STAGES,
        )
        for step in trace:
            self.assertEqual(sorted(step.keys()), ["stage", "status", "timestamp"])
            self.assertIn(step["status"], ("completed", "failed", "running"))
            self.assertTrue(step["timestamp"])

    def test_audit_feed_and_chain_after_processing(self):
        headers = {"Authorization": f"Bearer {self._token()}"}
        upload = self._upload(headers).json()
        self.client.post(
            f"/api/tasks/{upload['task_id']}/process",
            headers=headers,
        )
        feed = self.client.get("/api/audit/", headers=headers)
        self.assertEqual(feed.status_code, 200)
        self.assertGreaterEqual(len(feed.json()), 1)
        verify = self.client.get("/api/audit/verify", headers=headers)
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.json()["valid"])

    def test_standard_user_cannot_read_audit(self):
        headers = {"Authorization": f"Bearer {self._token('worker')}"}
        resp = self.client.get("/api/audit/", headers=headers)
        self.assertEqual(resp.status_code, 403)

    def test_dashboard_recent_tasks_endpoint(self):
        headers = {"Authorization": f"Bearer {self._token()}"}
        self._upload(headers, "safe_case.json")
        resp = self.client.get("/api/tasks?limit=10", headers=headers)
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 1)
        self.assertIn("status", tasks[0])

    def test_deliverable_download_endpoint(self):
        headers = {"Authorization": f"Bearer {self._token()}"}
        upload = self._upload(headers).json()
        self.client.post(
            f"/api/tasks/{upload['task_id']}/process",
            headers=headers,
        )
        deliv = self.client.get(
            f"/api/tasks/{upload['task_id']}/deliverables",
            headers=headers,
        ).json()
        self.assertGreaterEqual(len(deliv["deliverables"]), 1)
        item = deliv["deliverables"][0]
        download = self.client.get(
            f"/api/tasks/{upload['task_id']}/deliverables/{item['filename']}",
            headers=headers,
        )
        self.assertEqual(download.status_code, 200)
        self.assertGreater(len(download.content), 0)

    def test_deliverable_download_blocks_traversal(self):
        headers = {"Authorization": f"Bearer {self._token()}"}
        resp = self.client.get(
            "/api/tasks/TASK-001/deliverables/..%2F..%2Fsecret.txt",
            headers=headers,
        )
        self.assertEqual(resp.status_code, 404)


class WorkbenchStatusTest(unittest.TestCase):
    """Read-only workbench introspection endpoint (public, no auth)."""

    def setUp(self):
        self.client = TestClient(create_app())

    def test_workbench_status_reports_live_stack(self):
        resp = self.client.get("/api/workbench/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()

        self.assertEqual(body["application"]["name"], "VYOMA")
        self.assertIn("KAVACH", body["application"]["components"])

        self.assertEqual(
            body["orchestrator"]["stages"],
            AgentOrchestrator.PIPELINE_STAGES,
        )
        self.assertTrue(body["orchestrator"]["reasoning_provider"].startswith("ollama:"))

        self.assertIn(body["ollama"]["status"], ("online", "unreachable"))
        self.assertEqual(body["ollama"]["model_count"], len(body["ollama"]["models"]))

        self.assertIn("check_conflict", body["tools"]["registered"])
        generators = {g["name"] for g in body["tools"]["deliverable_generators"]}
        self.assertEqual(generators, {"word", "excel", "pdf", "audit"})
        types = {g["file_type"] for g in body["tools"]["deliverable_generators"]}
        self.assertIn("WORD_MEMO", types)
        self.assertIn("EXCEL_CONFLICT_MATRIX", types)
        self.assertIn("ANNOTATED_PDF", types)

    def test_workbench_status_graceful_when_ollama_unreachable(self):
        original = os.environ.get("VYOMA_OLLAMA_BASE_URL")
        os.environ["VYOMA_OLLAMA_BASE_URL"] = "http://127.0.0.1:1"
        try:
            resp = self.client.get("/api/workbench/status")
        finally:
            if original is None:
                os.environ.pop("VYOMA_OLLAMA_BASE_URL", None)
            else:
                os.environ["VYOMA_OLLAMA_BASE_URL"] = original

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["ollama"]["status"], "unreachable")
        self.assertEqual(body["ollama"]["models"], [])
        self.assertEqual(body["ollama"]["model_count"], 0)

    def test_workbench_security_reports_real_egress_evidence(self):
        resp = self.client.get("/api/workbench/security")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()

        self.assertIn("psutil", body["method"])
        self.assertEqual(
            body["external_connection_count"],
            len(body["external_connections"]),
        )
        self.assertEqual(
            body["local_connection_count"],
            len(body["local_connections"]),
        )
        # The granting property: no external destination observed since start.
        self.assertEqual(body["external_observed_since_start"], 0)
        self.assertIsInstance(body["interfaces"], list)
        for iface in body["interfaces"]:
            for addr in iface["addresses"]:
                self.assertNotIn(addr["family"], {"2", "10", "23", "-1"})
        self.assertIn("valid", body["audit_chain"])
        self.assertIn("sampled_at", body)
        for conn in body["external_connections"]:
            self.assertIsNotNone(conn["raddr"])
            ip = conn["raddr"]["ip"]
            self.assertNotEqual(ip.split(".")[0], "127")
            self.assertNotEqual(ip, "::1")

    def test_workbench_router_section_matches_model_router(self):
        resp = self.client.get("/api/workbench/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()

        config = load_ollama_config()
        reference = build_local_model_router(config=config)
        expected = {
            entry["capability"]: entry["provider"]
            for entry in reference.list_capabilities()
        }

        self.assertEqual(body["router"]["categories"], list(reference.capabilities()))
        self.assertEqual(
            body["router"]["registered_providers"],
            list(reference.registered_providers()),
        )
        got = {
            entry["capability"]: entry["provider"]
            for entry in body["router"]["routing"]
        }
        self.assertEqual(got, expected)

        reasoning = next(
            entry for entry in body["router"]["routing"]
            if entry["capability"] == "reasoning"
        )
        self.assertEqual(reasoning["provider"], "ollama:" + config.model)
        self.assertEqual(
            body["orchestrator"]["reasoning_provider"],
            f"ollama:{config.model}",
        )

    def test_workbench_router_unconfigured_capabilities_not_fabricated(self):
        resp = self.client.get("/api/workbench/status")
        body = resp.json()

        config = load_ollama_config()
        reference = build_local_model_router(config=config)
        served = {
            entry["capability"]: entry["provider"]
            for entry in reference.list_capabilities()
            if entry["provider"] is not None
        }

        # With only the local Ollama provider registered, "reasoning" is the
        # sole routed capability; nothing else may claim a serving model.
        self.assertEqual(served, {"reasoning": f"ollama:{config.model}"})

        registered = set(body["router"]["registered_providers"])
        for entry in body["router"]["routing"]:
            if entry["capability"] in served:
                self.assertEqual(entry["provider"], served[entry["capability"]])
                self.assertIn(entry["provider"], registered)
            else:
                self.assertIsNone(entry["provider"])
                self.assertIn("raises ModelRouterError", entry["logic"])


@unittest.skipUnless(
    subprocess.run(["node", "--version"], capture_output=True).returncode == 0,
    "node.js is not available",
)
class FrontendNodeRenderTest(unittest.TestCase):

    def test_result_model_passes_under_node(self):
        proc = subprocess.run(
            ["node", str(_REPO / "tests" / "js" / "render_test.mjs")],
            capture_output=True,
            text=True,
            cwd=_REPO,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("all assertions passed", proc.stdout)


if __name__ == "__main__":
    unittest.main()