import logging
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from campus_access.notifications import send_student_approval_email, is_console_email
from .models import ProgrammeRequirement, ProgrammeApplication, UnitLecturerAssignment, ProgrammeLecturerAllocation, SemesterRegistration, RegisteredUnit

log = logging.getLogger(__name__)


@admin.register(ProgrammeRequirement)
class ProgrammeRequirementAdmin(admin.ModelAdmin):
    list_display = ("programme", "minimum_mean_grade", "minimum_cluster_points", "requirements_verified", "applications_open")
    list_filter = ("requirements_verified", "applications_open", "minimum_mean_grade")
    list_editable = ("minimum_cluster_points", "minimum_mean_grade", "requirements_verified", "applications_open")
    search_fields = ("programme__name", "programme__code")
    list_select_related = ("programme",)


@admin.register(ProgrammeApplication)
class ProgrammeApplicationAdmin(admin.ModelAdmin):
    list_display = ("student_name", "programme", "kcse_mean_grade", "reported_cluster_points", "admission_status")
    list_filter = ("programme", "admission__status", "kcse_mean_grade")
    search_fields = ("admission__user__email", "admission__user__first_name", "admission__user__last_name", "programme__name")
    readonly_fields = ("admission", "programme", "kcse_mean_grade", "reported_cluster_points", "applied_at")
    actions = ("approve_and_email",)
    list_select_related = ("programme", "admission__user")

    @admin.display(description="Applicant")
    def student_name(self, obj):
        return obj.admission.user.get_full_name() or obj.admission.user.username

    @admin.display(description="Admission")
    def admission_status(self, obj):
        return obj.admission.get_status_display()

    @admin.action(description="Verify application, approve admission and send admission number")
    def approve_and_email(self, request, queryset):
        sent, failed, processed = 0, 0, 0
        for item in queryset.select_related("admission__user"):
            try:
                if item.admission.status == "APPROVED":
                    continue
                # Approval is a human decision; KUCCPS subject requirements must be verified externally.
                item.admission.approve()
                processed += 1
                try:
                    send_student_approval_email(item.admission)
                    sent += 1
                except Exception:
                    failed += 1
                    log.exception("Could not send approval email for application %s", item.pk)
            except ValidationError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        if processed:
            self.message_user(request, f"Approved {processed} application(s).", messages.SUCCESS)
        if sent:
            note = "Email previews printed to Django terminal." if is_console_email() else "Emails handed to mail server."
            self.message_user(request, f"{sent} notification(s): {note}", messages.WARNING if is_console_email() else messages.SUCCESS)
        if failed:
            self.message_user(request, f"{failed} email(s) failed. Admissions were saved; resend from Student Admissions.", messages.ERROR)


@admin.register(UnitLecturerAssignment)
class UnitLecturerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("placement", "lecturer")
    list_filter = ("placement__programme",)
    search_fields = ("placement__unit__code", "placement__unit__title", "lecturer__username", "lecturer__email")


@admin.register(ProgrammeLecturerAllocation)
class ProgrammeLecturerAllocationAdmin(admin.ModelAdmin):
    list_display = ("programme", "lecturer", "year", "semester", "updated_at")
    list_filter = ("programme", "year", "semester")
    search_fields = ("programme__code", "programme__name", "lecturer__username")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        count = obj.apply_to_units()
        self.message_user(request, f"Assigned {count} unit(s) to {obj.lecturer.get_username()}.", messages.SUCCESS)


class RegisteredUnitInline(admin.TabularInline):
    model = RegisteredUnit
    can_delete = False
    extra = 0
    readonly_fields = ("placement", "status", "reviewed_by", "reviewed_at", "review_note")
    fields = readonly_fields


@admin.register(SemesterRegistration)
class SemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ("student", "programme", "year", "semester", "status", "submitted_at")
    list_filter = ("status", "year", "semester", "student_programme__programme")
    search_fields = ("student_programme__student__email", "student_programme__student__username", "student_programme__programme__name")
    readonly_fields = ("student_programme", "year", "semester", "status", "submitted_at", "reviewed_at")
    inlines = (RegisteredUnitInline,)

    @admin.display(description="Student")
    def student(self, obj):
        return obj.student_programme.student

    @admin.display(description="Programme")
    def programme(self, obj):
        return obj.student_programme.programme


@admin.register(RegisteredUnit)
class RegisteredUnitAdmin(admin.ModelAdmin):
    list_display = ("registration", "placement", "status", "reviewed_by", "reviewed_at")
    list_filter = ("status", "placement__programme")
    search_fields = ("registration__student_programme__student__username", "placement__unit__code")
    readonly_fields = ("registration", "placement", "status", "reviewed_by", "reviewed_at", "review_note")
