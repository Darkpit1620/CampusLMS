"""Academic catalogue, separate from existing LMS courses and their data."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def current_year():
    return timezone.localdate().year


class Programme(models.Model):
    code = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=200)
    department = models.CharField(max_length=140, blank=True)
    duration_years = models.PositiveSmallIntegerField(default=4, choices=[(i, f"{i} year(s)") for i in range(1, 5)])
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name", "code")

    def __str__(self):
        return f"{self.code} — {self.name}"


class Unit(models.Model):
    code = models.CharField(max_length=24, unique=True)
    title = models.CharField(max_length=200)
    credits = models.PositiveSmallIntegerField(default=3)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} — {self.title}"


class ProgrammeUnit(models.Model):
    """A curriculum placement, optionally connected to a pre-existing LMS course."""
    YEAR_CHOICES = [(i, f"Year {i}") for i in range(1, 5)]
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 4)]
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="curriculum")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="placements")
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES)
    semester = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES)
    required = models.BooleanField(default=True)
    lms_course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="academic_placements",
        help_text="Optional: connect this unit to an existing teaching course, such as CSC101. Does not automatically enrol students.",
    )

    class Meta:
        ordering = ("programme__code", "year", "semester", "unit__code")
        constraints = [
            models.UniqueConstraint(
                fields=("programme", "unit", "year", "semester"),
                name="academics_unique_curriculum_slot",
            )
        ]

    def clean(self):
        super().clean()
        if self.programme_id and self.year and self.year > self.programme.duration_years:
            raise ValidationError({"year": "Year cannot exceed the programme duration."})

    def __str__(self):
        return f"{self.programme.code}: Y{self.year} S{self.semester} — {self.unit.code}"


class StudentProgramme(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        COMPLETED = "COMPLETED", "Completed"

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="academic_programme",
        limit_choices_to={"role": "STUDENT"},
    )
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="student_records")
    intake_year = models.PositiveIntegerField(default=current_year)
    current_year = models.PositiveSmallIntegerField(default=1, choices=ProgrammeUnit.YEAR_CHOICES)
    current_semester = models.PositiveSmallIntegerField(default=1, choices=ProgrammeUnit.SEMESTER_CHOICES)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("programme__code", "student__username")

    def clean(self):
        super().clean()
        if self.student_id and self.student.role != "STUDENT":
            raise ValidationError({"student": "Only student accounts can be assigned a programme."})
        if self.programme_id and self.current_year and self.current_year > self.programme.duration_years:
            raise ValidationError({"current_year": "Year exceeds this programme's duration."})

    def __str__(self):
        return f"{self.student.get_username()} — {self.programme.code} (Y{self.current_year} S{self.current_semester})"
