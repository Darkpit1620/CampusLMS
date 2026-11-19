from django import forms
from django.contrib import admin

from .models import StaffCategory, StaffDepartment, StaffProfile


@admin.register(StaffDepartment)
class StaffDepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    ordering = ("category", "name")


class StaffProfileAdminForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = "__all__"

    def clean(self):
        data = super().clean()
        department, category = data.get("department"), data.get("category")
        if department and category and department.category != category:
            self.add_error("department", "Department does not match staff category")
        return data


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    form = StaffProfileAdminForm
    list_display = (
        "employee", "category", "department", "is_department_head", "approved"
    )
    list_filter = ("category", "department", "is_department_head")
    search_fields = (
        "application__user__first_name", "application__user__last_name",
        "application__registration_number", "department__name",
    )
    readonly_fields = ("application",)
    list_select_related = ("application__user", "department")

    @admin.display(description="Employee")
    def employee(self, obj):
        return obj.application.user.get_full_name() or obj.application.user.username

    @admin.display(boolean=True, description="Approved account")
    def approved(self, obj):
        return obj.application.status == "APPROVED" and obj.application.user.is_active

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.extend(["category", "department", "is_department_head"])
        return fields

    def has_add_permission(self, request):
        # New staff profiles are created by signup; legacy users are managed
        # separately rather than assigning a profile to arbitrary accounts.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
