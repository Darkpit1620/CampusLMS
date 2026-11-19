"""One-command non-destructive CampusLMS Stage 14 installer.

Preflight, timestamped online SQLite backup, install NEW app, inject visible
student links, migrate/test. Never overwrites existing course/user/grade data.
"""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "_campus_services" / "files" / "campus_services"


def stop(reason):
    raise SystemExit("STOP: " + reason)


def command(*args):
    argv = [sys.executable, "manage.py", *args]
    print("\n>>> " + " ".join(argv), flush=True)
    result = subprocess.run(argv, cwd=ROOT, check=False)
    if result.returncode != 0:
        stop("Django returned an error. Please send the terminal output. Your safety backup is available; DO NOT delete or reset the database.")


def main():
    needed = (
        "manage.py", "db.sqlite3", "config/settings.py", "config/urls.py",
        "dashboard/templates/dashboard/base.html", "accounts/models.py",
        "academics/models.py", "academics/migrations/__init__.py",
        "courses/models.py", "assignments/models.py",
    )
    missing = [n for n in needed if not (ROOT / n).is_file()]
    if missing:
        stop("Please first install the integrated academic catalogue and extract this ZIP into your ORIGINAL CampusLMS folder. Missing: " + ", ".join(missing))
    if not (PAYLOAD / "models.py").is_file():
        stop("The ZIP was not extracted completely. Missing Stage 14 model files.")
    settings_path = ROOT / "config/settings.py"
    urls_path = ROOT / "config/urls.py"
    base_path = ROOT / "dashboard/templates/dashboard/base.html"
    role_path = ROOT / "dashboard/templates/dashboard/role_dashboard.html"
    originals = {p: p.read_text(encoding="utf-8") for p in (settings_path, urls_path, base_path)}
    if role_path.is_file():
        originals[role_path] = role_path.read_text(encoding="utf-8")
    settings = originals[settings_path]
    urls = originals[urls_path]
    base = originals[base_path]
    if not re.search(r"^INSTALLED_APPS\s*=\s*\[", settings, re.M):
        stop("Cannot find INSTALLED_APPS in settings.py. No files changed.")
    if "academics" not in settings:
        stop("The academic catalogue app is not active. Install Stage 13 first. No files changed.")
    if not re.search(r"^urlpatterns\s*=\s*\[", urls, re.M):
        stop("Cannot find urlpatterns in config/urls.py. No files changed.")
    if "</nav>" not in base or "</head>" not in base:
        stop("Your custom dashboard layout is not compatible with the safe automatic edit. No files changed.")
    if role_path.is_file() and "{% endblock %}" not in originals[role_path]:
        stop("The role_dashboard.html template has been heavily modified. Please share it so we can add the service cards safely.")
    if not re.search(r"['\"]campus_services(?:\.apps\.CampusServicesConfig)?['\"]", settings):
        settings = re.sub(r"^(INSTALLED_APPS\s*=\s*\[)",
                          r'\1\n    "campus_services.apps.CampusServicesConfig",', settings, count=1, flags=re.M)
    if not re.search(r"^from django\.urls import .*\binclude\b", urls, re.M):
        match = re.search(r"^from django\.urls import .*$", urls, re.M)
        if not match:
            stop("Cannot find django.urls import to add include. No files changed.")
        urls = urls[:match.end()] + "\nfrom django.urls import include" + urls[match.end():]
    if not re.search(r"path\(\s*['\"]services/['\"]", urls):
        urls = re.sub(r"^(urlpatterns\s*=\s*\[)",
                      r'\1\n    path("services/", include("campus_services.urls")),', urls, count=1, flags=re.M)
    if "<!-- CAMPUSLMS STUDENT SERVICES STYLES -->" not in base:
        base = base.replace("</head>",
            '''<!-- CAMPUSLMS STUDENT SERVICES STYLES -->
  <link rel="stylesheet" href="{% static 'campus_services/services.css' %}">
</head>''', 1)
    if "<!-- CAMPUSLMS STUDENT SERVICES NAV -->" not in base:
        navigation = '''            <!-- CAMPUSLMS STUDENT SERVICES NAV -->
            {% if user.is_authenticated and user.role == 'STUDENT' and not user.is_staff and not user.is_superuser %}
              <a href="{% url 'campus_services:home' %}">Student Services</a>
              <a href="{% url 'campus_services:fees' %}">My Fees</a>
              <a href="{% url 'campus_services:accommodation' %}">My Hostel</a>
              <a href="{% url 'campus_services:graduation' %}">Graduation</a>
            {% endif %}
'''
        base = base.replace("</nav>", navigation + "        </nav>", 1)
    planned = {settings_path: settings, urls_path: urls, base_path: base}
    if role_path.is_file():
        role = originals[role_path]
        if "<!-- CAMPUSLMS STUDENT SERVICES DASHBOARD -->" not in role:
            addition = '''
<!-- CAMPUSLMS STUDENT SERVICES DASHBOARD -->
{% if user.is_authenticated and user.role == 'STUDENT' and not user.is_staff and not user.is_superuser %}
<section class="cs-wrap" style="padding-top:0">
  <span class="cs-eyebrow">STUDENT ESSENTIALS</span>
  <h2>Finances, Accommodation &amp; Graduation</h2>
  <div class="cs-grid">
    <article class="cs-card"><h2>My Fees</h2><p class="cs-muted">Check tuition, payments, and balance.</p><a class="cs-link" href="{% url 'campus_services:fees' %}">View Fee Statement →</a></article>
    <article class="cs-card"><h2>My Hostel</h2><p class="cs-muted">See your allocated room and hostel fees.</p><a class="cs-link" href="{% url 'campus_services:accommodation' %}">Hostel &amp; Room →</a></article>
    <article class="cs-card"><h2>Graduation</h2><p class="cs-muted">Check clearances and provisional honours.</p><a class="cs-link" href="{% url 'campus_services:graduation' %}">Graduation Readiness →</a></article>
  </div>
</section>
{% endif %}
'''
            end = role.rfind("{% endblock %}")
            role = role[:end] + addition + role[end:]
        planned[role_path] = role

    target = ROOT / "campus_services"
    if target.exists():
        present = target / "models.py"
        if not present.is_file() or "class GraduationApplication(models.Model)" not in present.read_text(encoding="utf-8"):
            stop("An unrelated campus_services app exists. Stopping before any modification.")
        for source in PAYLOAD.rglob("*"):
            if source.is_file():
                dest = target / source.relative_to(PAYLOAD)
                if dest.exists() and dest.read_bytes() != source.read_bytes():
                    stop(f"An existing Stage 14 file differs from the installer: {dest}. No files changed. Preserve local edits and request a merge.")

    backup = Path.home() / "Documents" / ("CampusLMS_Services_Backup_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    backup.mkdir(parents=True, exist_ok=False)
    database = ROOT / "db.sqlite3"
    try:
        with sqlite3.connect(str(database)) as src, sqlite3.connect(str(backup / "db.sqlite3")) as dst:
            src.backup(dst)
    except sqlite3.Error as error:
        stop(f"Failed to back up SQLite: {error}. No project files changed.")
    for path in originals:
        dest = backup / "original_files" / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    print("\nSafety backup:", backup, flush=True)

    if not target.exists():
        shutil.copytree(PAYLOAD, target)
    else:
        for source in PAYLOAD.rglob("*"):
            if source.is_file():
                dest = target / source.relative_to(PAYLOAD)
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
    for path, revised in planned.items():
        if path.read_text(encoding="utf-8") != revised:
            path.write_text(revised, encoding="utf-8")

    command("check")
    command("makemigrations", "campus_services", "--noinput")
    command("migrate", "--noinput")
    command("prepare_fee_schedules")
    command("test", "campus_services", "--noinput")
    print("\nSUCCESS: CampusLMS student fees, accommodation, and graduation pages installed.")
    print("Use your EXISTING homepage, log in as a student, and open Student Services.")
    print("Admin must configure actual fee schedules, hostel rooms, verified results, and clearance before real figures appear.")
    print("Start with: python manage.py runserver 8001")


if __name__ == "__main__":
    main()
