/* Analysis Result (result.html) wiring.
 *
 * Reads ?id= from the URL and pulls the REAL task payload from
 * GET /api/tasks/{task_id}; rendering is done by KavachRender.
 */
(function () {
    "use strict";

    function taskIdFromQuery() {
        var params = new URLSearchParams(window.location.search);
        return params.get("id");
    }

    function renderFailure(message) {
        var el = document.getElementById("result");
        el.innerHTML =
            '<section class="ex ex-error"><strong>RESULT UNAVAILABLE</strong><br>' +
            KavachRender.esc(message) +
            "</section>";
    }

    function renderTask(task) {
        var el = document.getElementById("result");
        el.innerHTML = KavachRender.renderResult(task);
        var human = task.result && task.result.requires_human_review;
        var warn = document.getElementById("human-warning");
        if (warn) {
            warn.classList.toggle("hidden", !human);
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!KavachApi.isAuthed()) {
            window.location.href = "index.html";
            return;
        }
        KavachAuth.updateNav();
        var id = taskIdFromQuery();
        if (!id) {
            renderFailure("Missing task id parameter (?id=TASK-001).");
            return;
        }
        KavachApi.getTask(id)
            .then(renderTask)
            .catch(function (err) {
                if (err.status === 401) {
                    window.location.href = "index.html";
                    return;
                }
                renderFailure(err.message);
            });
    });
})();