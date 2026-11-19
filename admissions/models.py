from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class StudentAdmission(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_admission",
    )
    phone_number = models.CharField(max_length=25, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    admission_number = models.CharField(
        max_length=30, unique=True, null=True, blank=True, editable=False
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.get_status_display()}"

    @transaction.atomic
    def approve(self):
        """Approve a student, preserving any previously issued number."""
        if not self.pk:
            raise ValidationError("Save the admission record before approving.")
        if self.user.role != "STUDENT":
            raise ValidationError("Only a student account can receive admission.")
        if not self.admission_number:
            # Unique per record because the database primary key is unique.
            self.admission_number = f"CLMS-{timezone.localdate():%Y}-{self.pk:06d}"
        self.status = self.Status.APPROVED
        if not self.approved_at:
            self.approved_at = timezone.now()
        self.save(update_fields=["admission_number", "status", "approved_at"])
        if not self.user.is_active:
            self.user.is_active = True
            self.user.save(update_fields=["is_active"])
