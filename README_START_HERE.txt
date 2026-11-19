CAMPUSLMS STAGE 18 — STAFF DEPARTMENTS & STAFF DESK
==================================================

This UPGRADES the existing CampusLMS. It is NOT a new Django project.

WHAT CHANGES
- Staff signup uses a separate visual form, not the lecturer signup form.
- Staff category: Teaching Support Staff or Non-Teaching Staff.
- Department dropdown changes with category.
- 25 university departments seeded, including Human Resources, Games & Sports,
  Transport & Fleet, Library, Finance, Security, ICT, Maintenance, and more.
- Job title, country code, phone, DOB and password fields are preserved.
- Approval still handled by Django Admin -> Campus Access -> Employee Applications.
- Administrator approval still issues a registration number and email notice via
  the previously installed email notification configuration.
- Approved staff go to a unique Staff Desk with staff-specific info and department
  directory. Lecturers continue using their own teaching dashboard.
- Administrator can designate a Department Head in Staff Profiles. Signup cannot
  grant management permissions; staff cannot approve themselves.

INSTALL (run ONE command at a time in PowerShell)
1. Stop Django with Ctrl+C.
2. cd "C:\Users\USER\Documents\assignment\New folder\CampusLMS"
3. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\CampusLMS_Stage18_Staff_Departments.zip" -DestinationPath . -Force
4. python install_staff_portal.py
5. python manage.py runserver 8001
6. Refresh homepage using Ctrl+F5, open Staff Sign Up.

REQUIREMENTS
- The existing CampusLMS with the account portal and STAFF user role.
- Python 3.12 and your existing Django environment.
- Keep other apps (academics, campus_teaching, student_services) installed.

DOES NOT
- Recreate user accounts, change auth model, delete course data or grades.
- Automatically grant staff access to payroll/finance/HR employee records.
- Make staff into lecturers or superusers.
- Create SMTP credentials: real email remains dependent on configured SMTP.

SAFETY
- Installer checks expected files before editing.
- Makes external timestamped backup of existing files and SQLite database.
- Installs new tables with ordinary Django migrations.
- Can be rerun without duplicating navigation or departments.
- If it safety-stops on a customized file, STOP and share the error rather
  than removing your existing customizations.
