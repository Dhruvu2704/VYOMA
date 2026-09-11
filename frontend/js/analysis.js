/* PTW Analysis (analysis.html) wiring.
 *
 * Demonstrates the real KAVACH workflow over the backend API:
 *   upload -> process -> fetch result
 */
(function () {
    "use strict";

    var state = {
        file: null,
        taskId: null,
    };

    function esc(v) {
        return KavachRender.esc(v);
    }

    function setStatus(elId, html, cls) {
        var el = document.getElementById(elId);
        if (!el) {
            return;
        }
        el.classList.remove("hidden");
        el.className = "ex " + (cls || "ex-busy");
        el.innerHTML = html;
    }

    function hide(elId) {
        var el = document.getElementById(elId);
        if (el) {
            el.classList.add("hidden");
        }
    }

    function loadSelectedFixture() {
        var sel = document.getElementById("fixture-select");
        var src = sel.options[sel.selectedIndex].getAttribute("data-src");
        if (!src) {
            return Promise.resolve(null);
        }
        return fetch(src)
            .then(function (resp) {
                if (!resp.ok) {
                    throw new Error("Fixture unavailable: HTTP " + resp.status);
                }
                return resp.text();
            })
            .then(function (text) {
                JSON.parse(text);
                var name = src.split("/").pop();
                state.file = new File([text], name, {
                    type: "application/json",
                });
                var label = document.getElementById("selected-file");
                if (label) {
                    label.textContent = "Selected: " + name + " (fixture preset)";
                }
                hide("analysis-error");
                return state.file;
            });
    }

    function onFilePicked(ev) {
        var input = ev.target;
        if (input.files && input.files.length > 0) {
            state.file = input.files[0];
            var label = document.getElementById("selected-file");
            if (label) {
                label.textContent = "Selected: " + state.file.name;
            }
            hide("analysis-error");
        }
    }

    function requireFile() {
        if (state.file) {
            return Promise.resolve(state.file);
        }
        return loadSelectedFixture().then(function (file) {
            if (!file) {
                throw new Error("Choose a fixture preset or a local .json file");
            }
            return file;
        });
    }

    function showUploaded(task) {
        state.taskId = task.task_id;
        var el = document.getElementById("task-panel");
        el.classList.remove("hidden");
        document.getElementById("task-id").textContent = task.task_id;
        document.getElementById("task-filename").textContent = task.filename;
        document.getElementById("task-upload-status").textContent = task.status;
        var run = document.getElementById("run-button");
        run.disabled = false;
        setStatus(
            "analysis-status",
            "Envelope accepted. Task <span class='mono'>" +
                esc(task.task_id) +
                "</span> created as " +
                esc(task.status) +
                ".",
            "ex-ok"
        );
    }

    function fail(msg) {
        var run = document.getElementById("run-button");
        var uploadBtn = document.getElementById("upload-button");
        run.disabled = false;
        uploadBtn.disabled = false;
        setStatus(
            "analysis-status",
            "<strong>ANALYSIS FAILED</strong><br>" + esc(msg),
            "ex-error"
        );
    }

    function runAnalysis() {
        var run = document.getElementById("run-button");
        run.disabled = true;

        function process(taskId) {
            setStatus(
                "analysis-status",
                "<span class='led led-busy'></span>Running KAVACH AgentOrchestrator ..."
            );
            return KavachApi.processTask(taskId).then(function (processed) {
                window.location.href =
                    "result.html?id=" + encodeURIComponent(processed.task_id);
            });
        }

        if (state.taskId) {
            process(state.taskId).catch(function (err) {
                fail(err.message);
            });
            return;
        }

        requireFile()
            .then(KavachApi.uploadTask)
            .then(function (task) {
                showUploaded(task);
                return process(task.task_id);
            })
            .catch(function (err) {
                fail(err.message);
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!KavachApi.isAuthed()) {
            window.location.href = "index.html";
            return;
        }
        KavachAuth.updateNav();
        document.getElementById("upload-button").addEventListener("click", function () {
            var uploadBtn = document.getElementById("upload-button");
            uploadBtn.disabled = true;
            requireFile()
                .then(KavachApi.uploadTask)
                .then(showUploaded)
                .catch(function (err) {
                    uploadBtn.disabled = false;
                    setStatus(
                        "analysis-status",
                        "<strong>UPLOAD FAILED</strong><br>" + esc(err.message),
                        "ex-error"
                    );
                });
        });
        document.getElementById("run-button").addEventListener("click", runAnalysis);
        document.getElementById("file-input").addEventListener("change", onFilePicked);
    });
})();