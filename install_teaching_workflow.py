#!/usr/bin/env python
"""CampusLMS Stage 17 — conservative installer. Run in the CampusLMS root.

The installer never deletes data; it checks expected source layouts up-front,
creates a SQLite-consistent backup, and updates only the listed files.
"""
from pathlib import Path
from datetime import datetime
import os
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / '_stage17' / 'campus_teaching'


class SafeStop(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise SafeStop(reason)


def read(path):
    file = ROOT / path
    require(file.is_file(), f'Missing expected CampusLMS file: {path}. Nothing modified.')
    return file.read_text(encoding='utf-8')


def changed_role_guards(relative_path, code):
    if relative_path == 'campus_admissions_units/views.py':
        old = 'request.user.role != role or request.user.is_staff or request.user.is_superuser'
        new = 'request.user.role != role or not request.user.is_active or request.user.is_superuser'
    elif relative_path == 'campus_departments/views.py':
        old = "user.role != 'LECTURER' or not user.is_active or user.is_staff or user.is_superuser"
        new = "user.role != 'LECTURER' or not user.is_active or user.is_superuser"
    elif relative_path == 'campus_access/views.py':
        old = 'person.role != required or person.is_superuser or person.is_staff'
        new = 'person.role != required or person.is_superuser'
    else:
        return code
    # Already upgraded? Retain local code as is.
    if old in code:
        code = code.replace(old, new, 1)
    elif new not in code:
        raise SafeStop(f'Unexpected auth layout in {relative_path}. Nothing modified. Share that file for a tailored patch.')
    if relative_path == 'campus_access/views.py':
        code = code.replace('request.user.role != "STAFF" or request.user.is_staff or request.user.is_superuser',
                            'request.user.role != "STAFF" or not request.user.is_active or request.user.is_superuser', 1)
    return code


def plan():
    require((ROOT/'manage.py').is_file(), 'Run this installer from your CampusLMS project root.')
    require(SOURCE.is_dir(), 'Missing _stage17/campus_teaching assets. Extract the complete ZIP first.')
    required = [
        'config/settings.py', 'config/urls.py',
        'dashboard/templates/dashboard/base.html',
        'dashboard/templates/dashboard/role_dashboard.html',
        'campus_departments/models.py',
        'campus_departments/views.py',
        'campus_admissions_units/views.py',
        'campus_access/views.py',
    ]
    plan = {path: read(path) for path in required}

    # Strict source checks prevent partial or destructive modifications when
    # a locally customized project no longer matches the installed add-ons.
    settings = plan['config/settings.py']
    if '"campus_teaching.apps.CampusTeachingConfig"' not in settings and "'campus_teaching.apps.CampusTeachingConfig'" not in settings:
        settings, n = re.subn(r'(INSTALLED_APPS\s*=\s*\[)', r'\1\n    "campus_teaching.apps.CampusTeachingConfig",', settings, count=1)
        require(n == 1, 'Could not locate INSTALLED_APPS in config/settings.py.')
    plan['config/settings.py'] = settings

    routes = plan['config/urls.py']
    require(re.search(r'from\s+django\.urls\s+import\s+[^\n]*\binclude\b', routes),
            'config/urls.py must import include from django.urls. Nothing modified.')
    if 'include("campus_teaching.urls")' not in routes and "include('campus_teaching.urls')" not in routes:
        routes, n = re.subn(r'(urlpatterns\s*=\s*\[)',
                            r'\1\n    path("teaching/", include("campus_teaching.urls")),', routes, count=1)
        require(n == 1, 'Could not locate urlpatterns in config/urls.py.')
    # The old /lecturer/ address gave a 404. Keep it as a safe alias for the
    # teaching dashboard, without changing any /lecturer/reports/ route.
    if not re.search(r"path\([\'\"]lecturer/[\'\"]", routes):
        if 'from django.views.generic.base import RedirectView' not in routes:
            routes = 'from django.views.generic.base import RedirectView\n' + routes
        routes, n = re.subn(r'(urlpatterns\s*=\s*\[)',
                            r'\1\n    path("lecturer/", RedirectView.as_view(pattern_name="campus_teaching:dashboard", permanent=False), name="lecturer_home"),',
                            routes, count=1)
        require(n == 1, 'Cannot add legacy lecturer URL alias.')
    plan['config/urls.py'] = routes

    base = plan['dashboard/templates/dashboard/base.html']
    if 'campus_teaching:dashboard' not in base:
        nav = '''          {% if user.is_authenticated and user.role == 'LECTURER' and not user.is_superuser %}
            <a href="{% url 'campus_teaching:dashboard' %}">Teaching Units</a>
          {% endif %}
'''
        require('</nav>' in base, 'Could not find navbar </nav> in dashboard/base.html.')
        base = base.replace('</nav>', nav + '        </nav>', 1)
    plan['dashboard/templates/dashboard/base.html'] = base

    dash = plan['dashboard/templates/dashboard/role_dashboard.html']
    if 'campus_teaching:dashboard' not in dash:
        marker = '''
{% if user.role == 'LECTURER' and not user.is_superuser %}
<section style="max-width:1050px;margin:25px auto;padding:0 24px">
  <div style="border:1px solid var(--stroke,#47527a);border-radius:18px;background:var(--surface,#1c2746);padding:22px">
    <h2 style="margin:0 0 10px">Your approved teaching units</h2>
    <p style="color:var(--ink-soft,#b9c1df)">Open your assigned units to upload notes, create assignments and review students' unit registrations.</p>
    <a href="{% url 'campus_teaching:dashboard' %}" class="btn btn-primary">Open My Teaching Units →</a>
  </div>
</section>
{% endif %}
'''
        i = dash.rfind('{% endblock %}')
        require(i > 0, 'Could not find the ending Django template block in role_dashboard.html.')
        dash = dash[:i] + marker + '\n' + dash[i:]
    # Redirect lecturer cards that used to open an unauthorized legacy course
    # list. Student course links retain their current destination.
    old_course_url = "{% url 'courses:my_courses' %}"
    if old_course_url in dash:
        if 'campus_teaching_course_url' not in dash:
            anchor = '{% block content %}'
            require(anchor in dash, 'Missing dashboard content block.')
            choose = "{% if user.role == 'LECTURER' %}{% url 'campus_teaching:dashboard' as campus_teaching_course_url %}{% else %}{% url 'courses:my_courses' as campus_teaching_course_url %}{% endif %}"
            dash = dash.replace(anchor, anchor + '\n' + choose + '\n', 1)
        dash = dash.replace(old_course_url, '{{ campus_teaching_course_url }}')
    plan['dashboard/templates/dashboard/role_dashboard.html'] = dash

    for path in ('campus_departments/views.py', 'campus_admissions_units/views.py', 'campus_access/views.py'):
        plan[path] = changed_role_guards(path, plan[path])

    model = plan['campus_departments/models.py']
    sync_stmt = '''        # Stage 17: explicitly connect the approved unit to a lecturer-owned
        # teaching Course before committing administrator approval.
        from campus_teaching.services import ensure_teaching_course
        ensure_teaching_course(placement, record.lecturer)
'''
    if 'ensure_teaching_course(placement, record.lecturer)' not in model:
        anchor = '''        record.status = self.Status.APPROVED'''
        require(anchor in model and 'def approve(self, administrator)' in model,
                'Could not safely locate lecturer unit approval in campus_departments/models.py.')
        model = model.replace(anchor, sync_stmt + anchor, 1)
    plan['campus_departments/models.py'] = model

    # Check for conflicting pre-existing app. We never overwrite a customized
    # or different version of the same teaching app.
    for src in SOURCE.rglob('*'):
        if not src.is_file() or '__pycache__' in src.parts:
            continue
        dst = 'campus_teaching/' + str(src.relative_to(SOURCE)).replace('\\', '/')
        exists = ROOT/dst
        updated = src.read_text(encoding='utf-8')
        if exists.exists() and exists.read_text(encoding='utf-8') != updated:
            raise SafeStop(f'Customized teaching module already exists: {dst}. No changes made.')
        plan[dst] = updated
    return plan


def backup_sqlite(source, target):
    if source.exists():
        try:
            with sqlite3.connect(str(source)) as origin, sqlite3.connect(str(target)) as destination:
                origin.backup(destination)
        except sqlite3.Error as error:
            raise SafeStop('Database backup failed. No files were modified: ' + str(error)) from error


def install():
    files = plan()
    folder = Path.home()/'Documents'/('CampusLMS_Stage17_Backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True, exist_ok=False)
    backup_sqlite(ROOT/'db.sqlite3', folder/'db.sqlite3')
    for dest in files:
        target = ROOT/dest
        if target.is_file():
            old_copy = folder/'original_files'/dest
            old_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, old_copy)
    print('Verified backup:', folder, flush=True)
    for dest, content in files.items():
        target = ROOT/dest
        if target.is_file() and target.read_text(encoding='utf-8') == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_name(target.name + '.stage17.tmp')
        try:
            staged.write_text(content, encoding='utf-8')
            os.replace(staged, target)
        finally:
            if staged.exists(): staged.unlink()
        print('Updated:', dest, flush=True)

    for cmd in (['check'], ['test','campus_teaching','--noinput'], ['sync_teaching_courses']):
        print('>>> python manage.py', ' '.join(cmd), flush=True)
        result = subprocess.call([sys.executable, 'manage.py', *cmd], cwd=ROOT)
        if result:
            raise SafeStop('The Django step failed. Do not delete data or rerun migrations. Share the full terminal error and the backup path.')
    print('''
INSTALLATION COMPLETE.
1) Restart Django: python manage.py runserver 8001
2) Open the main homepage, sign in as lecturer, select Teaching Units.
3) Admin: approve lecturer account AND selected teaching-unit requests.
4) Lecturer: open unit -> Upload Learning Material / Create Assignment.
5) Student: Register Units -> lecturer approves in Unit Approval Requests.
If an existing URL still shows 403, copy its exact URL and traceback: do NOT disable authorization checks.
''', flush=True)


if __name__ == '__main__':
    try:
        install()
    except SafeStop as exc:
        raise SystemExit('SAFETY STOP: ' + str(exc))
