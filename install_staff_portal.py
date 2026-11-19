#!/usr/bin/env python3
"""CampusLMS Stage 18: non-destructive university staff departments upgrade.

Run in the EXISTING CampusLMS root. Creates external SQLite backup and
original-file backups; changes no existing user model or admissions data.
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / '_stage18' / 'staff_portal'


class SafetyStop(Exception):
    pass


def need(ok, message):
    if not ok:
        raise SafetyStop(message)


def read(name):
    file = ROOT / name
    need(file.is_file(), f'Missing {name}. Install the previous CampusLMS portal first; nothing changed.')
    return file.read_text(encoding='utf-8')


def switch_route(content, old_regex, replacement, existing, label):
    if existing in content:
        return content
    changed, count = re.subn(old_regex, replacement, content, count=1)
    need(count == 1, f'Unexpected {label} route format. No files updated. Share campus_access/urls.py for a safe merge.')
    return changed


def build_plan():
    need((ROOT / 'manage.py').is_file(), 'Run from the original CampusLMS project folder (manage.py missing).')
    need(PAYLOAD.is_dir(), 'ZIP extraction incomplete; expected _stage18/staff_portal folder.')
    need((PAYLOAD / 'models.py').is_file(), 'ZIP extraction incomplete; staff models missing.')
    need((ROOT / 'campus_access/models.py').is_file(), 'Existing staff access app missing. Install portal upgrade before this.')
    need('class EmployeeApplication' in read('campus_access/models.py'), 'Missing approved EmployeeApplication model.')
    need('STAFF' in read('accounts/models.py'), 'Accounts must already support role STAFF.')

    originals = {
        name: read(name)
        for name in [
            'config/settings.py', 'campus_access/urls.py',
            'dashboard/templates/dashboard/base.html',
            'campus_access/templates/campus_access/home.html',
        ]
    }
    changed = dict(originals)
    settings = changed['config/settings.py']
    if not re.search(r'[\'\"]staff_portal(?:\.apps\.StaffPortalConfig)?[\'\"]', settings):
        settings, count = re.subn(
            r'(INSTALLED_APPS\s*=\s*\[)',
            '\\1\n    "staff_portal.apps.StaffPortalConfig",',
            settings, count=1,
        )
        need(count == 1, 'Could not locate INSTALLED_APPS. No changes made.')
    changed['config/settings.py'] = settings

    urls = changed['campus_access/urls.py']
    if 'from staff_portal import views as staff_views' not in urls:
        match = re.search(r'^from\s+\.\s+import\s+views\s*$', urls, re.MULTILINE)
        need(match is not None, 'Could not find campus_access views import. No changes made.')
        urls = urls[:match.end()] + '\nfrom staff_portal import views as staff_views' + urls[match.end():]
    urls = switch_route(
        urls,
        r'path\(\s*[\'\"]staff/signup/[\'\"]\s*,\s*views\.employee_signup\s*,\s*\{\s*[\'\"]role[\'\"]\s*:\s*[\'\"]staff[\'\"]\s*\}\s*,\s*name\s*=\s*[\'\"]staff_signup[\'\"]\s*\)',
        'path("staff/signup/", staff_views.staff_signup, name="staff_signup")',
        'staff_views.staff_signup',
        'staff signup',
    )
    urls = switch_route(
        urls,
        r'path\(\s*[\'\"]staff/workspace/[\'\"]\s*,\s*views\.staff_workspace\s*,\s*name\s*=\s*[\'\"]staff_workspace[\'\"]\s*\)',
        'path("staff/workspace/", staff_views.staff_dashboard, name="staff_workspace")',
        'staff_views.staff_dashboard',
        'staff workspace',
    )
    if 'staff_views.staff_departments' not in urls:
        urls, count = re.subn(
            r'(urlpatterns\s*=\s*\[)',
            '\\1\n    path("staff/departments/", staff_views.staff_departments, name="staff_departments"),',
            urls, count=1,
        )
        need(count == 1, 'Could not locate campus_access urlpatterns. No changes made.')
    changed['campus_access/urls.py'] = urls

    base = changed['dashboard/templates/dashboard/base.html']
    marker = '<!-- CAMPUSLMS STAGE18 STAFF DASHBOARD -->'
    if marker not in base:
        old = '<a href="{% url \'dashboard\' %}">Dashboard</a>'
        new = ('{% if user.role == \'STAFF\' %}'
               '<a href="{% url \'campus_access:staff_workspace\' %}">Staff Desk</a>'
               '{% else %}' + old + '{% endif %}')
        if old in base:
            base = base.replace(old, marker + '\n            ' + new, 1)
        else:
            need('</nav>' in base, 'Could not find navbar. No changes made.')
            extra = ('{% if user.is_authenticated and user.role == \'STAFF\' %}'
                     '<a href="{% url \'campus_access:staff_workspace\' %}">Staff Desk</a>'
                     '{% endif %}')
            base = base.replace('</nav>', marker + '\n' + extra + '\n</nav>', 1)
    changed['dashboard/templates/dashboard/base.html'] = base

    home = changed['campus_access/templates/campus_access/home.html']
    old_desc = 'Apply for a university employee account and access approved functions.'
    if old_desc in home:
        home = home.replace(
            old_desc,
            'Join university teams in HR, Games and Sports, Transport, Finance, ICT, Library, teaching support, and more.',
            1,
        )
    changed['campus_access/templates/campus_access/home.html'] = home

    for src in PAYLOAD.rglob('*'):
        if not src.is_file() or '__pycache__' in src.parts:
            continue
        dest = 'staff_portal/' + str(src.relative_to(PAYLOAD)).replace('\\', '/')
        content = src.read_text(encoding='utf-8')
        if (ROOT / dest).exists():
            need((ROOT / dest).read_text(encoding='utf-8') == content,
                 f'Already installed staff file locally changed: {dest}. No overwrite; ask for an adapted patch.')
        changed[dest] = content
    return changed


def backup_sqlite(source, dest):
    if not source.exists():
        return
    try:
        with sqlite3.connect(str(source)) as conn_src, sqlite3.connect(str(dest)) as conn_dest:
            conn_src.backup(conn_dest)
    except sqlite3.Error as exc:
        raise SafetyStop(f'SQLite backup failed; nothing changed: {exc}') from exc


def run(*args):
    print('>>> python manage.py ' + ' '.join(args), flush=True)
    result = subprocess.call([sys.executable, 'manage.py', *args], cwd=ROOT)
    need(result == 0, 'A Django step failed. Do not delete your database. Share the full terminal error and backup path.')


def install():
    plan = build_plan()  # Fail safely before writing.
    backup = Path.home() / 'Documents' / ('CampusLMS_StaffBackup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    backup_sqlite(ROOT / 'db.sqlite3', backup / 'db.sqlite3')
    for rel in plan:
        existing = ROOT / rel
        if existing.is_file():
            destination = backup / 'original_files' / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(existing, destination)
    print('Safety backup:', backup, flush=True)
    for rel, content in plan.items():
        target = ROOT / rel
        if target.exists() and target.read_text(encoding='utf-8') == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.staff_upgrade.tmp')
        try:
            temp.write_text(content, encoding='utf-8')
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
        print('Updated:', rel, flush=True)

    run('check')
    run('makemigrations', 'staff_portal', '--noinput')
    run('migrate', '--noinput')
    run('seed_staff_departments')
    run('test', 'staff_portal', '--noinput')
    print('''\nSTAGE 18 INSTALLED.\nStart: python manage.py runserver 8001\nMain portal: http://127.0.0.1:8001/\nChoose Staff Sign Up -> Staff Category -> Department -> Submit.\nAdmin approves the EmployeeApplication; approval email uses existing settings.\nApproved staff sign in via Staff Login -> Staff Desk.\nAdmin may designate Department Head in Staff Profiles.\nExisting lecturer and student workflows are unchanged.\n''', flush=True)


if __name__ == '__main__':
    try:
        install()
    except SafetyStop as error:
        raise SystemExit('SAFETY STOP: ' + str(error))
