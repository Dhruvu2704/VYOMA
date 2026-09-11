/* Local FastAPI client for the KAVACH frontend.
 *
 * Every request targets the SAME ORIGIN (the FastAPI backend serving this
 * site). No external hosts are ever contacted and no credentials are
 * embedded in this code: authentication uses the backend JWT flow and the
 * token stays in sessionStorage for the current tab session.
 */
(function (g) {
    "use strict";

    var TOKEN_KEY = "kavach_token";

    function token() {
        return g.sessionStorage.getItem(TOKEN_KEY);
    }

    function setToken(value) {
        g.sessionStorage.setItem(TOKEN_KEY, value);
    }

    function clearToken() {
        g.sessionStorage.removeItem(TOKEN_KEY);
    }

    function isAuthed() {
        return !!token();
    }

    function apiFetch(path, options) {
        if (typeof path !== "string" || path.indexOf("/api/") !== 0) {
            throw new Error("Frontend may only call the local backend API");
        }
        options = options || {};
        options.headers = Object.assign({}, options.headers || {});
        var t = token();
        if (t) {
            options.headers["Authorization"] = "Bearer " + t;
        }
        return g.fetch(path, options);
    }

    function handleJson(resp) {
        if (resp.status === 401) {
            clearToken();
        }
        return resp.json().then(function (body) {
            if (!resp.ok) {
                var detail =
                    body && body.detail
                        ? String(body.detail)
                        : "HTTP " + resp.status;
                var err = new Error(detail);
                err.status = resp.status;
                throw err;
            }
            return body;
        });
    }

    function login(username, password) {
        return g.fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, password: password }),
        })
            .then(handleJson)
            .then(function (body) {
                setToken(body.access_token);
                return body;
            });
    }

    function register(username, password) {
        return g
            .fetch("/api/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: username, password: password }),
            })
            .then(handleJson)
            .then(function () {
                return login(username, password);
            });
    }

    function health() {
        return apiFetch("/api/health").then(handleJson);
    }

    function listTasks(limit) {
        return apiFetch("/api/tasks?limit=" + (limit || 20)).then(handleJson);
    }

    function getTask(taskId) {
        return apiFetch("/api/tasks/" + encodeURIComponent(taskId)).then(handleJson);
    }

    function uploadTask(file) {
        var fd = new FormData();
        fd.append("file", file, file.name);
        return apiFetch("/api/tasks/upload", { method: "POST", body: fd }).then(handleJson);
    }

    function processTask(taskId) {
        return apiFetch(
            "/api/tasks/" + encodeURIComponent(taskId) + "/process",
            { method: "POST" }
        ).then(handleJson);
    }

    function getAudit() {
        return apiFetch("/api/audit/").then(handleJson);
    }

    function verifyAudit() {
        return apiFetch("/api/audit/verify").then(handleJson);
    }

    var api = {
        TOKEN_KEY: TOKEN_KEY,
        token: token,
        setToken: setToken,
        clearToken: clearToken,
        isAuthed: isAuthed,
        apiFetch: apiFetch,
        login: login,
        register: register,
        health: health,
        listTasks: listTasks,
        getTask: getTask,
        uploadTask: uploadTask,
        processTask: processTask,
        getAudit: getAudit,
        verifyAudit: verifyAudit,
    };

    g.KavachApi = api;
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
})(typeof window !== "undefined" ? window : globalThis);