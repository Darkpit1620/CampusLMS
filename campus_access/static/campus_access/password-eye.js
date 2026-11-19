(function () {
    "use strict";
    function init() {
        var fields = document.querySelectorAll('input[type="password"]');
        fields.forEach(function (field) {
            if (field.dataset.eyeApplied) return;
            field.dataset.eyeApplied = "1";
            var wrapper = document.createElement("div");
            wrapper.className = "clms-password-wrap";
            field.parentNode.insertBefore(wrapper, field);
            wrapper.appendChild(field);
            var button = document.createElement("button");
            button.type = "button";
            button.className = "clms-password-eye";
            button.setAttribute("aria-label", "Show password");
            button.setAttribute("aria-pressed", "false");
            button.title = "Show password";
            // Accessible native button, no external icon package required.
            var openEye = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.1 12s3.6-7 9.9-7 9.9 7 9.9 7-3.6 7-9.9 7S2.1 12 2.1 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
            var crossedEye = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 3 18 18"/><path d="M10.6 5.1a11.2 11.2 0 0 1 1.4-.1c6.3 0 9.9 7 9.9 7a14.4 14.4 0 0 1-3.3 4"/><path d="M6.1 6.2C3.5 8.3 2.1 12 2.1 12s3.6 7 9.9 7c1.3 0 2.5-.3 3.6-.8"/><path d="M10 10a3 3 0 0 0 4 4"/></svg>';
            button.innerHTML = openEye;
            button.addEventListener("click", function () {
                var visible = field.type === "password";
                field.type = visible ? "text" : "password";
                button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
                button.setAttribute("aria-pressed", visible ? "true" : "false");
                button.title = visible ? "Hide password" : "Show password";
                button.innerHTML = visible ? crossedEye : openEye;
                field.focus();
            });
            wrapper.appendChild(button);
        });
        document.querySelectorAll("form").forEach(function (form) {
            var p1 = form.querySelector('[name="password1"]');
            var p2 = form.querySelector('[name="password2"]');
            if (!p1 || !p2) return;
            function validate() {
                p2.setCustomValidity(
                    p2.value && p1.value !== p2.value
                        ? "Passwords do not match. Please check both fields."
                        : ""
                );
            }
            p1.addEventListener("input", validate);
            p2.addEventListener("input", validate);
            form.addEventListener("submit", function (event) {
                validate();
                if (!p2.checkValidity()) {
                    event.preventDefault();
                    p2.reportValidity();
                }
            });
        });
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else { init(); }
}());
