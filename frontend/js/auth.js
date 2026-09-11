/* Shared authentication UI helpers.
 *
 * Integrates with the existing backend JWT auth (POST /api/auth/register,
 * POST /api/auth/login). Tokens are stored in sessionStorage only.
 */
(function (g) {
    "use strict";

    function updateNav() {
        var el = g.document.getElementById("auth-status");
        if (!el) {
            return;
        }
        if (KavachApi.isAuthed()) {
            el.innerHTML =
                '<span class="badge st-ok"><span class="led led-ok"></span>AUTHENTICATED</span>';
        } else {
            el.innerHTML =
                '<span class="badge st-idle"><span class="led led-idle"></span>NOT LOGGED IN</span>';
        }
    }

    function bindAuthForms(scope) {
        scope = scope || g.document;
        var loginForm = scope.getElementById("login-form");
        var registerForm = scope.getElementById("register-form");
        var authError = scope.getElementById("auth-error");

        function showError(msg) {
            if (authError) {
                authError.textContent = msg;
                authError.classList.remove("hidden");
            }
        }

        if (loginForm) {
            loginForm.addEventListener("submit", function (ev) {
                ev.preventDefault();
                var username = scope.getElementById("login-username").value;
                var password = scope.getElementById("login-password").value;
                KavachApi.login(username, password)
                    .then(function () {
                        g.location.reload();
                    })
                    .catch(function (err) {
                        showError("Login failed: " + err.message);
                    });
            });
        }

        if (registerForm) {
            registerForm.addEventListener("submit", function (ev) {
                ev.preventDefault();
                var username = scope.getElementById("register-username").value;
                var password = scope.getElementById("register-password").value;
                KavachApi.register(username, password)
                    .then(function () {
                        g.location.reload();
                    })
                    .catch(function (err) {
                        showError("Registration failed: " + err.message);
                    });
            });
        }
    }

    g.KavachAuth = {
        updateNav: updateNav,
        bindAuthForms: bindAuthForms,
    };
})(window);