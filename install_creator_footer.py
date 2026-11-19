"""Add a creator credit to the existing CampusLMS shared footer.

No Django model or database changes. Safe to rerun.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / 'dashboard' / 'templates' / 'dashboard' / 'base.html'
CSS_START = '<!-- CAMPUSLMS_CREATOR_CSS_START -->'
CSS_END = '<!-- CAMPUSLMS_CREATOR_CSS_END -->'
CREDIT_START = '<!-- CAMPUSLMS_CREATOR_CREDIT_START -->'
CREDIT_END = '<!-- CAMPUSLMS_CREATOR_CREDIT_END -->'

CSS = '''<!-- CAMPUSLMS_CREATOR_CSS_START -->
<style>
  .campus-creator-credit { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 6px 10px; margin-top: 10px; font-size: 13px; line-height: 1.7; color: var(--ink-soft, #667085); }
  .campus-creator-credit .creator-name { font-weight: 800; color: var(--ink, #172044); }
  .campus-creator-credit a { font-weight: 750; color: var(--purple, #6857f6); text-decoration: underline; text-underline-offset: 3px; }
  .campus-creator-credit a:hover, .campus-creator-credit a:focus-visible { opacity: .8; }
</style>
<!-- CAMPUSLMS_CREATOR_CSS_END -->'''


def remove_marked(source: str, start: str, end: str) -> str:
    pattern = re.compile(r'\s*' + re.escape(start) + r'.*?' + re.escape(end), re.S)
    return pattern.sub('', source)


def ask_value(prompt: str, default: str = '') -> str:
    try:
        value = input(prompt).strip()
    except EOFError:
        return default
    return value or default


def install(name: str, email: str):
    if not TEMPLATE.is_file():
        print('ERROR: Could not find dashboard/templates/dashboard/base.html.')
        print('Extract this ZIP into your existing CampusLMS folder first.')
        sys.exit(1)
    if not name.strip() or len(name) > 100:
        sys.exit('ERROR: Creator name must contain 1-100 characters.')
    email = email.strip()
    if email and not re.fullmatch(r'[^\s@<>"\']+@[^\s@<>"\']+\.[A-Za-z]{2,}', email):
        sys.exit('ERROR: Please enter a full valid email address, or leave it blank.')

    original = TEMPLATE.read_text(encoding='utf-8')
    if '</head>' not in original or '</body>' not in original:
        sys.exit('ERROR: The base.html layout is unusual; no changes made.')
    new = remove_marked(original, CSS_START, CSS_END)
    new = remove_marked(new, CREDIT_START, CREDIT_END)
    new = new.replace('</head>', CSS + '\n</head>', 1)

    safe_name = escape(name.strip())
    contact_html = (
        '<span aria-hidden="true">·</span> '
        '<a href="mailto:' + escape(email, quote=True) + '">Email the creator</a>'
        if email else ''
    )
    credit = (
        '\n    ' + CREDIT_START + '\n'
        '    <div class="campus-creator-credit">'
        '<span>Created by <span class="creator-name">' + safe_name + '</span></span>'
        + contact_html + '</div>\n'
        '    ' + CREDIT_END + '\n'
    )
    if re.search(r'</footer\s*>', new, flags=re.I):
        new, count = re.subn(r'</footer\s*>', lambda _: credit + '  </footer>', new, count=1, flags=re.I)
    else:
        new = new.replace('</body>', '<footer class="footer">' + credit + '</footer>\n</body>', 1)

    if new == original:
        print('No changes necessary.')
        return
    backup_dir = ROOT / 'creator_footer_backups'
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = backup_dir / f'base_before_creator_footer_{timestamp}.html'
    shutil.copy2(TEMPLATE, backup)
    TEMPLATE.write_text(new, encoding='utf-8')
    print('SUCCESS: Creator credit installed in the shared footer.')
    print('Creator:', name)
    print('Contact email:', email or '(not supplied; contact link hidden)')
    print('Backup:', backup)
    print('Database, models, migrations, and user accounts: unchanged.')


def main():
    parser = argparse.ArgumentParser(description='Add a safe creator footer to CampusLMS.')
    parser.add_argument('--name', help='Footer creator name (default: Lance Baraka)')
    parser.add_argument('--email', help='Full contact email address for the mailto link')
    args = parser.parse_args()
    name = args.name or ask_value('Name to display [Lance Baraka]: ', 'Lance Baraka')
    email = args.email if args.email is not None else ask_value('Contact email (optional, Enter to skip): ')
    install(name, email)


if __name__ == '__main__':
    main()
