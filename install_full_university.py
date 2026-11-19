"""One-command CampusLMS academic catalogue installation.

Run in original CampusLMS folder:
    python install_full_university.py

Safe re-runs: does not drop tables, overwrite models, or duplicate catalogue rows.
Makes an external SQLite and code backup first.
"""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "_campus_academics" / "files" / "academics"


def stop(message):
    raise SystemExit("STOP: " + message)


def copy_if_missing(source, target):
    if target.exists():
        if target.read_bytes() != source.read_bytes():
            stop(f"Existing custom file differs: {target}. Nothing overwritten. Ask for a safe merge.")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def check_commands():
    commands = [
        ["manage.py", "check"],
        ["manage.py", "makemigrations", "academics", "--noinput"],
        ["manage.py", "migrate", "--noinput"],
        ["manage.py", "seed_university_catalogue"],
        ["manage.py", "test", "academics", "--noinput"],
    ]
    for args in commands:
        command = [sys.executable, *args]
        print("\n>>> ", " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            stop(
                "Command above failed. Existing data remains in place. "
                "Review the error before running the installer again."
            )


def main():
    print("\nCampusLMS: Complete University Curriculum — 16 programmes, 840 units")
    needed = [
        "manage.py", "config/settings.py", "config/urls.py",
        "dashboard/templates/dashboard/base.html", "courses/models.py",
    ]
    for name in needed:
        if not (ROOT / name).is_file():
            stop(f"Missing {name}. Extract ZIP into your original CampusLMS project folder.")
    if not (PAYLOAD / "data" / "university_catalogue.json").is_file():
        stop("Missing source curriculum data. Re-extract the complete ZIP.")

    settings_file = ROOT / "config" / "settings.py"
    urls_file = ROOT / "config" / "urls.py"
    base_file = ROOT / "dashboard" / "templates" / "dashboard" / "base.html"
    portal_home = ROOT / "campus_access" / "templates" / "campus_access" / "home.html"
    settings = settings_file.read_text(encoding="utf-8")
    urls = urls_file.read_text(encoding="utf-8")
    base = base_file.read_text(encoding="utf-8")
    if not re.search(r"^INSTALLED_APPS\s*=\s*\[", settings, re.M):
        stop("Cannot safely identify INSTALLED_APPS in settings.py")
    if not re.search(r"^urlpatterns\s*=\s*\[", urls, re.M):
        stop("Cannot safely identify urlpatterns in config/urls.py")
    if not re.search(r"^from django\.urls import .*\bpath\b", urls, re.M):
        stop("config/urls.py needs a normal 'from django.urls import path' import")
    target = ROOT / "academics"
    if target.exists():
        model_file = target / "models.py"
        if not model_file.is_file() or not all(
            pattern in model_file.read_text(encoding="utf-8")
            for pattern in ("class Programme(", "class Unit(", "class ProgrammeUnit(", "class StudentProgramme(")
        ):
            stop("Found an incompatible existing academics folder; no files changed.")
        for relative in (
            "data/university_catalogue.json",
            "management/commands/seed_university_catalogue.py",
            "test_catalogue.py",
        ):
            source, dest = PAYLOAD / relative, target / relative
            if dest.exists() and dest.read_bytes() != source.read_bytes():
                stop(f"Existing {relative} differs from this installer. No files overwritten.")

    # Patch only missing routing/app registration, never replace old routing.
    new_settings = settings
    if not re.search(r"['\"]academics(?:\.apps\.AcademicsConfig)?['\"]", new_settings):
        new_settings = re.sub(
            r"^INSTALLED_APPS\s*=\s*\[",
            lambda m: m.group(0) + '\n    "academics.apps.AcademicsConfig",',
            new_settings, count=1, flags=re.M,
        )
    new_urls = urls
    if not re.search(r"^from django\.urls import .*\binclude\b", new_urls, re.M):
        new_urls = re.sub(
            r"^from django\.urls import .*?$",
            lambda m: m.group(0) + "\nfrom django.urls import include",
            new_urls, count=1, flags=re.M,
        )
    if not re.search(r"path\(\s*['\"]academics/['\"]", new_urls):
        new_urls = re.sub(
            r"^urlpatterns\s*=\s*\[",
            lambda m: m.group(0) + '\n    path("academics/", include("academics.urls")),',
            new_urls, count=1, flags=re.M,
        )

    new_base = base
    marker = "<!-- CAMPUSLMS MY UNITS NAV -->"
    needle = '<a href="{% url \'dashboard\' %}">Dashboard</a>'
    if marker not in base and needle in base:
        new_base = base.replace(
            needle, needle + f'''\n            {marker}
            {{% if user.is_authenticated and user.role == "STUDENT" and not user.is_staff and not user.is_superuser %}}
              <a href="{{% url 'academics:my_units' %}}">My Units</a>
            {{% endif %}}''', 1
        )
    new_home = None
    if portal_home.is_file():
        home = portal_home.read_text(encoding="utf-8")
        if "CAMPUSLMS ACADEMICS LINK" not in home and "{% endblock %}" in home:
            new_home = home.replace("{% endblock %}", '''<!-- CAMPUSLMS ACADEMICS LINK -->
<div style="max-width:1120px;margin:8px auto 40px;padding:0 24px;text-align:center">
<a class="access-link" style="display:inline-block;max-width:350px" href="{% url 'academics:programme_list' %}">Explore University Programmes</a>
</div>
{% endblock %}''', 1)

    # Backup the database and every file we might patch before changing anything.
    backup_dir = Path.home() / "Documents" / ("CampusLMS_FullCatalogue_Backup_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    backup_dir.mkdir(parents=True, exist_ok=False)
    db_file = ROOT / "db.sqlite3"
    if db_file.exists():
        try:
            with sqlite3.connect(str(db_file)) as src, sqlite3.connect(str(backup_dir / "db.sqlite3")) as dest:
                src.backup(dest)
        except sqlite3.Error as exc:
            stop(f"Could not create SQLite backup: {exc}")
    for src in (settings_file, urls_file, base_file, portal_home):
        if src.is_file():
            dest = backup_dir / "original_files" / src.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    if not target.exists():
        shutil.copytree(PAYLOAD, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print("Academic structure installed.")
    else:
        print("Existing academic structure detected; models, templates and prior migrations retained.")
        for relative in (
            "data/university_catalogue.json",
            "management/commands/seed_university_catalogue.py",
            "test_catalogue.py",
        ):
            copy_if_missing(PAYLOAD / relative, target / relative)
        print("Added expanded curriculum data and seed command only.")
    if new_settings != settings:
        settings_file.write_text(new_settings, encoding="utf-8")
    if new_urls != urls:
        urls_file.write_text(new_urls, encoding="utf-8")
    if new_base != base:
        base_file.write_text(new_base, encoding="utf-8")
    if new_home is not None:
        portal_home.write_text(new_home, encoding="utf-8")
    print("Safety backup:", backup_dir)
    print("No users, submissions, grades, enrolments or learning materials deleted.")
    check_commands()
    print("\nSUCCESS: Sample university academic catalogue installed and checked.")
    print("View: http://127.0.0.1:8001/academics/programmes/")
    print("Admin: http://127.0.0.1:8001/admin/")
    print("Students: http://127.0.0.1:8001/academics/my-units/")
    print("Start server: python manage.py runserver 8001")
    print("Review curricula in Admin before treating them as official university requirements.")


if __name__ == "__main__":
    main()
