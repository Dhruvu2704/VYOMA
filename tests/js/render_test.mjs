/* Node test for frontend/js/render.js (pure presentation logic).
 *
 * run with: node tests/js/render_test.mjs
 * Executed from tests/test_frontend_integration.py as a subprocess.
 */
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const RENDER_SRC = readFileSync(
    new URL("../../frontend/js/render.js", import.meta.url),
    "utf8"
);

eval(RENDER_SRC);
const R = globalThis.KavachRender;
assert.ok(R, "KavachRender must be exported to globalThis");

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
    error: null,
    result: {
        ...CONFLICT_TASK.result,
        rule_result: "PASS",
        rules_triggered: ["no-conflict", "tags-resolved"],
        conflicting_permit_ids: [],
        llm_result: "PASS",
        agreement: "AGREE",
        final_decision: "PASS",
        requires_human_review: false,
    },
};

const FAILED_TASK = {
    task_id: "TASK-003",
    status: "FAILED",
    filename: "bad.json",
    permit_id: "MR-0000-UNKNOWN",
    scenario: "unknown",
    audit_ref: null,
    error: "RuntimeError: connector failure",
    result: null,
    deliverables: [],
};

function check(html, needle, label) {
    assert.ok(html.includes(needle), `${label}: missing "${needle}" in rendered HTML`);
}

// ---- model extraction -----------------------------------------------------
{
    const m = R.buildResultModel(CONFLICT_TASK);
    assert.equal(m.finalDecision, "FLAGGED_FOR_REVIEW");
    assert.equal(m.ruleResult, "FLAGGED");
    assert.equal(m.permitId, "MR-0002-CONF");
    assert.equal(m.auditRef, "AUD-1234567890AB");
    assert.deepEqual(m.rulesTriggered[0], "permit-conflict");
    assert.deepEqual(m.conflictingPermitIds, ["MR-0003-CONF"]);
    assert.equal(m.reasoningProvider, "ollama:llama3");
    assert.equal(m.llmResult, "FLAGGED");
    assert.equal(m.verification, "AGREE");
    assert.equal(m.humanReview, true);
    assert.equal(m.elapsed, 12);
    assert.equal(m.deliverables.length, 1);
}

// ---- rendering: final decision -------------------------------------------
{
    const html = R.renderResult(CONFLICT_TASK);
    check(html, "FLAGGED_FOR_REVIEW", "final decision");
    check(html, "Human Review Required", "human review flag");
    check(html, "MR-0003-CONF", "conflicting permit");
    check(html, "permit-conflict", "rule triggered");
    check(html, "hot-work-overlap", "rule triggered");
    check(html, "isolation-overlap-time-window", "rule triggered");
    check(html, "ollama:llama3", "model provider");
    check(html, "AGREE", "verification");
    check(html, "AUD-1234567890AB", "audit reference");
    check(
        html,
        "/api/tasks/TASK-001/deliverables/memo_TASK-001.docx",
        "deliverable link"
    );
    check(html, "KAVACH AgentOrchestrator", "pipeline scope label");
}

// ---- rendering: PASS (no human review) ------------------------------------
{
    const html = R.renderResult(SAFE_TASK);
    check(html, "PASS", "pass decision");
    assert.ok(!html.includes("Human Review Required"), "PASS must not flag human review");
}

// ---- rendering: failed task shows error, no fabricated verdict ------------
{
    const html = R.renderResult(FAILED_TASK);
    check(html, "RuntimeError: connector failure", "error text");
    check(html, "PROCESSING ERROR", "error banner");
    assert.ok(!html.includes("FLAGGED_FOR_REVIEW"), "failed task must not fabricate a verdict");
}

// ---- status / decision / verification class mapping -----------------------
{
    assert.equal(R.statusClass("COMPLETED"), "st-ok");
    assert.equal(R.statusClass("PROCESSING"), "st-busy");
    assert.equal(R.statusClass("CREATED"), "st-idle");
    assert.equal(R.statusClass("FAILED"), "st-fail");
    assert.equal(R.decisionClass("FLAGGED_FOR_REVIEW"), "verdict-review");
    assert.equal(R.decisionClass("PASS"), "verdict-ok");
    assert.equal(R.decisionClass("BLOCKED"), "verdict-crit");
    assert.equal(R.verifyClass("AGREE"), "verify-ok");
    assert.equal(R.verifyClass("DISAGREE"), "verify-crit");
}

// ---- validation guards -----------------------------------------------------
{
    assert.throws(() => R.buildResultModel(null), /No task data/);
    assert.throws(() => R.buildResultModel({ task_id: "X" }), /Malformed task payload/);
}

// ---- deliverable URL encoding ---------------------------------------------
{
    assert.equal(
        R.deliverableUrl("TASK-001", "memo A&.docx"),
        "/api/tasks/TASK-001/deliverables/memo%20A%26.docx"
    );
}

console.log("render_test.mjs: all assertions passed");
process.exit(0);