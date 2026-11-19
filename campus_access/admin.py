import logging
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import StudentCountry, EmployeeApplication
from .notifications import send_employee_approval_email, is_console_email

logger = logging.getLogger(__name__)


@admin.register(EmployeeApplication)
class EmployeeApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "applicant", "requested_role", "registration_number",
        "department", "country", "status", "submitted_at",
    )
    list_filter = ("requested_role", "status", "department")
    search_fields = (
        "user__first_name", "user__last_name", "user__email",
        "department", "registration_number",
    )
    readonly_fields = ("status", "registration_number", "submitted_at", "reviewed_at")
    actions = ("approve_selected", "resend_notifications", "reject_selected")

    @admin.display(description="Applicant")
    def applicant(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.action(description="Approve lecturer/staff + notify by email")
    def approve_selected(self, request, queryset):
        done = emailed = failed = 0
        for application in queryset.select_related("user"):
            try:
                already_approved = (
                    application.status == EmployeeApplication.Status.APPROVED
                    and bool(application.registration_number)
                )
                application.approve()
                if not already_approved:
                    done += 1
                    try:
                        send_employee_approval_email(application)
                        emailed += 1
                    except Exception:
                        failed += 1
                        logger.exception("Employee approval notice failed for id %s", application.pk)
            except ValidationError as error:
                self.message_user(request, str(error), level=messages.ERROR)
        if done:
            self.message_user(request, f"Approved {done} lecturer/staff account(s).", level=messages.SUCCESS)
        self._email_summary(request, emailed, failed)

    @admin.action(description="Resend registration numbers to approved lecturer/staff")
    def resend_notifications(self, request, queryset):
        emailed = failed = 0
        for application in queryset.select_related("user"):
            if application.status != EmployeeApplication.Status.APPROVED or not application.registration_number:
                continue
            try:
                send_employee_approval_email(application)
                emailed += 1
            except Exception:
                failed += 1
                logger.exception("Employee approval resend failed for id %s", application.pk)
        self._email_summary(request, emailed, failed)

    @admin.action(description="Reject selected pending applications")
    def reject_selected(self, request, queryset):
        done = 0
        for application in queryset.select_related("user"):
            try:
                application.reject()
                done += 1
            except ValidationError as error:
                self.message_user(request, str(error), level=messages.ERROR)
        if done:
            self.message_user(request, f"Rejected {done} application(s).", level=messages.SUCCESS)

    def _email_summary(self, request, emailed, failed):
        if emailed:
            if is_console_email():
                self.message_user(request, f"{emailed} email preview(s) printed to Django terminal. SMTP is not configured; no real email was delivered.", messages.WARNING)
            else:
                self.message_user(request, f"{emailed} approval email(s) handed to mail server.", messages.SUCCESS)
        if failed:
            self.message_user(request, f"{failed} notification(s) failed. Approval was saved. Check SMTP and use Resend.", messages.ERROR)


@admin.register(StudentCountry)
class StudentCountryAdmin(admin.ModelAdmin):
    list_display = ("admission", "country")
    search_fields = ("admission__user__first_name", "admission__user__last_name")
