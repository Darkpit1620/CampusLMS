"""One-command CampusLMS integrated admission matching + lecturer unit approvals.

Designed for the existing CampusLMS that has the working four-account portal.
Makes an SQLite online backup outside the project BEFORE modifying files.
Installs the entire 16-programme academic catalogue if it was not installed yet.
Does not replace auth, User, student admission, course, assignment, submission or grade models.
"""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "_campus_admissions_units" / "files" / "campus_admissions_units"


def fail(message):
    raise SystemExit("STOP: " + message)


def execute(*args):
    command = [sys.executable, "manage.py", *args]
    print("\n>>> " + " ".join(command), flush=True)
    code = subprocess.call(command, cwd=str(ROOT))
    if code:
        fail("A Django check failed. The safety backup exists. "
             "Do not reset your database; share this error output for a targeted fix.")


def insert_after_line(text, pattern, insertion, filename):
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        fail(f"Could not safely identify the needed location inside {filename}; no Stage 13 files modified.")
    return text[:match.end()] + insertion + text[match.end():]


def main():
    needed = (
        "manage.py", "config/settings.py", "config/urls.py", "campus_access/urls.py",
        "campus_access/templates/campus_access/home.html", "dashboard/templates/dashboard/base.html",
        "admissions/models.py", "courses/models.py", "accounts/models.py",
        "install_full_university.py",
    )
    missing = [p for p in needed if not (ROOT / p).is_file()]
    if missing:
        fail("Extract into your original CampusLMS folder first; missing: " + ", ".join(missing))
    if not (PAYLOAD / "models.py").is_file():
        fail("ZIP was incompletely extracted. Expected _campus_admissions_units/files/campus_admissions_units/models.py")

    settings_path = ROOT / "config/settings.py"
    urls_path = ROOT / "config/urls.py"
    portal_urls_path = ROOT / "campus_access/urls.py"
    base_path = ROOT / "dashboard/templates/dashboard/base.html"
    home_path = ROOT / "campus_access/templates/campus_access/home.html"

    contents = {p: p.read_text(encoding="utf-8") for p in
                (settings_path, urls_path, portal_urls_path, base_path, home_path)}
    if not re.search(r"^urlpatterns\s*=\s*\[", contents[portal_urls_path], re.M):
        fail("Cannot read your existing campus_access URL configuration")
    if not re.search(r"path\(\s*['\"]student/signup/['\"],\s*(?:views|enrolment_views)\.student_signup", contents[portal_urls_path]):
        fail("Student signup route has been customized; no safe automated replacement. Share campus_access/urls.py to merge.")
    if not re.search(r"^urlpatterns\s*=\s*\[", contents[urls_path], re.M):
        fail("Cannot identify urlpatterns in config/urls.py")
    if not re.search(r"^INSTALLED_APPS\s*=\s*\[", contents[settings_path], re.M):
        fail("Cannot identify INSTALLED_APPS in config/settings.py")
    if '</nav>' not in contents[base_path]:
        fail("Could not find global navigation in dashboard base template")
    if '{% endblock %}' not in contents[home_path]:
        fail("Could not locate homepage content endblock")
    target = ROOT / "campus_admissions_units"
    if target.is_dir():
        current = target / "models.py"
        if not current.is_file() or 'class ProgrammeApplication(models.Model)' not in current.read_text(encoding="utf-8"):
            fail("An unrelated campus_admissions_units app is present; stopping to avoid overwriting it.")
        for source in PAYLOAD.rglob("*"):
            if source.is_file():
                dest = target / source.relative_to(PAYLOAD)
                if dest.exists() and dest.read_bytes() != source.read_bytes():
                    fail(f"An existing file was locally edited: {dest}. No files changed. Please merge manually.")

    # Plan edits before touching anything.
    new_settings = contents[settings_path]
    if not re.search(r"['\"]campus_admissions_units(?:\.apps\.CampusAdmissionsUnitsConfig)?['\"]", new_settings):
        new_settings = insert_after_line(new_settings, r"^INSTALLED_APPS\s*=\s*\[",
                 '\n    "campus_admissions_units.apps.CampusAdmissionsUnitsConfig",', 'config/settings.py')

    new_urls = contents[urls_path]
    if not re.search(r"^from django\.urls import .*\binclude\b", new_urls, re.M):
        new_urls = insert_after_line(new_urls, r'^from django\.urls import .*$', '\nfrom django.urls import include', 'config/urls.py')
    if not re.search(r"path\(\s*['\"]admissions-ui/['\"]", new_urls):
        new_urls = insert_after_line(new_urls, r'^urlpatterns\s*=\s*\[',
            '\n    path("admissions-ui/", include("campus_admissions_units.urls")),', 'config/urls.py')

    new_portal_urls = contents[portal_urls_path]
    if 'from campus_admissions_units import views as enrolment_views' not in new_portal_urls:
        new_portal_urls = insert_after_line(new_portal_urls, r'^from \. import views.*$',
            '\nfrom campus_admissions_units import views as enrolment_views', 'campus_access/urls.py')
    new_portal_urls = re.sub(
        r'(path\(\s*[\'\"]student/signup/[\'\"],\s*)views\.student_signup',
        r'\1enrolment_views.student_signup', new_portal_urls, count=1,
    )

    new_base = contents[base_path]
    if '<!-- CAMPUSLMS INTEGRATED ADMISSION AND UNIT NAV -->' not in new_base:
        insertion = '''\n            <!-- CAMPUSLMS INTEGRATED ADMISSION AND UNIT NAV -->
            {% if user.is_authenticated and user.role == 'STUDENT' and not user.is_staff and not user.is_superuser %}
              <a href="{% url 'campus_admissions_units:register_units' %}">Register Units</a>
            {% elif user.is_authenticated and user.role == 'LECTURER' and not user.is_staff and not user.is_superuser %}
              <a href="{% url 'campus_admissions_units:lecturer_queue' %}">Approve Units</a>
            {% endif %}
'''
        new_base = new_base.replace('</nav>', insertion + '        </nav>', 1)

    new_home = contents[home_path]
    if '<!-- CAMPUSLMS APPLICANT FINDER -->' not in new_home:
        addition = '''<!-- CAMPUSLMS APPLICANT FINDER -->
<div style="max-width:1000px;margin:12px auto 30px;padding:0 22px;text-align:center">
  <a class="access-link" href="{% url 'campus_access:student_signup' %}">🎓 Check KCSE Points & Apply for a Programme</a>
  <p class="access-lead" style="margin-top:10px;font-size:13px">View preliminary programme matches during student signup. Final admission requires university verification.</p>
</div>
'''
        new_home = new_home.replace('{% endblock %}', addition + '{% endblock %}', 1)

    # Run an online SQLite backup; this works even if someone left the development DB in WAL mode.
    backup = Path.home() / "Documents" / ("CampusLMS_AdmissionUnits_Backup_" + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    db = ROOT / "db.sqlite3"
    if db.exists():
        try:
            with sqlite3.connect(str(db)) as source, sqlite3.connect(str(backup / "db.sqlite3")) as destination:
                source.backup(destination)
        except sqlite3.Error as exc:
            fail(f"Could not safely back up SQLite: {exc}")
    for p in contents:
        dest = backup / "original_files" / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
    print('Safety backup:', backup, flush=True)

    # Install the full academic catalogue using its own idempotent importer.
    if not (ROOT / "academics/models.py").is_file() or not (ROOT / "academics/data/university_catalogue.json").is_file():
        print('Installing complete university academic catalogue first...', flush=True)
    else:
        print('Ensuring your existing university catalogue is complete...', flush=True)
    result = subprocess.call([sys.executable, "install_full_university.py"], cwd=str(ROOT))
    if result:
        fail('Academic catalogue installer reported an error; Stage 13 app was not applied.')

    if not target.exists():
        shutil.copytree(PAYLOAD, target)
    else:
        for source in PAYLOAD.rglob('*'):
            if source.is_file():
                dest = target / source.relative_to(PAYLOAD)
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
    for path, content in {
        settings_path: new_settings, urls_path: new_urls,
        portal_urls_path: new_portal_urls, base_path: new_base, home_path: new_home,
    }.items():
        if path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")

    execute('check')
    execute('makemigrations', 'campus_admissions_units', '--noinput')
    execute('migrate', '--noinput')
    execute('seed_sample_admission_thresholds')
    execute('test', 'campus_admissions_units', '--noinput')
    print('''\nSUCCESS: Student programme matching and lecturer unit approvals are installed.
Open http://127.0.0.1:8001/ (same existing four-portal homepage)
Students: Student Sign Up now asks for grade, points and programme; login has Register Units navigation.
Lecturers: their navigation has Approve Units.
Admin: Admissions and Unit Registration section contains entry rules, applications and lecturer allocations.
All sample thresholds are illustrative and UNVERIFIED. Verify institution cutoffs and subject requirements before real admissions.
Start: python manage.py runserver 8001
''')


if __name__ == '__main__':
    main()
