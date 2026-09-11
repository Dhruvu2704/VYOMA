/* Audit / Trace (audit.html) wiring.
 *
 * Reads the persisted audit chain from the backend (GET /api/audit/ and
 * GET /api/audit/verify). Trace data is only what the backend records; no
 * trace is invented here.
 */
(function () {
    "use strict";

    function showChainStatus(verification) {
        var el = document.getElementById("chain-status");
        if (!el) {
            return;
        }
        var ok = verification && verification.valid === true;
        el.classList.remove("hidden");
        el.className = "ex " + (ok ? "ex-ok" : "ex-error");
        el.innerHTML = ok
            ? "<span class='led led-ok'></span>AUDIT CHAIN VALID - records are hash-chained and consistent"
            : "<span class='led led-fail'></span>AUDIT CHAIN INVALID - a record has been tampered with";
    }

    function showEvents(events) {
        var el = document.getElementById("audit-rows");
        if (!el) {
            return;
        }
        el.innerHTML = KavachRender.renderAuditRows(events);
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!KavachApi.isAuthed()) {
            window.location.href = "index.html";
            return;
        }
        KavachAuth.updateNav();
        KavachApi.verifyAudit()
            .then(showChainStatus)
            .catch(function () {
                showChainStatus({ valid: false });
            });
        KavachApi.getAudit()
            .then(showEvents)
            .catch(function (err) {
                var el = document.getElementById("audit-rows");
                if (el) {
                    el.innerHTML =
                        '<tr><td colspan="6"><span class="muted">Could not load audit records: ' +
                        KavachRender.esc(err.message) +
                        "</span></td></tr>";
                }
            });
    });
})();