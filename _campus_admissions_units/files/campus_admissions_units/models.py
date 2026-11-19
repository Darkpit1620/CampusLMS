"""Applicants, transparent sample entry thresholds, and lecturer-reviewed units.

This app extends existing CampusLMS models; it never replaces User, Admission,
Programme, ProgrammeUnit, Course, Submission or Grade.
"""
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from academics.models import Programme, ProgrammeUnit, StudentProgramme
from admissions.models import StudentAdmission


GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "E"]
GRADE_CHOICES = [(g, g) for g in GRADES]


class ProgrammeRequirement(models.Model):
    """Admin-editable *indicative* filtering thresholds, not KUCCPS verification."""
    programme = models.OneToOneField(Programme, on_delete=models.CASCADE, related_name="admission_requirement")
    minimum_cluster_points = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("48"))],
        help_text="Illustrative score on a 0–48 scale until this institution verifies its requirements."
    )
    minimum_mean_grade = models.CharField(max_length=2, choices=GRADE_CHOICES, default="C+")
    requirements_verified = models.BooleanField(
        default=False, help_text="Only tick after institution-specific KUCCPS and subject requirements are verified."
    )
    applications_open = models.BooleanField(default=True)
    source_notes = models.CharField(max_length=250, blank=True, help_text="Year and verified official source, if any.")

    def __str__(self):
        return f"{self.programme.code} entry requirements"


class ProgrammeApplication(models.Model):
    """The requested programme; an admission approval places the existing user in it."""
    admission = models.OneToOneField(StudentAdmission, on_delete=models.PROTECT, related_name="programme_application")
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT)
    kcse_mean_grade = models.CharField(max_length=2, choices=GRADE_CHOICES)
    reported_cluster_points = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("48"))],
        help_text="Self-reported score. Not independently validated by CampusLMS."
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admission.user.get_full_name()} → {self.programme.code}"


class UnitLecturerAssignment(models.Model):
    """Allows units without an LMS Course to be approved by a named lecturer."""
    placement = models.OneToOneField(ProgrammeUnit, on_delete=models.CASCADE, related_name="review_assignment")
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, limit_choices_to={"role": "LECTURER"})

    def clean(self):
        super().clean()
        if self.lecturer_id and (self.lecturer.role != "LECTURER" or not self.lecturer.is_active):
            raise ValidationError({"lecturer": "Select an active lecturer account."})

    def __str__(self):
        return f"{self.placement} → {self.lecturer.get_username()}"


class ProgrammeLecturerAllocation(models.Model):
    """Admin shortcut to assign a lecturer to all units of a programme or selected term."""
    YEARS = [(0, "All years")] + ProgrammeUnit.YEAR_CHOICES
    SEMESTERS = [(0, "All semesters")] + ProgrammeUnit.SEMESTER_CHOICES
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT)
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, limit_choices_to={"role": "LECTURER"})
    year = models.PositiveSmallIntegerField(default=0, choices=YEARS)
    semester = models.PositiveSmallIntegerField(default=0, choices=SEMESTERS)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("programme", "year", "semester"), name="campus_unique_lecturer_allocation_scope")]

    def clean(self):
        super().clean()
        if self.lecturer_id and (self.lecturer.role != "LECTURER" or not self.lecturer.is_active):
            raise ValidationError({"lecturer": "Choose an active lecturer."})

    def apply_to_units(self):
        placements = ProgrammeUnit.objects.filter(programme=self.programme)
        if self.year:
            placements = placements.filter(year=self.year)
        if self.semester:
            placements = placements.filter(semester=self.semester)
        count = 0
        for placement in placements:
            UnitLecturerAssignment.objects.update_or_create(placement=placement, defaults={"lecturer": self.lecturer})
            count += 1
        return count

    def __str__(self):
        return f"{self.programme.code} → {self.lecturer.get_username()} ({self.get_year_display()}, {self.get_semester_display()})"


class SemesterRegistration(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Awaiting lecturer approval"
        PARTIAL = "PARTIAL", "Partially reviewed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    student_programme = models.ForeignKey(StudentProgramme, on_delete=models.PROTECT, related_name="unit_registrations")
    year = models.PositiveSmallIntegerField(choices=ProgrammeUnit.YEAR_CHOICES)
    semester = models.PositiveSmallIntegerField(choices=ProgrammeUnit.SEMESTER_CHOICES)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("student_programme", "year", "semester"),
            name="campus_unique_student_term_registration"
        )]
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"{self.student_programme.student.get_username()}: Y{self.year} S{self.semester}"


class RegisteredUnit(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    registration = models.ForeignKey(SemesterRegistration, on_delete=models.PROTECT, related_name="units")
    placement = models.ForeignKey(ProgrammeUnit, on_delete=models.PROTECT, related_name="registration_requests")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("registration", "placement"),
            name="campus_unique_unit_in_registration"
        )]
        ordering = ("placement__unit__code",)

    def clean(self):
        super().clean()
        if self.registration_id and self.placement_id:
            sp = self.registration.student_programme
            if (
                sp.programme_id != self.placement.programme_id
                or self.registration.year != self.placement.year
                or self.registration.semester != self.placement.semester
            ):
                raise ValidationError("Unit does not belong to the student's selected programme and semester.")

    def __str__(self):
        return f"{self.registration} / {self.placement.unit.code}: {self.status}"
