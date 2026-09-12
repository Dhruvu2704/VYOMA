import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/* Node test for the Next.js frontend `result-model` mapper and API client.
 *
 * run with: node tests/js/render_test.mjs
 * Executed from tests/test_frontend_integration.py as a subprocess.
 * Requires Node >= 23.6 (native TypeScript type stripping).
 */

const resultModel = await import("../../frontend/lib/result-model.ts");
const { buildVerdictModel } = resultModel;

// The frontend must never hard-code the outcome values of the project
// fixtures; they must arrive from the backend payload at runtime.
const HARDCODED_OUTCOME_VALUES = [
  "MR-0003-CONF",
  "ollama:llama3",
  "hot-work-overlap",
  "isolation-overlap-time-window",
  "permit-conflict",
  "FLAGGED_FOR_REVIEW",
];
{
    const src = readFileSync(new URL("../../frontend/lib/result-model.ts", import.meta.url), "utf8");
    for (const value of HARDCODED_OUTCOME_VALUES) {
        assert.ok(
            !src.includes(value),
            `result-model.ts must not hard-code "${value}"`
        );
    }
}

const apiSrc = readFileSync(new URL("../../frontend/lib/api.ts", import.meta.url), "utf8");
{
    for (const endpoint of [
        "/api/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/tasks/upload",
        "/api/tasks?limit=",
        "/api/tasks/",
        "/process",
        "/api/audit/",
        "/api/audit/verify",
    ]) {
        assert.ok(apiSrc.includes(endpoint), `api.ts must reference ${endpoint}`);
    }
    assert.ok(apiSrc.includes("Authorization") && apiSrc.includes("Bearer"), "api.ts must send the JWT bearer header");
}

const CONFLICT_TASK = {
    task_id: "TASK-001",
    status: "COMPLETED",
    filename: "conflict_case.json",
    permit_id: "MR-0002-CONF",
    scenario: "conflict",
    audit_ref: "AUD-1234567890AB",
    error: null,
    created_at: "2026-09-11T08:00:00Z",
    updated_at: "2026-09-11T08:00:12Z",
    result: {
        deterministic_safety_evaluated: true,
        rule_result: "FLAGGED",
        rules_triggered: [
            "permit-conflict",
            "hot-work-overlap",
            "isolation-overlap-time-window",
        ],
        conflicting_permit_ids: ["MR-0003-CONF"],
        rule_explanation: "Hot work overlaps an active isolation.",
        llm_result: "FLAGGED",
        reasoning_provider: "ollama:llama3",
        reasoning_explanation: "Local model agrees.",
        agreement: "AGREE",
        final_decision: "FLAGGED_FOR_REVIEW",
        requires_human_review: true,
        explanation: "Permit conflict found; operator review required.",
        generated_at: "2026-09-11T08:00:12Z",
    },
    deliverables: [
        {
            filename: "memo_TASK-001.docx",
            file_type: "docx",
            file_path: "outputs/task-001/memo_TASK-001.docx",
            sha256: "abc123",
        },
    ],
};

const SAFE_TASK = {
    ...CONFLICT_TASK,
    task_id: "TASK-002",
    permit_id: "MR-0001-SAFE",
    scenario: "safe",
    audit_ref: "AUD-000000000001",
    result: {
        ...CONFLICT_TASK.result,
        rule_result: "PASS",
        rules_triggered: [],
        conflicting_permit_ids: [],
        llm_result: "PASS",
        reasoning_provider: "DeterministicReasoningEngine",
        reasoning_explanation: "All constraints satisfied.",
        agreement: "AGREE",
        final_decision: "PASS",
        requires_human_review: false,
    },
};

const UNAVAILABLE_TASK = {
    ...CONFLICT_TASK,
    task_id: "TASK-003",
    status: "COMPLETED",
    result: {
        ...CONFLICT_TASK.result,
        rule_result: "PASS",
        rules_triggered: [],
        conflicting_permit_ids: [],
        llm_result: "UNAVAILABLE",
        reasoning_provider: null,
        reasoning_explanation: "",
        agreement: "UNAVAILABLE",
        final_decision: "REVIEW_REQUIRED",
        requires_human_review: true,
    },
};

const FAILED_TASK = {
    task_id: "TASK-004",
    status: "FAILED",
    filename: "bad.json",
    permit_id: "MR-0000-UNKNOWN",
    scenario: "unknown",
    audit_ref: null,
    error: "RuntimeError: connector failure",
    result: null,
    deliverables: [],
};

// ---- conflict model extraction ---------------------------------------------
{
    const m = buildVerdictModel(CONFLICT_TASK);
    assert.equal(m.finalDecision, "FLAGGED_FOR_REVIEW");
    assert.equal(m.ruleResult, "FLAGGED");
    assert.equal(m.permitId, "MR-0002-CONF");
    assert.equal(m.taskId, "TASK-001");
    assert.equal(m.auditRef, "AUD-1234567890AB");
    assert.ok(
        m.ruleChecks.some((c) => c.includes("permit-conflict")),
        "rule checks must surface triggered constraints"
    );
    assert.equal(m.ruleIssues.length, 1);
    assert.ok(m.ruleIssues[0].title.includes("MR-0003-CONF"));
    assert.equal(m.reasoningProvider, "ollama:llama3");
    assert.equal(m.llmResult, "FLAGGED");
    assert.equal(m.agreement, "AGREE");
    assert.equal(m.requiresHumanReview, true);
    assert.equal(m.deterministicEvaluated, true);
    assert.ok(m.llmReasoning.length > 0);
    assert.equal(m.explanation, "Permit conflict found; operator review required.");
}

// ---- PASS model (no human review) ------------------------------------------
{
    const m = buildVerdictModel(SAFE_TASK);
    assert.equal(m.finalDecision, "PASS");
    assert.equal(m.ruleResult, "PASS");
    assert.equal(m.requiresHumanReview, false);
    assert.ok(m.ruleChecks.includes("All evaluated safety constraints were satisfied."));
}

// ---- LLM unavailable: deterministic result must stand ----------------------
{
    const m = buildVerdictModel(UNAVAILABLE_TASK);
    assert.equal(m.llmResult, "UNAVAILABLE");
    assert.equal(m.agreement, "UNAVAILABLE");
    assert.equal(m.reasoningProvider, null);
    assert.ok(m.llmReasoning.includes("not reachable"), "must explain missing AI verdict");
    assert.equal(m.requiresHumanReview, true);
}

// ---- failed task: no fabricated verdict ------------------------------------
{
    const m = buildVerdictModel(FAILED_TASK);
    assert.equal(m.finalDecision, "NOT_EVALUATED");
    assert.equal(m.requiresHumanReview, false);
    assert.ok(m.explanation.includes("No safety analysis"));
}

// ---- guard rails ------------------------------------------------------------
{
    assert.throws(() => buildVerdictModel(null), "must reject a null payload");
    assert.equal(buildVerdictModel({ task_id: "X", status: "CREATED", result: null }).permitId, "PERMIT-UNKNOWN");
}

console.log("render_test.mjs: all assertions passed");
// Let the event loop drain instead of forcing teardown with process.exit(0):
// on Windows, calling process.exit() while the top-level await import is
// still wrapping up can trip a libuv async-handle closing assertion and abort
// the process (exit code 0xC0000409) even though every assertion passed.
process.exitCode = 0;