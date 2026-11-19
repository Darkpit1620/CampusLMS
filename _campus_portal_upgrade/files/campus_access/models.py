from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class StudentCountry(models.Model):
    """Country of registration for NEW student signups; old records need not change."""
    admission = models.OneToOneField(
        "admissions.StudentAdmission",
        on_delete=models.PROTECT,
        related_name="country_detail",
    )
    country = models.CharField(max_length=2)

    def __str__(self):
        return f"{self.admission.user.get_full_name()} ({self.country})"


class EmployeeApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class RequestedRole(models.TextChoices):
        LECTURER = "LECTURER", "Lecturer"
        STAFF = "STAFF", "University Staff"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employee_application",
    )
    requested_role = models.CharField(max_length=10, choices=RequestedRole.choices)
    phone_number = models.CharField(max_length=25)
    country = models.CharField(max_length=2)
    date_of_birth = models.DateField()
    department = models.CharField(max_length=120)
    job_title = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    registration_number = models.CharField(
        max_length=36, unique=True, null=True, blank=True, editable=False
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.get_requested_role_display()}"

    @transaction.atomic
    def approve(self):
        if not self.pk:
            raise ValidationError("Save the application before approving it.")
        if self.requested_role not in {"LECTURER", "STAFF"}:
            raise ValidationError("Only lecturers and university staff may use this approval.")
        if self.user.role != self.requested_role:
            raise ValidationError("The user role does not match this application.")
        if self.status == self.Status.REJECTED:
            raise ValidationError("A rejected application cannot be approved without review.")
        if not self.registration_number:
            prefix = "LEC" if self.requested_role == "LECTURER" else "STF"
            self.registration_number = (
                f"CLMS-{prefix}-{timezone.localdate():%Y}-{self.pk:06d}"
            )
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.save(update_fields=["registration_number", "status", "reviewed_at"])
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=["is_active"])

    @transaction.atomic
    def reject(self):
        if not self.pk:
            raise ValidationError("Save the application before rejecting it.")
        if self.status == self.Status.APPROVED:
            raise ValidationError("An approved account must be managed separately.")
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at"])
        if self.user.is_active:
            self.user.is_active = False
            self.user.save(update_fields=["is_active"])
