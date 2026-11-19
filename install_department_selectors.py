"""Safe Stage 15 CampusLMS in-place extension; run in the existing project.

No auth model replacement, no existing user/course/grade deletion, and no
implicit authorization for lecturer teaching requests.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / '_campus_departments' / 'files' / 'campus_departments'


class SafeStop(Exception):
    pass


def require(condition, explanation):
    if not condition:
        raise SafeStop(explanation)


def add_after(text, anchor, insert, description):
    match = re.search(anchor, text, re.MULTILINE)
    require(match is not None, f'Cannot safely locate {description}; no files updated.')
    return text[:match.end()] + insert + text[match.end():]


def once_replace(text, old, new, label):
    if new in text:
        return text
    require(old in text, f'{label} differs from expected CampusLMS Stage 13. No changes made. Share {label} for merging.')
    return text.replace(old, new, 1)


def command(*args):
    cmd = [sys.executable, 'manage.py', *args]
    print('\n>>> ' + ' '.join(cmd), flush=True)
    result = subprocess.call(cmd, cwd=ROOT)
    require(result == 0, 'A Django command failed. Do NOT reset the database; share the error. A backup has been saved.')


def plan():
    paths = {
        name: ROOT / name for name in [
            'config/settings.py', 'config/urls.py',
            'campus_access/views.py',
            'campus_access/templates/campus_access/signup.html',
            'campus_admissions_units/views.py',
            'campus_admissions_units/templates/campus_admissions_units/student_signup.html',
            'dashboard/templates/dashboard/base.html',
        ]
    }
    require((ROOT / 'manage.py').is_file(), 'Run from the EXISTING CampusLMS folder (manage.py is missing).')
    for name, path in paths.items():
        require(path.is_file(), f'Missing {name}. Install the integrated Stage 13 package first.')
    require((ROOT / 'academics/models.py').is_file(), 'Academic catalogue is missing; install Stage 13 first.')
    require(PAYLOAD.is_dir() and (PAYLOAD / 'forms.py').is_file(), 'ZIP extraction incomplete. Missing Stage 15 payload.')
    target = ROOT / 'campus_departments'
    if target.exists():
        require((target / 'models.py').is_file(), 'An unrelated campus_departments folder already exists; refusing overwrite.')
        require('class LecturerUnitRequest' in (target / 'models.py').read_text(encoding='utf-8'),
                'Existing campus_departments models differ; stopping to avoid overwriting.')
        for src in PAYLOAD.rglob('*'):
            if src.is_file():
                dst = target / src.relative_to(PAYLOAD)
                require(not dst.exists() or dst.read_bytes() == src.read_bytes(),
                        f'Locally edited file {dst}. No overwrite; merge manually.')

    original = {name: path.read_text(encoding='utf-8') for name, path in paths.items()}
    updated = dict(original)
    s = updated['config/settings.py']
    if not re.search(r'''['"]campus_departments(?:\.apps\.CampusDepartmentsConfig)?['"]''', s):
        s = add_after(s, r'^INSTALLED_APPS\s*=\s*\[',
                      '\n    "campus_departments.apps.CampusDepartmentsConfig",', 'INSTALLED_APPS')
    updated['config/settings.py'] = s

    urls = updated['config/urls.py']
    if not re.search(r'^from django\.urls import .*\binclude\b', urls, re.MULTILINE):
        urls = add_after(urls, r'^from django\.urls import .+$', '\nfrom django.urls import include', 'config URL include import')
    if not re.search(r'''path\(\s*['"]department-options/['"]''', urls):
        urls = add_after(urls, r'^urlpatterns\s*=\s*\[',
                         '\n    path("department-options/", include("campus_departments.urls")),', 'config URL list')
    updated['config/urls.py'] = urls

    lecturer_view = updated['campus_access/views.py']
    if 'from campus_departments.forms import DepartmentEmployeeSignupForm' not in lecturer_view:
        lecturer_view = add_after(lecturer_view, r'^from \.forms import EmployeeSignupForm, InternationalStudentForm.*$',
                                  '\nfrom campus_departments.forms import DepartmentEmployeeSignupForm',
                                  'campus_access/views.py form import')
    lecturer_view = once_replace(
        lecturer_view,
        'form = EmployeeSignupForm(request.POST or None, requested_role=requested_role)',
        'form = DepartmentEmployeeSignupForm(request.POST or None, requested_role=requested_role)',
        'campus_access/views.py',
    )
    updated['campus_access/views.py'] = lecturer_view

    student_view = updated['campus_admissions_units/views.py']
    if 'from campus_departments.forms import DepartmentStudentSignupForm' not in student_view:
        student_view = add_after(student_view, r'^from \.forms import ApplicantSignupForm.*$',
                                 '\nfrom campus_departments.forms import DepartmentStudentSignupForm',
                                 'campus_admissions_units/views.py form import')
    student_view = once_replace(
        student_view,
        'form = ApplicantSignupForm(request.POST or None)',
        'form = DepartmentStudentSignupForm(request.POST or None)',
        'campus_admissions_units/views.py',
    )
    updated['campus_admissions_units/views.py'] = student_view

    student_html = updated['campus_admissions_units/templates/campus_admissions_units/student_signup.html']
    student_html = once_replace(
        student_html,
        "data-finder-url=\"{% url 'campus_admissions_units:programme_finder' %}\"",
        "data-finder-url=\"{% url 'campus_departments:eligible_programmes' %}\"",
        'student signup template finder URL',
    )
    student_html = once_replace(
        student_html,
        "{% static 'campus_admissions_units/programme-finder.js' %}",
        "{% static 'campus_departments/student-programme-picker.js' %}",
        'student signup JavaScript',
    )
    if "{% static 'campus_departments/department.css' %}" not in student_html:
        student_html = once_replace(
            student_html,
            "<link rel=\"stylesheet\" href=\"{% static 'campus_access/access.css' %}\">",
            "<link rel=\"stylesheet\" href=\"{% static 'campus_access/access.css' %}\">\n<link rel=\"stylesheet\" href=\"{% static 'campus_departments/department.css' %}\">",
            'student signup CSS',
        )
    student_html = once_replace(
        student_html,
        "field.name == 'programme' %}",
        "field.name == 'programme' or field.name == 'department' %}",
        'student signup department layout',
    )
    updated['campus_admissions_units/templates/campus_admissions_units/student_signup.html'] = student_html

    employee_html = updated['campus_access/templates/campus_access/signup.html']
    if "{% static 'campus_departments/department.css' %}" not in employee_html:
        employee_html = once_replace(
            employee_html,
            "<link rel=\"stylesheet\" href=\"{% static 'campus_access/access.css' %}\">",
            "<link rel=\"stylesheet\" href=\"{% static 'campus_access/access.css' %}\">\n<link rel=\"stylesheet\" href=\"{% static 'campus_departments/department.css' %}\">",
            'employee signup CSS',
        )
    employee_html = once_replace(
        employee_html,
        "field.name == 'department' or field.name == 'job_title' %}",
        "field.name == 'department' or field.name == 'job_title' or field.name == 'requested_units' %}",
        'employee signup layout',
    )
    employee_html = once_replace(
        employee_html,
        '      {{ field }}',
        "      {% if field.name == 'requested_units' %}\n"
        "        {% include 'campus_departments/unit_picker.html' %}\n"
        '      {% else %}{{ field }}{% endif %}',
        'employee signup unit picker',
    )
    if 'campus_departments/department-picker.js' not in employee_html:
        employee_html = once_replace(
            employee_html, '{% endblock %}',
            "{% if role_title == 'Lecturer' %}<script defer src=\"{% static 'campus_departments/department-picker.js' %}\"></script>{% endif %}\n{% endblock %}",
            'employee signup picker script',
        )
    updated['campus_access/templates/campus_access/signup.html'] = employee_html

    base = updated['dashboard/templates/dashboard/base.html']
    if '<!-- CAMPUSLMS STAGE15 TEACHING LINK -->' not in base:
        require('</nav>' in base, 'Cannot locate the shared navigation. No files modified.')
        nav = '''\n            <!-- CAMPUSLMS STAGE15 TEACHING LINK -->
            {% if user.is_authenticated and user.role == 'LECTURER' and not user.is_staff and not user.is_superuser %}
              <a href="{% url 'campus_departments:my_teaching' %}">My Teaching Units</a>
            {% endif %}
'''
        base = base.replace('</nav>', nav + '</nav>', 1)
    updated['dashboard/templates/dashboard/base.html'] = base
    return paths, original, updated


def install():
    paths, original, updated = plan()
    backup = Path.home() / 'Documents' / ('CampusLMS_Departments_Backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    db = ROOT / 'db.sqlite3'
    if db.exists():
        try:
            with sqlite3.connect(str(db)) as src, sqlite3.connect(str(backup / 'db.sqlite3')) as dest:
                src.backup(dest)
        except sqlite3.Error as exc:
            raise SafeStop(f'Failed to back up database; no changes made: {exc}') from exc
    for name, old in original.items():
        path = backup / 'original_files' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old, encoding='utf-8')
    print('Safety backup created:', backup, flush=True)

    target = ROOT / 'campus_departments'
    if not target.exists():
        shutil.copytree(PAYLOAD, target)
    else:
        for src in PAYLOAD.rglob('*'):
            if src.is_file():
                dst = target / src.relative_to(PAYLOAD)
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
    for name, content in updated.items():
        if content != original[name]:
            paths[name].write_text(content, encoding='utf-8')
    command('check')
    command('makemigrations', 'campus_departments', '--noinput')
    command('migrate', '--noinput')
    command('test', 'campus_departments', '--noinput')
    print('''\nSUCCESS — Department selectors and lecturer teaching requests installed.
Use the existing CampusLMS homepage at http://127.0.0.1:8001/
- Student Sign Up: choose a department, then KCSE points and matching programme.
- Lecturer Sign Up: select department and units across different years/terms.
- Staff Sign Up: choose department from the dropdown.
- Lecturer Dashboard: My Teaching Units (navigation link).
- Admin: Department and Teaching Requests -> Lecturer Unit Requests -> Approve.
Lecturer requests only become actual teaching assignments AFTER admin approval.
''', flush=True)


if __name__ == '__main__':
    try:
        install()
    except SafeStop as exc:
        raise SystemExit('STOP: ' + str(exc))
