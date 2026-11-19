CampusLMS Student Admissions Add-on — SAFE INSTALL
================================================
IMPORTANT: This pack is for the existing CampusLMS Django 5.2 project. It does not replace the database or existing course, assignment, or grading models. Back up first.

1. STOP Django with Ctrl+C, and back up db.sqlite3 and your accounts / config / dashboard code.

2. Extract the ZIP into the EXISTING CampusLMS folder. Merge folders; do not delete folders. Files in the new `admissions/` app are new. The ZIP includes an updated accounts/templates/accounts/login.html; keep a backup of the current login.html before replacing it.

3. In `config/settings.py`, ADD this entry to INSTALLED_APPS (do not replace others):
    "admissions.apps.AdmissionsConfig",

4. In `config/urls.py`, ADD import:
    from admissions.forms import CampusAuthenticationForm
   KEEP all existing urlpatterns. ADD this URL entry:
    path("register/", include("admissions.urls")),
   MODIFY the existing "login/" LoginView so it uses:
    auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=CampusAuthenticationForm,
    )
   Keep the existing name="login". Ensure `include` is imported from django.urls.

5. In your existing colorful homepage (dashboard/templates/dashboard/home.html), add a button to:
    <a href="{% url 'admissions:register' %}">Create Student Account</a>
   The login template already links to registration, so adding the homepage button is optional.

6. Create and apply migrations (NON-DESTRUCTIVE):
    python manage.py check
    python manage.py makemigrations admissions
    python manage.py migrate

7. Run server:
    python manage.py runserver 8001

8. Register a test student at:
    http://127.0.0.1:8001/register/
   The new account will stay inactive and its admission status PENDING.

9. Admin reviews at:
    http://127.0.0.1:8001/admin/admissions/studentadmission/
   Tick the profile, choose action "Approve selected students and issue admission numbers", and press Go.
   The new admission number displays in the list. The administrator must communicate it to the student securely. Email notification is NOT automatic.

10. Student logs in at /login/ using admission number and password. Staff and lecturer accounts still use usernames.

11. Existing student1: to continue logging in, create a StudentAdmission record in the admin for existing student1, then approve it via the same action. This retains the original student1 user ID and all its course enrollments, submissions and grades. Do NOT create a replacement student1 account.

12. For optional tests, after migration:
    python manage.py test admissions

Notes:
- Never use date of birth or admission number as a password. Student's chosen password is hashed via Django.
- The example admission number format is CLMS-2026-000001, determined from the StudentAdmission primary key when approved. It is unique in the database. It is an identifier, not proof of identity.
- Student email uniqueness is checked by the signup form, not yet guaranteed by a unique database constraint on the existing User model.
- No automated email/phone verification or applicant notifications are included; the admin reviews manually.
- Store personal data securely and configure HTTPS, privacy notice and rate limiting before production.
- Do not run flush, delete db.sqlite3, or recreate the User model.
