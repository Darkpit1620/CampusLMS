"""Student billing, accommodation and graduation records.

Students can only view their own financial records. Only authorized Django
Admin users record actual payments, allocate rooms and approve graduation.
These models do NOT collect payment credentials or take online payments.
"""
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from academics.models import Programme, ProgrammeUnit


def current_year():
    return timezone.localdate().year


YEAR_CHOICES = [(i, f"Year {i}") for i in range(1, 5)]
TERM_CHOICES = [(i, f"Semester {i}") for i in range(1, 4)]
POSITIVE_MONEY = MinValueValidator(Decimal("0.00"))


class FeeStructure(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="fee_structures")
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES)
    semester = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    tuition = models.DecimalField(max_digits=12, decimal_places=2, validators=[POSITIVE_MONEY])
    other_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[POSITIVE_MONEY])
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=180, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["programme", "year", "semester"], name="svc_unique_programme_fee_term")]
        ordering = ["programme__code", "year", "semester"]

    def clean(self):
        super().clean()
        if self.programme_id and self.year and self.year > self.programme.duration_years:
            raise ValidationError({"year": "Year exceeds the programme duration."})

    def __str__(self):
        return f"{self.programme.code} Y{self.year} S{self.semester}"


class Hostel(models.Model):
    name = models.CharField(max_length=120, unique=True)
    campus = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class HostelRoom(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="rooms")
    number = models.CharField(max_length=30)
    capacity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    semester_fee = models.DecimalField(max_digits=12, decimal_places=2, validators=[POSITIVE_MONEY], default=0)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["hostel", "number"], name="svc_unique_hostel_room")]
        ordering = ["hostel__name", "number"]

    def __str__(self):
        return f"{self.hostel.name} / Room {self.number}"


class HostelRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending allocation"
        ALLOCATED = "ALLOCATED", "Allocated"
        DECLINED = "DECLINED", "Declined"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hostel_requests")
    academic_year = models.PositiveIntegerField(default=current_year)
    semester = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=300, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "academic_year", "semester"], name="svc_unique_student_hostel_request_term")]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student.get_username()} {self.academic_year} S{self.semester}"


class HostelAllocation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hostel_allocations")
    room = models.ForeignKey(HostelRoom, on_delete=models.PROTECT, related_name="allocations")
    academic_year = models.PositiveIntegerField()
    semester = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "academic_year", "semester"], name="svc_unique_student_allocation_term")]
        ordering = ["-academic_year", "-semester"]

    def clean(self):
        super().clean()
        if self.student_id and self.student.role != "STUDENT":
            raise ValidationError({"student": "Only students can be allocated hostel rooms."})
        if self.room_id:
            if not self.room.active or not self.room.hostel.active:
                raise ValidationError({"room": "This room or hostel is inactive."})
            if self.status == self.Status.ACTIVE and self.academic_year and self.semester:
                existing = HostelAllocation.objects.filter(
                    room=self.room, academic_year=self.academic_year, semester=self.semester,
                    status=self.Status.ACTIVE,
                )
                if self.pk:
                    existing = existing.exclude(pk=self.pk)
                if existing.count() >= self.room.capacity:
                    raise ValidationError({"room": "This room has reached its capacity for the selected semester."})

    def __str__(self):
        return f"{self.student.get_username()} — {self.room} ({self.academic_year} S{self.semester})"


class FeeCharge(models.Model):
    class Category(models.TextChoices):
        TUITION = "TUITION", "Tuition / university fees"
        HOSTEL = "HOSTEL", "Hostel fees"
        OTHER = "OTHER", "Other fees"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="fee_charges")
    category = models.CharField(max_length=8, choices=Category.choices)
    description = models.CharField(max_length=180)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[POSITIVE_MONEY])
    academic_year = models.PositiveIntegerField()
    semester = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, blank=True, null=True, related_name="charges")
    hostel_allocation = models.OneToOneField(HostelAllocation, on_delete=models.PROTECT, blank=True, null=True, related_name="fee_charge")
    issued_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "fee_structure"], condition=Q(fee_structure__isnull=False), name="svc_unique_student_fee_structure")]
        ordering = ["-issued_at", "-id"]

    def clean(self):
        super().clean()
        if self.student_id and self.student.role != "STUDENT":
            raise ValidationError({"student": "Charges can only be issued to students."})
        if self.hostel_allocation_id and self.student_id != self.hostel_allocation.student_id:
            raise ValidationError({"hostel_allocation": "Hostel allocation belongs to another student."})
        if self.fee_structure_id and self.student_id:
            from academics.models import StudentProgramme
            record = StudentProgramme.objects.filter(student_id=self.student_id).first()
            if not record or record.programme_id != self.fee_structure.programme_id:
                raise ValidationError({"fee_structure": "The fee structure belongs to another programme."})

    @property
    def received(self):
        return self.payments.aggregate(amount=Sum("amount"))["amount"] or Decimal("0.00")

    @property
    def balance(self):
        return self.amount - self.received

    def __str__(self):
        return f"{self.student.get_username()} — {self.description}"


class FeePayment(models.Model):
    class Method(models.TextChoices):
        BANK = "BANK", "Bank"
        MPESA = "MPESA", "M-Pesa"
        CASH = "CASH", "Cash / Office"
        OTHER = "OTHER", "Other verified method"

    charge = models.ForeignKey(FeeCharge, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    reference = models.CharField(max_length=100, unique=True)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.BANK)
    received_on = models.DateField(default=timezone.localdate)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recorded_fee_payments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_on", "-id"]

    def clean(self):
        super().clean()
        if self.charge_id and self.amount and self.amount > 0:
            other = FeePayment.objects.filter(charge_id=self.charge_id).exclude(pk=self.pk).aggregate(amount=Sum("amount"))["amount"] or Decimal("0.00")
            if other + self.amount > self.charge.amount:
                raise ValidationError({"amount": "Payment exceeds the remaining balance on this charge."})

    def __str__(self):
        return f"{self.reference} / KES {self.amount}"


class StudentClearance(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_clearance")
    finance = models.BooleanField(default=False)
    library = models.BooleanField(default=False)
    hostel = models.BooleanField(default=False)
    department = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clearance — {self.student.get_username()}"


class FinalUnitResult(models.Model):
    """Official final percentage per programme placement; NOT assignment marks."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="official_unit_results")
    placement = models.ForeignKey(ProgrammeUnit, on_delete=models.PROTECT, related_name="official_results")
    mark = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="verified_unit_results")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "placement"], name="svc_unique_official_unit_result")]
        ordering = ["placement__year", "placement__semester", "placement__unit__code"]

    def clean(self):
        super().clean()
        if self.student_id and self.placement_id:
            from academics.models import StudentProgramme
            record = StudentProgramme.objects.filter(student_id=self.student_id).first()
            if not record or record.programme_id != self.placement.programme_id:
                raise ValidationError("Final result must match the student's official programme.")

    def __str__(self):
        return f"{self.student.get_username()} / {self.placement.unit.code}: {self.mark}%"


class GraduationPolicy(models.Model):
    class Scheme(models.TextChoices):
        HONOURS = "HONOURS", "Percentage-based honours"
        PASS_ONLY = "PASS_ONLY", "Pass / Fail"
        MANUAL = "MANUAL", "Registrar determines award"

    programme = models.OneToOneField(Programme, on_delete=models.PROTECT, related_name="graduation_policy")
    scheme = models.CharField(max_length=10, choices=Scheme.choices, default=Scheme.MANUAL)
    first_class = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    upper_second = models.DecimalField(max_digits=5, decimal_places=2, default=60)
    lower_second = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    notes = models.CharField(max_length=300, blank=True)

    def clean(self):
        super().clean()
        if not (Decimal("0") <= self.pass_mark < self.lower_second < self.upper_second < self.first_class <= Decimal("100")):
            raise ValidationError("Cutoffs must increase in this order: pass, lower second, upper second, first class.")

    def __str__(self):
        return f"{self.programme.code} graduation policy"


class GraduationApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting registrar review"
        APPROVED = "APPROVED", "Approved for graduation"
        REJECTED = "REJECTED", "Returned for correction"

    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="graduation_application")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True, related_name="graduation_reviews")
    award_confirmed = models.CharField(max_length=150, blank=True, help_text="For MANUAL schemes: enter the official registrar-verified award.")
    note = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"Graduation / {self.student.get_username()} — {self.status}"

    @transaction.atomic
    def approve(self, reviewer):
        if not (reviewer.is_active and reviewer.is_staff and
                reviewer.has_perm("campus_services.change_graduationapplication")):
            raise ValidationError("Only an authorized university registrar or administrator may approve graduation.")
        from .services import graduation_readiness
        ready = graduation_readiness(self.student)
        if not ready["eligible"]:
            raise ValidationError("Cannot approve graduation: " + "; ".join(ready["blockers"]))
        if ready["scheme"] == "MANUAL" and not self.award_confirmed.strip():
            raise ValidationError("Registrar must enter the verified award for manually classified programmes.")
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save(update_fields=["status", "reviewed_at", "reviewed_by", "award_confirmed"])
