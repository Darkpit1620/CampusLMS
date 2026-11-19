CampusLMS — Colorful UI Makeover (November 2026)
================================================

WHAT IT CHANGES
---------------
One shared CSS file and 12 Django HTML templates:
- homepage
- login
- lecturer, student, and administrator dashboards
- course list, course details, lecturer upload form
- assignment list, assignment creation, student submission form
- lecturer submission review and grading screens

WHAT IT DOES NOT CHANGE
-----------------------
No changes to Python views, models, migration files, users, passwords,
course records, uploaded learning material, or SQLite database.

IMPORTANT BEFORE INSTALLING
---------------------------
If your CampusLMS still shows the SyntaxError on line 181 of
assignments/views.py, the visual redesign cannot fix it. Finish correcting
the "grade" entry inside the render() context dictionary as previously
explained, then run:
    python -m py_compile assignments/views.py
    python manage.py check

INSTALLATION IN WINDOWS POWERSHELL / VS CODE
---------------------------------------------
1. Stop any running CampusLMS server with Ctrl+C.
2. Open your CampusLMS folder:
   cd "C:\Users\USER\Documents\assignment\New folder\CampusLMS"
3. Back up existing code (run these two commands separately):
   New-Item -ItemType Directory -Path .\UI_Backup -Force
   Copy-Item -Path .\accounts,.\dashboard,.\courses,.\assignments -Destination .\UI_Backup -Recurse -Force
4. Download CampusLMS_Colorful_UI_Pack.zip to your Windows Downloads folder.
5. Extract the zip into your CampusLMS ROOT folder (where manage.py lives):
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\CampusLMS_Colorful_UI_Pack.zip" -DestinationPath . -Force
6. Your virtual environment should still be .venv; activate if needed:
   .\.venv\Scripts\Activate.ps1
7. Check and start:
   python manage.py check
   python manage.py runserver 8001
8. Visit http://127.0.0.1:8001/ and refresh with Ctrl+F5.

NOTE: No extra pip packages or migrations required for the UI itself.

To inspect the design WITHOUT Django, open PREVIEW_Home.html and
PREVIEW_Dashboard.html from the extracted directory. They are static mockups,
not live app pages, and contain example text only.

The design links to EXISTING named Django URLs including:
    home, login, logout, dashboard
    courses:my_courses, courses:course_detail,
    courses:upload_material, courses:download_material
    assignments:course_assignments, assignments:create_assignment,
    assignments:submit_assignment
    assignments:assignment_submissions,
    assignments:download_submission, assignments:grade_submission
    admin:index, admin:accounts_user_changelist,
    admin:courses_course_changelist

Some links require the matching views and URLs to be implemented.
The optional grade/review links are hidden if those names are not yet
registered. Authentication and permissions remain controlled by Python,
not the UI templates.

Security: This redesign does NOT make file uploads safe or harden your
server for production. Continue using a local-only development server
until file validation, authorisation, secret management and deployment
security are verified.
