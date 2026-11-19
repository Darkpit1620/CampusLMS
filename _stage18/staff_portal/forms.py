"""A staff-only registration form reusing the existing secure signup backend."""
from django import forms
from django.db import transaction

from campus_access.forms import EmployeeSignupForm
from .models import StaffCategory, StaffDepartment, StaffProfile


class StaffSignupForm(EmployeeSignupForm):
    staff_category = forms.ChoiceField(
        label="Staff category",
        choices=[("", "Choose staff category")] + list(StaffCategory.choices),
        help_text="Lecturers must use the separate Lecturer Portal. Teaching support is for assistants and academic services.",
    )
    department = forms.ChoiceField(label="Staff department", choices=())
    job_title = forms.CharField(
        label="Job title / position",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. HR Officer, Driver, Games Coordinator"}),
    )

    def __init__(self, *args, **kwargs):
        # The requested role must NEVER be taken from user-supplied POST data.
        kwargs.pop("requested_role", None)
        super().__init__(*args, requested_role="STAFF", **kwargs)
        departments = list(StaffDepartment.objects.filter(is_active=True).order_by("name"))
        self.fields["department"].choices = [("", "Choose department")] + [
            (item.name, item.name) for item in departments
        ]
        self.order_fields([
            "first_name", "last_name", "email", "staff_category", "department",
            "job_title", "phone_country", "phone_number", "date_of_birth",
            "password1", "password2",
        ])

    def clean(self):
        data = super().clean()
        category, department_name = data.get("staff_category"), data.get("department")
        if category and department_name:
            if not StaffDepartment.objects.filter(
                category=category, name=department_name, is_active=True
            ).exists():
                self.add_error("department", "Choose a department in your selected staff category.")
        return data

    @transaction.atomic
    def save(self):
        if not self.is_valid():
            raise ValueError("Cannot save an invalid staff registration")
        application = super().save()  # Creates inactive STAFF user & pending application.
        department = StaffDepartment.objects.get(
            name=self.cleaned_data["department"], is_active=True,
            category=self.cleaned_data["staff_category"],
        )
        StaffProfile.objects.create(
            application=application,
            category=self.cleaned_data["staff_category"],
            department=department,
            is_department_head=False,
        )
        return application
