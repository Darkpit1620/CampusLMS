import logging
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from campus_access.notifications import send_student_approval_email, is_console_email
from .models import StudentAdmission

logger = logging.getLogger(__name__)


@admin.register(StudentAdmission)
class StudentAdmissionAdmin(admin.ModelAdmin):
    list_display = (
        "applicant", "email", "phone_number", "status",
        "admission_number", "submitted_at",
    )
    list_filter = ("status", "submitted_at")
    search_fields = (
        "user__first_name", "user__last_name", "user__email",
        "user__username", "admission_number", "phone_number",
    )
    readonly_fields = ("status", "admission_number", "submitted_at", "approved_at")
    fields = (
        "user", "phone_number", "date_of_birth", "status",
        "admission_number", "submitted_at", "approved_at",
    )
    actions = ["approve_students", "resend_notifications"]

    @admin.display(description="Student")
    def applicant(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

    @admin.action(description="Approve selected students + notify by email")
    def approve_students(self, request, queryset):
        approved = 0
        emailed = 0
        failed = 0
        for application in queryset.select_related("user"):
            try:
                previously_approved = (
                    application.status == StudentAdmission.Status.APPROVED
                    and bool(application.admission_number)
                )
                application.approve()
                if not previously_approved:
                    approved += 1
                    try:
                        send_student_approval_email(application)
                        emailed += 1
                    except Exception:
                        failed += 1
                        logger.exception("Student admission notice failed for id %s", application.pk)
            except ValidationError as exc:
                self.message_user(request, str(exc), messages.ERROR)
        if approved:
            self.message_user(request, f"Approved {approved} student(s).", messages.SUCCESS)
        self._email_summary(request, emailed, failed)

    @admin.action(description="Resend admission number emails to approved students")
    def resend_notifications(self, request, queryset):
        emailed = failed = 0
        for application in queryset.select_related("user"):
            if application.status != StudentAdmission.Status.APPROVED or not application.admission_number:
                continue
            try:
                send_student_approval_email(application)
                emailed += 1
            except Exception:
                failed += 1
                logger.exception("Student approval resend failed for id %s", application.pk)
        self._email_summary(request, emailed, failed)

    def _email_summary(self, request, emailed, failed):
        if emailed:
            if is_console_email():
                self.message_user(request, f"{emailed} email preview(s) printed in the Django terminal. SMTP is not configured; no real email was delivered.", messages.WARNING)
            else:
                self.message_user(request, f"{emailed} approval email(s) handed to the mail server.", messages.SUCCESS)
        if failed:
            self.message_user(request, f"{failed} notification(s) failed. Approvals were saved. Check SMTP settings and use the Resend action.", messages.ERROR)
