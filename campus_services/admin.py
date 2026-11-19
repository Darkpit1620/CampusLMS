from decimal import Decimal
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from academics.models import StudentProgramme
from .models import (FeeStructure, FeeCharge, FeePayment, Hostel, HostelRoom,
                     HostelRequest, HostelAllocation, StudentClearance,
                     FinalUnitResult, GraduationPolicy, GraduationApplication)


@admin.action(description="Issue these term fee invoices to currently enrolled students")
def issue_fee_invoices(modeladmin, request, queryset):
    created = 0
    with transaction.atomic():
        for fee in queryset.filter(is_active=True).select_related("programme"):
            amount = fee.tuition + fee.other_fees
            if amount <= 0:
                continue
            students = StudentProgramme.objects.filter(
                programme=fee.programme, current_year=fee.year,
                current_semester=fee.semester, status=StudentProgramme.Status.ACTIVE,
            ).select_related("student")
            for record in students:
                charge, was_created = FeeCharge.objects.get_or_create(
                    student=record.student, fee_structure=fee,
                    defaults={
                        "category": FeeCharge.Category.TUITION,
                        "description": f"University fees: {fee.programme.code}, Year {fee.year}, Semester {fee.semester}",
                        "amount": amount,
                        "academic_year": timezone.localdate().year,
                        "semester": fee.semester,
                    },
                )
                created += int(was_created)
    modeladmin.message_user(request, f"Created {created} new invoices; existing invoices were not duplicated.")


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("programme", "year", "semester", "tuition", "other_fees", "is_active")
    list_filter = ("programme", "year", "semester", "is_active")
    search_fields = ("programme__code", "programme__name")
    actions = [issue_fee_invoices]


@admin.register(FeeCharge)
class FeeChargeAdmin(admin.ModelAdmin):
    list_display = ("student", "category", "description", "amount", "academic_year", "semester", "issued_at")
    list_filter = ("category", "academic_year", "semester")
    search_fields = ("student__username", "description")
    autocomplete_fields = ("student", "fee_structure", "hostel_allocation")
    def has_delete_permission(self, request, obj=None):
        return False
    def get_readonly_fields(self, request, obj=None):
        return ("student", "category", "amount", "academic_year", "semester", "fee_structure", "hostel_allocation", "issued_at") if obj else ()


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "charge", "amount", "method", "received_on", "entered_by")
    list_filter = ("method", "received_on")
    search_fields = ("reference", "charge__student__username")
    autocomplete_fields = ("charge",)
    exclude = ("entered_by",)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("charge", "amount", "reference", "method", "received_on", "created_at")
        return ()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.entered_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ("name", "campus", "active")
    search_fields = ("name", "campus")


@admin.register(HostelRoom)
class HostelRoomAdmin(admin.ModelAdmin):
    list_display = ("hostel", "number", "capacity", "semester_fee", "active")
    list_filter = ("hostel", "active")
    search_fields = ("hostel__name", "number")


@admin.register(HostelRequest)
class HostelRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "academic_year", "semester", "status", "submitted_at")
    list_filter = ("status", "academic_year", "semester")
    search_fields = ("student__username", "student__first_name", "student__last_name")


@admin.register(HostelAllocation)
class HostelAllocationAdmin(admin.ModelAdmin):
    list_display = ("student", "room", "academic_year", "semester", "status")
    list_filter = ("room__hostel", "academic_year", "semester", "status")
    search_fields = ("student__username", "room__number")
    autocomplete_fields = ("student", "room")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return ("student", "room", "academic_year", "semester", "assigned_at") if obj else ()


@admin.register(StudentClearance)
class StudentClearanceAdmin(admin.ModelAdmin):
    list_display = ("student", "finance", "library", "hostel", "department", "updated_at")
    list_filter = ("finance", "library", "hostel", "department")
    search_fields = ("student__username", "student__first_name", "student__last_name")
    autocomplete_fields = ("student",)


@admin.register(FinalUnitResult)
class FinalUnitResultAdmin(admin.ModelAdmin):
    list_display = ("student", "placement", "mark", "verified", "verified_by", "verified_at")
    list_filter = ("verified", "placement__programme")
    search_fields = ("student__username", "placement__unit__code")
    autocomplete_fields = ("student", "placement")
    exclude = ("verified_by", "verified_at")

    def save_model(self, request, obj, form, change):
        if obj.verified:
            obj.verified_by = request.user
            obj.verified_at = timezone.now()
        else:
            obj.verified_by = None
            obj.verified_at = None
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(GraduationPolicy)
class GraduationPolicyAdmin(admin.ModelAdmin):
    list_display = ("programme", "scheme", "first_class", "upper_second", "lower_second", "pass_mark")
    list_filter = ("scheme",)
    search_fields = ("programme__code", "programme__name")


@admin.action(description="Approve eligible graduation applications after clearance")
def approve_graduation(modeladmin, request, queryset):
    approved = 0
    for application in queryset.select_related("student"):
        try:
            application.approve(request.user)
            approved += 1
        except ValidationError as error:
            modeladmin.message_user(request, f"{application.student.username}: {error}", level=messages.ERROR)
    modeladmin.message_user(request, f"Approved {approved} eligible applications.")


@admin.register(GraduationApplication)
class GraduationApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "submitted_at", "reviewed_at", "reviewed_by", "award_confirmed")
    list_filter = ("status",)
    search_fields = ("student__username", "student__first_name", "student__last_name")
    autocomplete_fields = ("student",)
    actions = [approve_graduation]
    readonly_fields = ("student", "status", "submitted_at", "reviewed_by", "reviewed_at")
    fields = ("student", "status", "submitted_at", "award_confirmed", "note", "reviewed_by", "reviewed_at")

    def has_add_permission(self, request):
        # Students submit applications in their own portal.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
