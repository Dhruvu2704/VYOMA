"""Phase 3 backend integration tests.

Environment variables (VYOMA_DB_URL, VYOMA_UPLOAD_DIR, VYOMA_OUTPUT_DIR)
must be set before importing any backend module. This is done at module
level.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_TEST_BASE = Path(tempfile.mkdtemp(prefix="vyoma_backend_test_"))
os.environ["VYOMA_DB_URL"] = (
    "sqlite:///" + (_TEST_BASE / "test.db").as_posix().replace("\\", "/")
)
os.environ["VYOMA_UPLOAD_DIR"] = str(_TEST_BASE / "uploads")
os.environ["VYOMA_OUTPUT_DIR"] = str(_TEST_BASE / "outputs")
os.environ.setdefault("VYOMA_SECRET_KEY", "test-secret-key-0123456789abcdef")

from fastapi.testclient import TestClient  # noqa: E402

from backend.db.database import Base, SessionLocal, engine  # noqa: E402
from backend.db.models import AuditLog, Permit, User  # noqa: E402
from backend.main import create_app  # noqa: E402
from backend.services.audit_logger import AuditLogger  # noqa: E402
from backend.services.kavach import KavachConnector, DEFAULT_ENTRYPOINT  # noqa: E402
from backend.services.password import hash_password  # noqa: E402

from ai_agent.orchestrator.orchestrator import AgentOrchestrator  # noqa: E402
from ai_agent.plant_safety_integration import evaluate_plant_safety  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"
CLOUD_PROVIDERS = ("openai", "anthropic", "claude", "gpt", "bedrock")


def _load_fixture(name: str) -> Dict[str, Any]:
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


def _discard_overlap(envelope: Dict[str, Any]) -> Dict[str, Any]:
    envelope = dict(envelope)
    graph = dict(envelope.get("graph_facts") or {})
    graph.pop("overlap_check", None)
    envelope["graph_facts"] = graph
    return envelope


class RecordingConnector:

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.status_during_run: str | None = None
        self.orchestrator = AgentOrchestrator(
            plant_safety_evaluator=evaluate_plant_safety
        )

    def __call__(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(dict(envelope))
        with SessionLocal() as db:
            from backend.db.models import Task

            task = db.query(Task).order_by(Task.id.desc()).first()
            self.status_during_run = task.status if task else None
        return dict(self.orchestrator.run(dict(envelope)))

    def expected_decision(self, envelope: Dict[str, Any]) -> str:
        result = self.orchestrator.run(dict(envelope))
        return result.get("final_verdict", {}).get("final_decision", "")


def _failing_execute(_: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("connector failure")


def _blocking_execute(_: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_request": {"permit_id": "X"},
        "final_verdict": {"final_decision": "BLOCKED", "requires_human_review": True},
        "verification": {"agreement": "AGREE"},
        "audit": {"audit_ref": "AUD-BLOCKED"},
        "failed_stage": "reasoning",
        "errors": "blocked by test",
    }


class BackendIntegrationTest(unittest.TestCase):

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.app = create_app()
        self.recording = RecordingConnector()
        self.app.state.kavach_connector = KavachConnector(execute=self.recording)
        self.client = TestClient(self.app)

    def _seed_user(self, username: str, role: str) -> str:
        with SessionLocal() as db:
            db.add(User(username=username, password_hash=hash_password("pass"), role=role))
            db.commit()
        resp = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": "pass"},
        )
        return resp.json()["access_token"]

    def _upload(self, fixture: str, token: str) -> Dict[str, Any]:
        envelope = _load_fixture(fixture)
        return self.client.post(
            "/api/tasks/upload",
            files={
                "file": (
                    "envelope.json",
                    json.dumps(envelope).encode(),
                    "application/json",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()

    def _process(self, task_id: str, token: str) -> Dict[str, Any]:
        return self.client.post(
            f"/api/tasks/{task_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

    def _review(
        self,
        task_id: str,
        token: str,
        decision: str,
        reason: str,
    ) -> Any:
        return self.client.post(
            f"/api/tasks/{task_id}/review",
            json={"decision": decision, "reason": reason},
            headers={"Authorization": f"Bearer {token}"},
        )

    def _reviewable_task(self, token: str) -> Dict[str, Any]:
        body = self._upload("conflict_case.json", token)
        result = self._process(body["task_id"], token)
        self.assertTrue(result["result"]["requires_human_review"])
        return body

    def test_health_endpoint(self) -> None:
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_register_and_login(self) -> None:
        reg = self.client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "pw"},
        )
        self.assertEqual(reg.status_code, 200)
        self.assertEqual(reg.json()["role"], "USER")
        login = self.client.post(
            "/api/auth/login",
            json={"username": "newuser", "password": "pw"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access_token", login.json())

    def test_unauthorized_task_access_rejected(self) -> None:
        resp = self.client.get("/api/tasks/TASK-001")
        self.assertEqual(resp.status_code, 401)

    def test_upload_requires_auth(self) -> None:
        envelope = _load_fixture("conflict_case.json")
        resp = self.client.post(
            "/api/tasks/upload",
            files={
                "file": (
                    "e.json",
                    json.dumps(envelope).encode(),
                    "application/json",
                )
            },
        )
        self.assertEqual(resp.status_code, 401)

    def test_authorized_upload_creates_task(self) -> None:
        token = self._seed_user("u1", "USER")
        body = self._upload("conflict_case.json", token)
        self.assertEqual(body["status"], "CREATED")
        self.assertTrue(body["task_id"].startswith("TASK-"))

    def test_process_rejects_regular_user(self) -> None:
        token = self._seed_user("u2", "USER")
        body = self._upload("conflict_case.json", token)
        resp = self.client.post(
            f"/api/tasks/{body['task_id']}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_invalid_json_upload_rejected(self) -> None:
        token = self._seed_user("u3", "USER")
        resp = self.client.post(
            "/api/tasks/upload",
            files={"file": ("bad.json", b"not json", "application/json")},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_structured_ptw_rejected(self) -> None:
        token = self._seed_user("u4", "USER")
        bad = json.dumps({"task_request": {"permit_id": "X"}}).encode()
        resp = self.client.post(
            "/api/tasks/upload",
            files={"file": ("n.json", bad, "application/json")},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_task_transitions_processing_then_completed(self) -> None:
        token = self._seed_user("off1", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        result = self._process(body["task_id"], token)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertIsNotNone(result["result"])

    def test_kavach_orchestrator_invoked(self) -> None:
        token = self._seed_user("off2", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        self._process(body["task_id"], token)
        self.assertEqual(len(self.recording.calls), 1)
        envelope = self.recording.calls[0]
        self.assertIn("structured_ptw", envelope)
        self.assertIn("structured_pid", envelope)

    def test_verdict_flows_to_api(self) -> None:
        token = self._seed_user("off3", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        result = self._process(body["task_id"], token)
        r = result["result"]
        self.assertTrue(r["deterministic_safety_evaluated"])
        self.assertEqual(r["rule_result"], "FLAGGED")
        self.assertEqual(r["agreement"], "AGREE")
        self.assertEqual(r["final_decision"], "FLAGGED_FOR_REVIEW")
        self.assertTrue(r["requires_human_review"])
        self.assertIn("MR-0003-CONF", r["conflicting_permit_ids"])

    def test_audit_reference_reaches_api(self) -> None:
        token = self._seed_user("off4", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        result = self._process(body["task_id"], token)
        audit_ref = result["audit_ref"]
        self.assertTrue(audit_ref and audit_ref.startswith("AUD-"))
        audit_list = self.client.get(
            "/api/audit/",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        self.assertIn(audit_ref, [e["audit_ref"] for e in audit_list])

    def test_local_model_provider(self) -> None:
        token = self._seed_user("off5", "SAFETY_OFFICER")
        body = self._upload("safe_case.json", token)
        result = self._process(body["task_id"], token)
        provider = result["result"]["reasoning_provider"]
        self.assertNotIn(provider.lower(), CLOUD_PROVIDERS)

    def test_failed_task_reaches_failed(self) -> None:
        app = create_app()
        app.state.kavach_connector = KavachConnector(execute=_failing_execute)
        client = TestClient(app)
        with SessionLocal() as db:
            db.add(User(username="fail_user", password_hash=hash_password("p"), role="SAFETY_OFFICER"))
            db.commit()
        token = client.post(
            "/api/auth/login",
            json={"username": "fail_user", "password": "p"},
        ).json()["access_token"]
        body = client.post(
            "/api/tasks/upload",
            files={
                "file": (
                    "e.json",
                    json.dumps(_load_fixture("conflict_case.json")).encode(),
                    "application/json",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        resp = client.post(
            f"/api/tasks/{body['task_id']}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.json()["status"], "FAILED")
        self.assertIn("RuntimeError", resp.json()["error"])

    def test_blocked_pipeline_reaches_failed(self) -> None:
        app = create_app()
        app.state.kavach_connector = KavachConnector(execute=_blocking_execute)
        client = TestClient(app)
        with SessionLocal() as db:
            db.add(User(username="block_user", password_hash=hash_password("p"), role="SAFETY_OFFICER"))
            db.commit()
        token = client.post(
            "/api/auth/login",
            json={"username": "block_user", "password": "p"},
        ).json()["access_token"]
        body = client.post(
            "/api/tasks/upload",
            files={
                "file": (
                    "e.json",
                    json.dumps(_load_fixture("conflict_case.json")).encode(),
                    "application/json",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        resp = client.post(
            f"/api/tasks/{body['task_id']}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.json()["status"], "FAILED")
        self.assertIn("reasoning", resp.json()["error"])

    def test_ollama_unavailable_reaches_failed(self) -> None:
        # KAVACH scenario 9 end-to-end at the backend boundary: the DEFAULT
        # entrypoint (execute_fixture -> plant_safety=True) cannot reach the
        # reason provider, so the task is FAILED and never given a verdict.
        app = create_app()
        client = TestClient(app)
        with SessionLocal() as db:
            db.add(
                User(
                    username="ollama_off",
                    password_hash=hash_password("p"),
                    role="SAFETY_OFFICER",
                )
            )
            db.commit()
        token = client.post(
            "/api/auth/login",
            json={"username": "ollama_off", "password": "p"},
        ).json()["access_token"]
        body = client.post(
            "/api/tasks/upload",
            files={
                "file": (
                    "e.json",
                    json.dumps(_load_fixture("conflict_case.json")).encode(),
                    "application/json",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        prev_base = os.environ.pop("VYOMA_OLLAMA_BASE_URL", None)
        prev_timeout = os.environ.pop("VYOMA_OLLAMA_TIMEOUT", None)
        os.environ["VYOMA_OLLAMA_BASE_URL"] = "http://127.0.0.1:59977"
        os.environ["VYOMA_OLLAMA_TIMEOUT"] = "5"
        try:
            resp = client.post(
                f"/api/tasks/{body['task_id']}/process",
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            if prev_base is None:
                os.environ.pop("VYOMA_OLLAMA_BASE_URL", None)
            else:
                os.environ["VYOMA_OLLAMA_BASE_URL"] = prev_base
            if prev_timeout is None:
                os.environ.pop("VYOMA_OLLAMA_TIMEOUT", None)
            else:
                os.environ["VYOMA_OLLAMA_TIMEOUT"] = prev_timeout
        self.assertEqual(resp.json()["status"], "FAILED")
        self.assertIn("Ollama", resp.json()["error"])

    def test_active_permit_drives_overlap_evidence(self) -> None:
        token = self._seed_user("off6", "SAFETY_OFFICER")
        envelope = _discard_overlap(_load_fixture("conflict_case.json"))
        body = self.client.post(
            "/api/tasks/upload",
            files={
                "file": (
                    "e.json",
                    json.dumps(envelope).encode(),
                    "application/json",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        with SessionLocal() as db:
            db.add(Permit(
                permit_id="MR-0003-CONF",
                status="ACTIVE",
                plant="Unit-3",
                equipment="Solvent-Bay",
                valid_from=datetime(2026, 9, 6, 9, 0),
                valid_to=datetime(2026, 9, 6, 13, 0),
                issued_by=1,
            ))
            db.commit()
        result = self._process(body["task_id"], token)
        r = result["result"]
        self.assertEqual(r["rule_result"], "FLAGGED")
        self.assertIn("MR-0003-CONF", r["conflicting_permit_ids"])

    def test_conflict_fixture_reaches_flagged_for_review(self) -> None:
        token = self._seed_user("off7", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        result = self._process(body["task_id"], token)
        self.assertEqual(result["result"]["final_decision"], "FLAGGED_FOR_REVIEW")
        self.assertTrue(result["result"]["requires_human_review"])

    def test_safe_fixture_reaches_pass(self) -> None:
        token = self._seed_user("off8", "SAFETY_OFFICER")
        body = self._upload("safe_case.json", token)
        result = self._process(body["task_id"], token)
        self.assertEqual(result["result"]["final_decision"], "PASS")
        self.assertFalse(result["result"]["requires_human_review"])

    def test_safety_officer_review_recorded_and_final_unchanged(self) -> None:
        token = self._seed_user("rev1", "SAFETY_OFFICER")
        body = self._reviewable_task(token)
        processed = self.client.get(
            f"/api/tasks/{body['task_id']}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        self.assertEqual(
            processed["result"]["final_decision"], "FLAGGED_FOR_REVIEW"
        )

        resp = self._review(
            body["task_id"],
            token,
            "APPROVE",
            "Isolation confirmed on site; safe to proceed.",
        )
        self.assertEqual(resp.status_code, 200)
        reviewed = resp.json()
        self.assertEqual(reviewed["review_status"], "APPROVED")
        self.assertEqual(
            reviewed["review_reason"], "Isolation confirmed on site; safe to proceed."
        )
        self.assertIsNotNone(reviewed["reviewed_by"])
        self.assertIsNotNone(reviewed["reviewed_at"])
        with SessionLocal() as db:
            reviewer_id = (
                db.query(User).filter(User.username == "rev1").first().id
            )
        self.assertEqual(reviewed["reviewed_by"], reviewer_id)
        self.assertEqual(
            reviewed["result"]["final_decision"], "FLAGGED_FOR_REVIEW"
        )
        self.assertTrue(reviewed["result"]["requires_human_review"])

    def test_review_persists_across_db_session_reload(self) -> None:
        token = self._seed_user("rev2", "SAFETY_OFFICER")
        body = self._reviewable_task(token)

        resp = self._review(
            body["task_id"], token, "REJECT", "Missing gas test certificate."
        )
        self.assertEqual(resp.status_code, 200)

        fresh = self.client.get(
            f"/api/tasks/{body['task_id']}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        self.assertEqual(fresh["review_status"], "REJECTED")
        self.assertEqual(fresh["review_reason"], "Missing gas test certificate.")
        self.assertIsNotNone(fresh["reviewed_at"])
        self.assertEqual(
            fresh["result"]["final_decision"], "FLAGGED_FOR_REVIEW"
        )

    def test_user_role_cannot_review(self) -> None:
        officer = self._seed_user("rev_officer", "SAFETY_OFFICER")
        body = self._reviewable_task(officer)
        user = self._seed_user("rev3", "USER")
        resp = self._review(
            body["task_id"], user, "APPROVE", "Approving as a regular user."
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_reviewable_task_rejected(self) -> None:
        token = self._seed_user("rev4", "SAFETY_OFFICER")
        body = self._upload("safe_case.json", token)
        self._process(body["task_id"], token)
        resp = self._review(body["task_id"], token, "APPROVE", "OK to approve.")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not reviewable", resp.json()["detail"])

    def test_review_without_verdict_rejected(self) -> None:
        token = self._seed_user("rev5", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        resp = self._review(body["task_id"], token, "APPROVE", "Never processed.")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not reviewable", resp.json()["detail"])

    def test_already_reviewed_task_conflict(self) -> None:
        token = self._seed_user("rev6", "SAFETY_OFFICER")
        body = self._reviewable_task(token)
        first = self._review(body["task_id"], token, "APPROVE", "Looks good.")
        self.assertEqual(first.status_code, 200)
        second = self._review(
            body["task_id"], token, "REQUEST_CHANGES", "Changed my mind."
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("already reviewed", second.json()["detail"])

    def test_blank_reason_rejected(self) -> None:
        token = self._seed_user("rev7", "SAFETY_OFFICER")
        body = self._reviewable_task(token)
        resp = self._review(body["task_id"], token, "APPROVE", "   ")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("reason", resp.json()["detail"])
        missing = self.client.post(
            f"/api/tasks/{body['task_id']}/review",
            json={"decision": "APPROVE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(missing.status_code, 422)

    def test_invalid_decision_rejected(self) -> None:
        token = self._seed_user("rev8", "SAFETY_OFFICER")
        body = self._reviewable_task(token)
        resp = self._review(body["task_id"], token, "MAYBE", "Unsure.")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("decision", resp.json()["detail"])

    def test_review_event_in_audit_chain(self) -> None:
        token = self._seed_user("rev9", "SAFETY_OFFICER")
        body = self._reviewable_task(token)
        resp = self._review(
            body["task_id"], token, "REQUEST_CHANGES", "Redraw the isolation sketch."
        )
        self.assertEqual(resp.status_code, 200)

        with SessionLocal() as db:
            rows = (
                db.query(AuditLog)
                .filter(AuditLog.pipeline == "human_review")
                .all()
            )
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertTrue(row.audit_ref.startswith("REVIEW-"))
            self.assertEqual(row.permit_id, "MR-0002-CONF")
            self.assertIn("REQUEST_CHANGES", row.stages)
            self.assertIn("redraw the isolation sketch", row.stages.lower())
            self.assertEqual(row.sequence, f"review:{self._task_numeric(body)}")
            self.assertTrue(AuditLogger().verify_chain(db))

    @staticmethod
    def _task_numeric(body: Dict[str, Any]) -> int:
        return int(body["task_id"].replace("TASK-", ""))

    def test_audit_chain_verifiable_and_tamper_detected(self) -> None:
        token = self._seed_user("off9", "SAFETY_OFFICER")
        self._upload("safe_case.json", token)
        body2 = self._upload("conflict_case.json", token)
        self._process(body2["task_id"], token)
        verify = self.client.get(
            "/api/audit/verify",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        self.assertTrue(verify["valid"])

        with SessionLocal() as db:
            log = db.query(AuditLog).first()
            log.pipeline = log.pipeline + ",TAMPERED"
            db.commit()

        verify_tampered = self.client.get(
            "/api/audit/verify",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        self.assertFalse(verify_tampered["valid"])

    def test_deliverables_generated(self) -> None:
        token = self._seed_user("off10", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        self._process(body["task_id"], token)
        deliv = self.client.get(
            f"/api/tasks/{body['task_id']}/deliverables",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        self.assertGreaterEqual(len(deliv["deliverables"]), 1)
        item = deliv["deliverables"][0]
        self.assertTrue(Path(item["file_path"]).exists())
        self.assertTrue(item["sha256"])

    def test_no_external_network_or_cloud_ai_imports(self) -> None:
        import pathlib

        forbidden = ["requests", "httpx", "urllib", "socket", "http.client", "openai", "anthropic"]
        for path in pathlib.Path("backend").rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(
                    token,
                    content,
                    f"{path} references forbidden token '{token}'",
                )

    def test_architecture_delegates_to_orchestrator(self) -> None:
        default = KavachConnector()
        self.assertEqual(default.entrypoint, DEFAULT_ENTRYPOINT)
        self.assertEqual(
            DEFAULT_ENTRYPOINT,
            "ai_agent.orchestrator.fixture_run.execute_fixture",
        )
        import ai_agent.orchestrator.fixture_run as fr

        self.assertTrue(hasattr(fr, "execute_fixture"))

    def test_api_final_decision_matches_orchestrator(self) -> None:
        token = self._seed_user("off11", "SAFETY_OFFICER")
        body = self._upload("conflict_case.json", token)
        expected = self.recording.expected_decision(_load_fixture("conflict_case.json"))
        result = self._process(body["task_id"], token)
        self.assertEqual(result["result"]["final_decision"], expected)

    def test_invalid_task_id_rejected(self) -> None:
        token = self._seed_user("u5", "USER")
        resp = self.client.get(
            "/api/tasks/INVALID",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_task_returns_404(self) -> None:
        token = self._seed_user("u6", "USER")
        resp = self.client.get(
            "/api/tasks/TASK-999",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()