"""CampusLMS Stage 16: safer dropdown/semester UI patch (no schema changes).

Run from existing CampusLMS after extracting ZIP. All edits are narrow, backed up,
and idempotent. Do not reinstall/migrate users or existing student records.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SRC = ROOT / '_stage16' / 'campus_departments'

class SafeStop(Exception):
    pass

def require(ok: bool, msg: str) -> None:
    if not ok:
        raise SafeStop(msg)

def read(relative: str) -> str:
    p = ROOT / relative
    require(p.is_file(), f'Missing {relative}. Install Stage 15 first and keep this project unchanged.')
    return p.read_text(encoding='utf-8')

def insert_after(s: str, anchor: str, content: str, label: str) -> str:
    require(anchor in s, f'Cannot find the expected {label}; no files modified.')
    return s.replace(anchor, anchor + content, 1)

def append_to_content(s: str, snippet: str, sentinel: str, label: str) -> str:
    if sentinel in s:
        return s
    idx = s.rfind('{% endblock %}')
    require(idx >= 0, f'Missing closing template block in {label}; no files modified.')
    return s[:idx] + snippet + '\n' + s[idx:]

def plan():
    require((ROOT/'manage.py').is_file(), 'Run in the original CampusLMS folder containing manage.py.')
    required = [
        'campus_departments/views.py',
        'campus_departments/templates/campus_departments/unit_picker.html',
        'campus_departments/static/campus_departments/department-picker.js',
        'campus_access/templates/campus_access/signup.html',
        'campus_admissions_units/templates/campus_admissions_units/student_signup.html',
        'campus_admissions_units/templates/campus_admissions_units/student_units.html',
    ]
    originals = {p: read(p) for p in required}
    out = dict(originals)
    require('data-cd-unit-picker' in originals[required[1]],
            'Current unit picker differs from CampusLMS Stage 15. No files changed.')
    require('def unit_options(' in originals[required[0]],
            'Missing Stage 15 department endpoint. No files changed.')
    require('class="cu-grid"' in originals[required[-1]],
            'Student registration page differs from Stage 13. No files changed.')

    # Provide programme_id so student previews use an exact validated programme PK.
    api = out['campus_departments/views.py']
    if "'programme_id': placement.programme_id" not in api:
        anchor = "        'programme': f'{placement.programme.code} — {placement.programme.name}',"
        require(anchor in api, 'Department API layout changed. No files modified.')
        api = insert_after(api, anchor,
                           "\n        'programme_id': placement.programme_id, 'required': placement.required,",
                           'department API')
    out['campus_departments/views.py'] = api

    # Fix the Stage 15 bug: script was inserted inside block TITLE, not block CONTENT.
    employee = out['campus_access/templates/campus_access/signup.html']
    script = "{% if role_title == 'Lecturer' %}<script defer src=\"{% static 'campus_departments/department-picker.js' %}\"></script>{% endif %}"
    title = re.search(r'\{% block title %\}.*?\{% endblock %\}', employee, flags=re.DOTALL)
    require(title, 'Employee signup title block not found. No files changed.')
    if script in title.group():
        employee = employee.replace(script, '', 1)
    # Remove any double script reference only from title, don't touch other scripts.
    employee = append_to_content(employee,
                                 f'\n{script}\n',
                                 "<script defer src=\"{% static 'campus_departments/department-picker.js' %}\"></script>{% endif %}\n{% endblock %}",
                                 'lecturer signup') if script not in employee[employee.find('{% block content %}'): ] else employee
    # More explicit idempotence for title-only migration.
    content_start = employee.find('{% block content %}')
    require(content_start >= 0, 'Employee signup content block missing.')
    if script not in employee[content_start:]:
        employee = append_to_content(employee, '\n' + script + '\n',
                                     'data-cd-unit-picker-boot', 'employee signup')
    if "stage16.css" not in employee:
        employee = insert_after(employee,
            '<link rel="stylesheet" href="{% static \'campus_departments/department.css\' %}">',
            '\n<link rel="stylesheet" href="{% static \'campus_departments/stage16.css\' %}">', 'employee CSS')
    out['campus_access/templates/campus_access/signup.html'] = employee

    student = out['campus_admissions_units/templates/campus_admissions_units/student_signup.html']
    if 'data-s16-student-preview' not in student:
        anchor = '      <div class="cu-match" id="cu-results"'
        require(anchor in student, 'Student signup results section not found. No files changed.')
        snippet = '''      <details class="s16-student-preview" data-s16-student-preview
          data-units-url="{% url 'campus_departments:unit_options' %}" open>
        <summary data-s16-unit-heading>Year 1 · Semester 1 units</summary>
        <div data-s16-unit-list>Choose a department and eligible programme above to preview the first-semester units.</div>
        <small>These units are a preview only. After administrator approval, students register all required units for their assigned semester in the Student Dashboard.</small>
      </details>
'''
        student = student.replace(anchor, snippet + anchor, 1)
    if "stage16.css" not in student:
        student = insert_after(student,
            '<link rel="stylesheet" href="{% static \'campus_departments/department.css\' %}">',
            '\n<link rel="stylesheet" href="{% static \'campus_departments/stage16.css\' %}">', 'student signup CSS')
    if "student-unit-preview.js" not in student:
        student = append_to_content(student,
            '<script defer src="{% static \'campus_departments/student-unit-preview.js\' %}"></script>\n',
            'student-unit-preview.js', 'student signup JS')
    out['campus_admissions_units/templates/campus_admissions_units/student_signup.html'] = student

    units = out['campus_admissions_units/templates/campus_admissions_units/student_units.html']
    if "stage16.css" not in units:
        units = insert_after(units,
            '<link rel="stylesheet" href="{% static \'campus_admissions_units/admission-units.css\' %}">',
            '\n<link rel="stylesheet" href="{% static \'campus_departments/stage16.css\' %}">', 'student semester CSS')
    if 'class="s16-student-semester"' not in units:
        toolbar = '<div class="cu-toolbar"><button class="cu-mini" type="button" onclick="document.querySelectorAll(\'[name=units]\').forEach(e=>e.checked=true)">Select all units</button><span>Choose units for the current semester</span></div>'
        require(toolbar in units, 'Student unit toolbar differs. No files modified.')
        units = insert_after(units, toolbar,
            '\n      <details class="s16-student-semester" open>\n'
            '        <summary>All {{ rows|length }} units for {{ record.programme.code }} · Year {{ record.current_year }}, Semester {{ record.current_semester }} (expand/collapse)</summary>',
            'student semester unit dropdown')
        closing = '''      </div>
      <button type="submit" class="cu-button cu-submit"'''
        require(closing in units, 'Student unit list closing section differs. No files modified.')
        units = units.replace(closing,
            '      </div>\n      </details>\n      <button type="submit" class="cu-button cu-submit"', 1)
    out['campus_admissions_units/templates/campus_admissions_units/student_units.html'] = units

    # Copy replacement components plus new assets and tests after backing up originals.
    replacements = {
      'campus_departments/static/campus_departments/department-picker.js': SRC/'static/campus_departments/department-picker.js',
      'campus_departments/templates/campus_departments/unit_picker.html': SRC/'templates/campus_departments/unit_picker.html',
    }
    for dst, source in replacements.items():
        require(source.is_file(), f'ZIP missing {source.name}.')
        out[dst] = source.read_text(encoding='utf-8')
    for dst, source in {
       'campus_departments/static/campus_departments/student-unit-preview.js': SRC/'static/campus_departments/student-unit-preview.js',
       'campus_departments/static/campus_departments/stage16.css': SRC/'static/campus_departments/stage16.css',
       'campus_departments/test_stage16.py': SRC/'test_stage16.py',
    }.items():
        require(source.is_file(), f'ZIP missing {source.name}.')
        new = source.read_text(encoding='utf-8')
        if (ROOT/dst).exists():
            require((ROOT/dst).read_text(encoding='utf-8') == new,
                    f'Existing Stage 16 asset has local changes: {dst}. No files modified.')
        out[dst] = new
    return out

def install():
    out = plan()   # All preconditions before altering a file.
    backup = Path.home()/'Documents'/('CampusLMS_Stage16_Backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    db = ROOT/'db.sqlite3'
    if db.is_file():
        try:
            with sqlite3.connect(str(db)) as source, sqlite3.connect(str(backup/'db.sqlite3')) as dest:
                source.backup(dest)
        except sqlite3.Error as error:
            raise SafeStop(f'Backup failed: {error}; no project files were changed.') from error
    for dst in out:
        target = ROOT/dst
        if target.is_file():
            p = backup/'original_files'/dst
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, p)
    print('Backup saved at:', backup, flush=True)
    for dst, updated in out.items():
        target = ROOT/dst
        if target.is_file() and target.read_text(encoding='utf-8') == updated:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name+'.stage16.tmp')
        try:
            tmp.write_text(updated, encoding='utf-8')
            os.replace(tmp, target)
        finally:
            if tmp.exists(): tmp.unlink()
        print('Updated:', dst, flush=True)
    for command in [('check',), ('test','campus_departments','--noinput')]:
        print('>>> python manage.py ' + ' '.join(command), flush=True)
        code = subprocess.call([sys.executable, 'manage.py', *command], cwd=ROOT)
        if code:
            raise SafeStop('Django checks/tests failed. Do not reset the database. Share the error and restore the backed-up templates if needed.')
    print('''
SUCCESS. Stage 16 installed; no migrations were needed.
Refresh CampusLMS with Ctrl+F5.
Lecturer signup: department -> programme/year/semester -> dropdown -> selected teaching units.
Student signup: department -> eligible programme -> Year 1 Semester 1 unit preview.
Student Dashboard: Register Units -> all current semester units selected for lecturer approval.
Lecturer Dashboard: My Teaching Units -> request selected units; admin review still required.
''', flush=True)

if __name__ == '__main__':
    try: install()
    except SafeStop as error: raise SystemExit('STOP: ' + str(error))
