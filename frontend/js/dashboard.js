/* Dashboard (index.html) wiring. */
(function () {
    "use strict";

    function renderHealth(status) {
        var el = document.getElementById("health-status");
        if (!el) {
            return;
        }
        var ok = status && status.status === "ok";
        el.className = "kv";
        el.innerHTML =
            '<span class="k">API STATUS</span><span class="v">' +
            '<span class="badge ' +
            (ok ? "st-ok" : "st-fail") +
            '"><span class="led ' +
            (ok ? "led-ok" : "led-fail") +
            '"></span>' +
            (ok ? "ONLINE" : "OFFLINE") +
            "</span></span>";
    }

    function renderTasks(tasks) {
        var el = document.getElementById("task-list");
        if (!el) {
            return;
        }
        if (!tasks || tasks.length === 0) {
            el.innerHTML =
                '<tr><td colspan="5"><span class="muted">No tasks yet. Start a safety analysis.</span></td></tr>';
            return;
        }
        el.innerHTML = tasks.map(KavachRender.renderTaskRow).join("");
    }

    function loadDashboard() {
        KavachApi.health()
            .then(renderHealth)
            .catch(function () {
                renderHealth({ status: "down" });
            });
        if (KavachApi.isAuthed()) {
            KavachApi.listTasks(10)
                .then(renderTasks)
                .catch(function (err) {
                    var el = document.getElementById("task-list");
                    if (el) {
                        el.innerHTML =
                            '<tr><td colspan="5"><span class="muted">Could not load tasks: ' +
                            KavachRender.esc(err.message) +
                            "</span></td></tr>";
                    }
                });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        KavachAuth.updateNav();
        KavachAuth.bindAuthForms(document);
        loadDashboard();
    });
})();