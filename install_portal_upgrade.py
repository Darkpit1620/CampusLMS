"""CampusLMS portal patcher: makes backups and surgically registers new portals.
Run once from the EXISTING CampusLMS project folder:
    python install_portal_upgrade.py

Never deletes or resets a database. Idempotent on repeated runs.
"""
from pathlib import Path
import datetime
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "_campus_portal_upgrade" / "files"


def stop(message):
    raise SystemExit("STOP: " + message)


def ensure_after(pattern, text, insertion, desc):
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        stop(f"Could not safely update {desc}. No project files changed.")
    return text[:match.end()] + insertion + text[match.end():]


def main():
    required = ["manage.py", "config/urls.py", "config/settings.py", "accounts/models.py", "admissions/models.py", "dashboard/templates/dashboard/base.html"]
    missing = [p for p in required if not (ROOT / p).is_file()]
    if missing:
        stop(f"Run from your existing CampusLMS directory, not Downloads. Missing: {', '.join(missing)}")
    if not PAYLOAD.is_dir():
        stop("The ZIP was not extracted completely; the _campus_portal_upgrade/files folder is missing.")

    originals = {p: (ROOT/p).read_text(encoding="utf-8") for p in [
        "config/urls.py", "config/settings.py", "accounts/models.py", "dashboard/templates/dashboard/base.html"
    ]}
    planned = {}

    # Update Role choices in the SAME custom user model, preserving existing users.
    code = originals["accounts/models.py"]
    if not re.search(r'\bSTAFF\s*=\s*[\'"]STAFF[\'"]', code):
        code = ensure_after(r'^\s*STUDENT\s*=\s*[\'"]STUDENT[\'"].*$', code,
                            '\n        STAFF = "STAFF", "University Staff"', "accounts/models.py")
    planned["accounts/models.py"] = code

    settings = originals["config/settings.py"]
    if '"campus_access.apps.CampusAccessConfig"' not in settings and "'campus_access.apps.CampusAccessConfig'" not in settings and "'campus_access'" not in settings and '"campus_access"' not in settings:
        settings = ensure_after(r'^INSTALLED_APPS\s*=\s*\[', settings,
                                '\n    "campus_access.apps.CampusAccessConfig",', "config/settings.py")
    if "# BEGIN CAMPUSLMS APPROVAL EMAIL" not in settings and not re.search(r'^\s*EMAIL_BACKEND\s*=', settings, re.MULTILINE):
        settings += '''\n\n# BEGIN CAMPUSLMS APPROVAL EMAIL (environment variables only; no secrets in code)\nimport os as _campus_os\nEMAIL_BACKEND = _campus_os.getenv(\n    "CAMPUS_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"\n)\nDEFAULT_FROM_EMAIL = _campus_os.getenv("CAMPUS_FROM_EMAIL", "CampusLMS <no-reply@localhost>")\nEMAIL_HOST = _campus_os.getenv("CAMPUS_SMTP_HOST", "smtp.gmail.com")\nEMAIL_PORT = int(_campus_os.getenv("CAMPUS_SMTP_PORT", "587"))\nEMAIL_USE_TLS = _campus_os.getenv("CAMPUS_SMTP_TLS", "1") == "1"\nEMAIL_HOST_USER = _campus_os.getenv("CAMPUS_SMTP_USER", "")\nEMAIL_HOST_PASSWORD = _campus_os.getenv("CAMPUS_SMTP_PASSWORD", "")\nEMAIL_TIMEOUT = 15\nCAMPUS_PUBLIC_URL = _campus_os.getenv("CAMPUS_PUBLIC_URL", "http://127.0.0.1:8001")\n# END CAMPUSLMS APPROVAL EMAIL\n'''
    elif 'CAMPUS_PUBLIC_URL' not in settings:
        settings += '\n# Links in approval emails (set CAMPUS_PUBLIC_URL on your server)\nimport os as _campus_os\nCAMPUS_PUBLIC_URL = _campus_os.getenv("CAMPUS_PUBLIC_URL", "http://127.0.0.1:8001")\n'
    planned["config/settings.py"] = settings

    # The root '/' now renders CampusLMS portal choices directly. Original '/' home remains
    # available as a view within dashboard, but is deliberately superseded at the root.
    urls = originals["config/urls.py"]
    if 'from campus_access.views import access_home as campus_portal_home' not in urls:
        urls = ensure_after(r'^from django\.urls import .*$', urls,
            '\nfrom campus_access.views import access_home as campus_portal_home', 'config/urls.py import')
    if not re.search(r'from django\.urls import .*\binclude\b', urls):
        urls = ensure_after(r'^from django\.urls import .*$', urls, '\nfrom django.urls import include', 'config/urls.py include import')
    extra_paths = ''
    if not re.search(r'path\(\s*[\'"]\s*[\'"],\s*campus_portal_home\s*,', urls):
        extra_paths += '\n    path("", campus_portal_home, name="campus_portal_root"),'
    if not re.search(r'path\(\s*[\'"]access/[\'"],', urls):
        extra_paths += '\n    path("access/", include("campus_access.urls")),'
    if extra_paths:
        urls = ensure_after(r'^urlpatterns\s*=\s*\[', urls, extra_paths, 'config/urls.py urlpatterns')
    planned["config/urls.py"] = urls

    base = originals["dashboard/templates/dashboard/base.html"]
    if "campus_access/password-eye.css" not in base or "campus_access/password-eye.js" not in base:
        if '</head>' not in base:
            stop('Shared base.html has no </head>. Cannot safely add show/hide control.')
        asset_tags = ''
        if 'campus_access/password-eye.css' not in base:
            asset_tags += '''  <link rel="stylesheet" href="{% static 'campus_access/password-eye.css' %}">\n'''
        if 'campus_access/password-eye.js' not in base:
            asset_tags += '''  <script defer src="{% static 'campus_access/password-eye.js' %}"></script>\n'''
        base = base.replace('</head>', asset_tags + '</head>', 1)
    # Change only the anonymous nav 'Sign in' link. The portal home displays all roles.
    base = base.replace('href="{% url \'login\' %}"', 'href="{% url \'campus_access:home\' %}"')
    planned["dashboard/templates/dashboard/base.html"] = base

    # Additional generated templates are pulled from Stage 11C, not user project files.
    payload_files = [p for p in PAYLOAD.rglob('*') if p.is_file()]
    files_to_backup = set(planned.keys()) | {str(p.relative_to(PAYLOAD)) for p in payload_files}
    # Use an external backup directory. Make a fresh copy of SQLite before anything changes.
    backup_root = Path.home() / "Documents" / ("CampusLMS_PortalFixBackup_" + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup_root.mkdir(parents=True, exist_ok=False)
    db = ROOT / "db.sqlite3"
    if db.is_file(): shutil.copy2(db, backup_root / db.name)
    backed_up = 0
    for relative in sorted(files_to_backup):
        original = ROOT / relative
        if original.is_file():
            target = backup_root / "original_files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            backed_up += 1

    # Only after the preflight and backup, modify the project.
    for p in payload_files:
        target = ROOT / p.relative_to(PAYLOAD)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    for relative, content in planned.items():
        (ROOT / relative).write_text(content, encoding="utf-8")
    print("\\nCampusLMS Portal Upgrade files applied successfully.")
    print("Existing db.sqlite3 was NOT reset or modified by this installer.")
    print(f"Safety backup: {backup_root}")
    print(f"Existing files backed up: {backed_up}")
    print("Next, run: python manage.py check")
    print("Then: python manage.py makemigrations accounts campus_access")
    print("Then: python manage.py migrate")
    print("Then: python manage.py test campus_access admissions")
    print("Finally: python manage.py runserver 8001")
    print("Open: http://127.0.0.1:8001/ (main address, no /access/ needed)")


if __name__ == "__main__":
    main()
