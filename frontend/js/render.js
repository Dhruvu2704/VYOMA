/* Pure presentation logic for the KAVACH frontend.
 *
 * This module has NO DOM coupling: it turns backend JSON payloads into
 * display models and HTML strings. It is loaded in the browser as a plain
 * script and exercised directly under Node for integration tests.
 *
 * It contains no safety logic, no verdict calculation, no hash
 * computation, and no hard-coded analysis results: every value shown to
 * the operator originates from the local FastAPI backend.
 */
(function (g) {
    "use strict";

    function esc(v) {
        return String(v === undefined || v === null ? "" : v)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function statusClass(status) {
        var s = String(status || "").toUpperCase();
        if (s === "COMPLETED") {
            return "st-ok";
        }
        if (s === "PROCESSING") {
            return "st-busy";
        }
        if (s === "CREATED") {
            return "st-idle";
        }
        return "st-fail";
    }

    function decisionClass(decision) {
        var d = String(decision || "");
        if (d === "PASS" || d == "APPROVED") {
            return "verdict-ok";
        }
        if (d === "FLAGGED_FOR_REVIEW" || d === "REVIEW") {
            return "verdict-review";
        }
        return "verdict-crit";
    }

    function verifyClass(agreement) {
        var a = String(agreement || "").toUpperCase();
        if (a === "AGREE") {
            return "verify-ok";
        }
        if (a === "DISAGREE") {
            return "verify-crit";
        }
        return "verify-unknown";
    }

    function htmlList(items) {
        if (!Array.isArray(items) || items.length === 0) {
            return '<span class="muted">none</span>';
        }
        var lis = items.map(function (i) {
            return "<li>" + esc(i) + "</li>";
        });
        return '<ul class="rule-list">' + lis.join("") + "</ul>";
    }

    function deliverableUrl(taskId, filename) {
        return (
            "/api/tasks/" +
            encodeURIComponent(taskId) +
            "/deliverables/" +
            encodeURIComponent(filename)
        );
    }

    function validateTask(task) {
        if (!task || typeof task !== "object") {
            throw new Error("No task data");
        }
        if (String(task.task_id || "").indexOf("TASK-") !== 0) {
            throw new Error("Malformed task payload");
        }
    }

    function buildResultModel(task) {
        validateTask(task);
        var r = task.result || {};
        var elapsed = null;
        if (task.created_at && task.updated_at) {
            var t0 = Date.parse(task.created_at);
            var t1 = Date.parse(task.updated_at);
            if (!isNaN(t0) && !isNaN(t1)) {
                elapsed = Math.max(0, Math.round((t1 - t0) / 1000));
            }
        }
        return {
            taskId: task.task_id,
            status: task.status,
            permitId: task.permit_id || "\u2014",
            scenario: task.scenario || "\u2014",
            filename: task.filename || "\u2014",
            error: task.error || null,
            auditRef: task.audit_ref || "\u2014",
            elapsed: elapsed,
            deterministicEvaluated: Boolean(r.deterministic_safety_evaluated),
            ruleResult: r.rule_result || "\u2014",
            rulesTriggered: r.rules_triggered || [],
            conflictingPermitIds: r.conflicting_permit_ids || [],
            ruleExplanation: r.rule_explanation || "",
            llmResult: r.llm_result || "\u2014",
            reasoningProvider: r.reasoning_provider || "\u2014",
            reasoningExplanation: r.reasoning_explanation || "",
            verification: r.agreement || "\u2014",
            finalDecision: r.final_decision || "\u2014",
            humanReview: Boolean(r.requires_human_review),
            explanation: r.explanation || "",
            generatedAt: r.generated_at || "\u2014",
            deliverables: task.deliverables || [],
        };
    }

    function renderStatusBadge(status) {
        return (
            '<span class="badge ' +
            statusClass(status) +
            '"><span class="led ' +
            (statusClass(status) === "st-ok"
                ? "led-ok"
                : statusClass(status) === "st-busy"
                ? "led-busy"
                : statusClass(status) === "st-fail"
                ? "led-fail"
                : "led-idle") +
            '"></span>' +
            esc(status || "\u2014") +
            "</span>"
        );
    }

    function renderDeliverables(model) {
        if (!model.deliverables.length) {
            return '<span class="muted">none</span>';
        }
        var rows = model.deliverables.map(function (d) {
            return (
                "<tr>" +
                '<td><a href="' +
                deliverableUrl(model.taskId, d.filename) +
                '">' +
                esc(d.filename) +
                "</a></td>" +
                "<td>" +
                esc(d.file_type || "\u2014") +
                "</td>" +
                '<td class="mono">' +
                esc(d.sha256 || "\u2014") +
                "</td>" +
                "</tr>"
            );
        });
        return '<table class="data"><tr><th>File</th><th>Type</th><th>SHA-256</th></tr>' + rows.join("") + "</table>";
    }

    function renderResult(task) {
        var m = buildResultModel(task);
        var html = [];

        html.push(
            '<section class="panel verdict ' +
                decisionClass(m.finalDecision) +
                '">' +
                '<div class="verdict-label">Final Decision</div>' +
                '<div class="verdict-value">' +
                esc(m.finalDecision) +
                "</div>" +
                (m.humanReview
                    ? '<div class="human-review-flag">Human Review Required</div>'
                    : "") +
                "</section>"
        );

        if (m.error) {
            html.push(
                '<section class="ex ex-error">PROCESSING ERROR: ' +
                    esc(m.error) +
                    "</section>"
            );
        }

        html.push('<div class="grid2">');
        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Permit / Task</div>' +
                '<div class="kv"><span class="k">Permit ID</span><span class="v">' +
                esc(m.permitId) +
                "</span></div>" +
                '<div class="kv"><span class="k">Task ID</span><span class="v">' +
                esc(m.taskId) +
                "</span></div>" +
                '<div class="kv"><span class="k">Scenario</span><span class="v">' +
                esc(m.scenario) +
                "</span></div>" +
                '<div class="kv"><span class="k">Source File</span><span class="v">' +
                esc(m.filename) +
                "</span></div>" +
                '<div class="kv"><span class="k">Status</span><span class="v">' +
                renderStatusBadge(m.status) +
                "</span></div>" +
                (m.elapsed !== null
                    ? '<div class="kv"><span class="k">Processing Time</span><span class="v">' +
                      m.elapsed +
                      " sec</span></div>"
                    : "") +
                "</section>"
        );

        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Audit &amp; Trace</div>' +
                '<div class="kv"><span class="k">Audit Reference</span><span class="v mono">' +
                esc(m.auditRef) +
                "</span></div>" +
                '<div class="kv"><span class="k">Generated At</span><span class="v">' +
                esc(m.generatedAt) +
                "</span></div>" +
                '<div class="kv"><span class="k">Deliverables</span><span class="v">' +
                m.deliverables.length +
                "</span></div>" +
                '<div class="kv"><span class="k">Scope</span><span class="v">KAVACH AgentOrchestrator</span></div>' +
                "</section>"
        );
        html.push("</div>");

        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Deterministic Safety <span class="pad">(Plant Safety Rules)</span></div>' +
                '<div class="kv"><span class="k">Deterministic Result</span><span class="v">' +
                esc(m.ruleResult) +
                "</span></div>" +
                '<div class="kv"><span class="k">Safety Evaluated</span><span class="v">' +
                (m.deterministicEvaluated ? "True" : "False") +
                "</span></div>" +
                '<div class="kv"><span class="k">Rules Triggered</span><span class="v">' +
                htmlList(m.rulesTriggered) +
                "</span></div>" +
                '<div class="kv"><span class="k">Conflicting Permits</span><span class="v">' +
                htmlList(m.conflictingPermitIds) +
                "</span></div>" +
                '<div class="kv"><span class="k">Rule Detail</span><span class="v">' +
                esc(m.ruleExplanation) +
                "</span></div>" +
                "</section>"
        );

        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Model Reasoning <span class="pad">(Local)</span></div>' +
                '<div class="kv"><span class="k">Model Provider</span><span class="v">' +
                esc(m.reasoningProvider) +
                "</span></div>" +
                '<div class="kv"><span class="k">Reasoning Result</span><span class="v">' +
                esc(m.llmResult) +
                "</span></div>" +
                '<div class="kv"><span class="k">Reasoning Detail</span><span class="v">' +
                esc(m.reasoningExplanation) +
                "</span></div>" +
                "</section>"
        );

        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Verification</div>' +
                '<div class="kv"><span class="k">Model vs. Deterministic</span><span class="v">' +
                '<span class="badge ' +
                (m.verification === "AGREE" ? "st-ok" : m.verification === "DISAGREE" ? "st-fail" : "st-idle") +
                '">' +
                esc(m.verification) +
                "</span></span></div>" +
                "</section>"
        );

        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Explanation</div>' +
                '<div class="muted">' +
                esc(m.explanation) +
                "</div>" +
                "</section>"
        );

        html.push(
            '<section class="panel">' +
                '<div class="sec-label">Deliverables</div>' +
                renderDeliverables(m) +
                "</section>"
        );

        return html.join("\n");
    }

    function renderTaskRow(task) {
        var decision = task.result && task.result.final_decision
            ? esc(task.result.final_decision)
            : '<span class="muted">\u2014</span>';
        return (
            "<tr>" +
            '<td><a href="result.html?id=' +
            encodeURIComponent(task.task_id) +
            '">' +
            esc(task.task_id) +
            "</a></td>" +
            "<td>" +
            esc(task.permit_id || "\u2014") +
            "</td>" +
            "<td>" +
            esc(task.scenario || "\u2014") +
            "</td>" +
            "<td>" +
            renderStatusBadge(task.status) +
            "</td>" +
            "<td>" +
            decision +
            "</td>" +
            "</tr>"
        );
    }

    function renderAuditRows(events) {
        if (!Array.isArray(events) || events.length === 0) {
            return '<tr><td colspan="6"><span class="muted">No audit records yet</span></td></tr>';
        }
        return events
            .map(function (e) {
                return (
                    "<tr>" +
                    '<td class="mono">' +
                    esc(e.audit_ref) +
                    "</td>" +
                    "<td>" +
                    esc(e.permit_id) +
                    "</td>" +
                    '<td class="mono">' +
                    esc(e.timestamp) +
                    "</td>" +
                    '<td class="mono">' +
                    esc(e.pipeline || "") +
                    "</td>" +
                    '<td class="mono">' +
                    esc(e.previous_hash) +
                    "</td>" +
                    '<td class="mono">' +
                    esc(e.event_hash) +
                    "</td>" +
                    "</tr>"
                );
            })
            .join("");
    }

    var api = {
        esc: esc,
        statusClass: statusClass,
        decisionClass: decisionClass,
        verifyClass: verifyClass,
        htmlList: htmlList,
        deliverableUrl: deliverableUrl,
        buildResultModel: buildResultModel,
        renderResult: renderResult,
        renderStatusBadge: renderStatusBadge,
        renderTaskRow: renderTaskRow,
        renderAuditRows: renderAuditRows,
    };

    g.KavachRender = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);