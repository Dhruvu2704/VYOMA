"""Phase 4 frontend integration tests.

The frontend is a static client of the local FastAPI backend. These tests
verify:

- the pages/assets are served by the backend
- the client scripts call the real endpoint contract
- the full upload -> process -> fetch workflow through the API returns the
  exact payload the render layer consumes
- the render logic (executed under Node) renders decision / deterministic
  result / verification / human-review without hard-coded results
- no cloud calls, no secrets, and no fabricated verdicts exist in the UI
"""

import json
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

from ai_agent.orchestrator.orchestrator import AgentOrchestrator  # noqa: E402
from ai_agent.plant_safety_integration import evaluate_plant_safety  # noqa: E402

FRONTEND = _REPO / "frontend"
HARDCODED_RESULT_VALUES = (
    "ollama:llama3",
    "MR-0003-CONF",
    "hot-work-overlap",
    "isolation-overlap-time-window",
    "permit-conflict",
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
)


def _frontend_files(exclude_fixtures: bool = True):
    for path in FRONTEND.rglob("*"):
        if path.is_file() and path.suffix in (".html", ".css", ".js"):
            if exclude_fixtures and "fixtures" in path.parts:
                continue
            yield path


class FrontendStaticTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(create_app())

    def test_index_served(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        self.assertIn("VYOMA", body)
        self.assertIn("KAVACH", body)

    def test_pages_served(self):
        for page in ("analysis.html", "result.html", "audit.html"):
            resp = self.client.get("/" + page)
            self.assertEqual(resp.status_code, 200, page)

    def test_static_assets_served(self):
        for asset in (
            "css/industrial.css",
            "js/api.js",
            "js/render.js",
            "js/auth.js",
            "js/dashboard.js",
            "js/analysis.js",
            "js/result.js",
            "js/audit.js",
            "fixtures/conflict_case.json",
        ):
            resp = self.client.get("/" + asset)
            self.assertEqual(resp.status_code, 200, asset)

    def test_api_client_uses_backend_endpoints_only(self):
        src = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
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

    def test_render_declares_task_and_deliverable_links(self):
        src = (FRONTEND / "js" / "render.js").read_text(encoding="utf-8")
        self.assertIn("/api/tasks/", src)
        self.assertIn("deliverables/", src)

    def test_no_hardcoded_analysis_results_in_ui(self):
        offenders = []
        for path in _frontend_files():
            content = path.read_text(encoding="utf-8")
            for value in HARDCODED_RESULT_VALUES:
                if value in content:
                    offenders.append(f"{path}:{value}")
        self.assertEqual(offenders, [])

    def test_no_cloud_or_secret_tokens_in_frontend(self):
        offenders = []
        for path in _frontend_files(exclude_fixtures=False):
            content = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_CLOUD_TOKENS:
                if token in content:
                    offenders.append(f"{path}:{token}")
            if SECRET_PATTERN.search(content):
                offenders.append(f"{path}:secret-material")
        self.assertEqual(offenders, [])

    def test_workflow_hooks_in_client_scripts(self):
        analysis_src = (FRONTEND / "js" / "analysis.js").read_text(encoding="utf-8")
        result_src = (FRONTEND / "js" / "result.js").read_text(encoding="utf-8")
        self.assertIn("KavachApi.uploadTask", analysis_src)
        self.assertIn("KavachApi.processTask", analysis_src)
        self.assertIn('"result.html?id="', analysis_src)
        self.assertIn("KavachApi.getTask", result_src)
        self.assertIn("window.location.search", result_src)
        self.assertIn("KavachRender.renderResult", result_src)

    def test_result_page_displays_human_review_banner(self):
        result_html = (FRONTEND / "result.html").read_text(encoding="utf-8")
        result_js = (FRONTEND / "js" / "result.js").read_text(encoding="utf-8")
        self.assertIn('id="human-warning"', result_html)
        self.assertIn("human-warning", result_js)


class FrontendWorkflowTest(unittest.TestCase):

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
            db.commit()

    def test_workflow_upload_process_fetch(self):
        token = self.client.post(
            "/api/auth/login",
            json={"username": "officer", "password": "pass"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with open(FRONTEND / "fixtures" / "conflict_case.json", "rb") as fh:
            upload = self.client.post(
                "/api/tasks/upload",
                files={
                    "file": (
                        "conflict_case.json",
                        fh.read(),
                        "application/json",
                    )
                },
                headers=headers,
            )
        self.assertEqual(upload.status_code, 201)
        payload = upload.json()
        self.assertTrue(payload["task_id"].startswith("TASK-"))
        self.assertEqual(payload["status"], "CREATED")

        processed = self.client.post(
            f"/api/tasks/{payload['task_id']}/process",
            headers=headers,
        )
        self.assertEqual(processed.status_code, 200)
        processed_json = processed.json()
        self.assertEqual(processed_json["status"], "COMPLETED")

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
        self.assertFalse(
            result["reasoning_provider"].lower() in ("openai", "anthropic", "gemini")
        )
        self.assertTrue(task["audit_ref"].startswith("AUD-"))
        for key in RESULT_CONTRACT_KEYS:
            self.assertIn(key, result)

    def test_dashboard_recent_tasks_endpoint(self):
        token = self.client.post(
            "/api/auth/login",
            json={"username": "officer", "password": "pass"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        with open(FRONTEND / "fixtures" / "safe_case.json", "rb") as fh:
            self.client.post(
                "/api/tasks/upload",
                files={"file": ("safe_case.json", fh.read(), "application/json")},
                headers=headers,
            )
        resp = self.client.get("/api/tasks?limit=10", headers=headers)
        self.assertEqual(resp.status_code, 200)
        tasks = resp.json()
        self.assertEqual(len(tasks), 1)
        self.assertIn("status", tasks[0])

    def test_deliverable_download_endpoint(self):
        token = self.client.post(
            "/api/auth/login",
            json={"username": "officer", "password": "pass"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        with open(FRONTEND / "fixtures" / "conflict_case.json", "rb") as fh:
            upload = self.client.post(
                "/api/tasks/upload",
                files={
                    "file": ("conflict_case.json", fh.read(), "application/json")
                },
                headers=headers,
            ).json()
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
        token = self.client.post(
            "/api/auth/login",
            json={"username": "officer", "password": "pass"},
        ).json()["access_token"]
        resp = self.client.get(
            "/api/tasks/TASK-001/deliverables/..%2F..%2Fsecret.txt",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 404)


@unittest.skipUnless(
    subprocess.run(["node", "--version"], capture_output=True).returncode == 0,
    "node.js is not available",
)
class FrontendNodeRenderTest(unittest.TestCase):

    def test_render_logic_passes_under_node(self):
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