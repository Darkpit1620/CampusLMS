"""Approval notices. Never email passwords, authentication tokens or secrets."""
from django.conf import settings
from django.core.mail import send_mail


def _portal_url(path):
    base = getattr(settings, "CAMPUS_PUBLIC_URL", "http://127.0.0.1:8001")
    return base.rstrip("/") + path


def is_console_email():
    return settings.EMAIL_BACKEND in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
    }


def send_student_approval_email(application):
    number = application.admission_number
    if not number:
        raise ValueError("Student has no admission number yet")
    recipient = application.user.email.strip()
    if not recipient:
        raise ValueError("The student has no email address; update the account first")
    send_mail(
        subject="CampusLMS: Your student admission is approved",
        message=(
            f"Hello {application.user.get_full_name() or 'Student'},\n\n"
            "Your CampusLMS student application has been approved.\n\n"
            f"Admission number: {number}\n"
            f"Student sign in: {_portal_url('/access/student/login/')}\n\n"
            "Use the password you chose during registration. "
            "We will never email you your password.\n\n"
            "If you did not apply, contact your university administrator.\n\n"
            "CampusLMS Admissions\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )


def send_employee_approval_email(application):
    number = application.registration_number
    if not number:
        raise ValueError("Employee has no registration number yet")
    recipient = application.user.email.strip()
    if not recipient:
        raise ValueError("The employee has no email address; update the account first")
    role_name = application.get_requested_role_display()
    portal = "lecturer" if application.requested_role == "LECTURER" else "staff"
    send_mail(
        subject=f"CampusLMS: Your {role_name} account is approved",
        message=(
            f"Hello {application.user.get_full_name() or role_name},\n\n"
            f"Your CampusLMS {role_name.lower()} account has been approved.\n\n"
            f"Registration number: {number}\n"
            f"Sign in: {_portal_url('/access/' + portal + '/login/')}\n\n"
            "Use the password you chose during registration. "
            "Existing lecturers may still use their original username.\n"
            "Do not share your password.\n\n"
            "CampusLMS Administration\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )
