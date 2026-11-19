"""Staff-only data, without changing the existing custom User or EmployeeApplication.

Lecturer accounts continue to use their separate teaching approval workflow.
"""
from django.core.exceptions import ValidationError
from django.db import models


class StaffCategory(models.TextChoices):
    TEACHING_SUPPORT = "TEACHING_SUPPORT", "Teaching support staff"
    NON_TEACHING = "NON_TEACHING", "Non-teaching staff"


class StaffDepartment(models.Model):
    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=20, choices=StaffCategory.choices)
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("category", "name")

    def __str__(self):
        return self.name


class StaffProfile(models.Model):
    """Supplement to campus_access.EmployeeApplication for university workers."""

    application = models.OneToOneField(
        "campus_access.EmployeeApplication",
        on_delete=models.PROTECT,
        related_name="staff_profile",
    )
    category = models.CharField(max_length=20, choices=StaffCategory.choices)
    department = models.ForeignKey(
        StaffDepartment, on_delete=models.PROTECT, related_name="staff_profiles"
    )
    # Granted by an authorized university administrator, NEVER by signup.
    is_department_head = models.BooleanField(default=False)

    class Meta:
        ordering = ("department__name", "application__user__last_name")

    def clean(self):
        super().clean()
        if self.department_id and self.category != self.department.category:
            raise ValidationError({"department": "Department must match the staff category."})
        if self.application_id and self.application.requested_role != "STAFF":
            raise ValidationError("A staff profile must belong to a staff application.")

    def __str__(self):
        return f"{self.application.user.get_full_name() or self.application.user.username} – {self.department}"
