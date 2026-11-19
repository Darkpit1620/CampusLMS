CampusLMS — Stage 11C Access Add-on (SAFE, ADDITIVE)
===================================================
Purpose: create dedicated student, lecturer, staff, and administrator access links.
This ZIP only adds a new campus_access/ application. It does NOT overwrite your existing accounts/, admissions/, courses/, assignments/, or dashboard/ files. Do NOT delete the database.

1) KEEP THE BACKUP YOU ALREADY MADE. Stop the Django development server (Ctrl+C).
2) Extract into the EXISTING CampusLMS project root. Use Expand-Archive from PowerShell.
3) In activated .venv, install dependencies:
   python -m pip install "django-countries>=7,<9" "phonenumbers>=9,<10"
4) Open config/settings.py, add ONE INSTALLED_APPS entry:
   "campus_access.apps.CampusAccessConfig",
5) Open config/urls.py, ensure include is imported:
   from django.urls import path, include
   Add ONE urlpatterns entry BEFORE any final catch-all path:
   path("access/", include("campus_access.urls")),
   Do not remove existing routes. Student admissions /register/ and /login/ remain available.
6) accounts/models.py must include inside User.Role:
   STAFF = "STAFF", "University Staff"
   If already present, do not duplicate. If not, add it and save.
7) One command at a time:
   python manage.py check
   python manage.py makemigrations accounts campus_access
   python manage.py migrate
   python manage.py test campus_access
   python manage.py runserver 8001
8) Open http://127.0.0.1:8001/access/
   Student signup: /access/student/signup/
   Lecturer signup: /access/lecturer/signup/
   Staff signup: /access/staff/signup/
   Student login: /access/student/login/
   Lecturer login: /access/lecturer/login/
   Staff login: /access/staff/login/
   Admin login: /admin/
9) Approve student at /admin/admissions/studentadmission/ using existing Approve action.
   Approve lecturer/staff at /admin/campus_access/employeeapplication/ using Approve selected action.
10) Lecturer and university staff use their registered EMAIL as their username, together with the password they created. Existing lecturer accounts (such as lecturer1) can continue using their old username. Automatic email/SMS delivery is NOT included.
11) For easy access from your existing homepage, optionally add:
   <a href="{% url 'campus_access:home' %}">Register / Sign in</a>
   Do not remove your old buttons until the new portal is tested.

IMPORTANT SECURITY DETAILS:
- Public ADMIN signup is intentionally NOT permitted: superusers are created/invited by existing superusers.
- University STAFF is a CampusLMS role, not Django is_staff. Staff signup never grants admin access.
- Student admission numbers are created only by the existing approval process.
- New students are inactive until approved; lecturer/staff applications are inactive until approved.
- Application pages provide no automatic email/SMS delivery or email ownership validation.
- This development system requires HTTPS, secure settings, email verification, rate limiting, and data privacy policies before production use.
- If an error occurs, DO NOT delete your db.sqlite3, do not run flush, and do not make new accounts to replace existing ones.
