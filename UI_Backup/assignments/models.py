
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
)
from django.db import models

from courses.models import Course, Enrollment


def submission_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()

    return (
        f"submissions/assignment_{instance.assignment_id}/"
        f"{uuid4().hex}{extension}"
    )


def validate_submission_size(value):
    maximum_size = 10 * 1024 * 1024

    if value.size > maximum_size:
        raise ValidationError(
            "The file must not exceed 10 MB."
        )


class Assignment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    title = models.CharField(max_length=200)

    instructions = models.TextField()

    due_at = models.DateTimeField()

    max_marks = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_assignments",
        limit_choices_to={"role": "LECTURER"},
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()

        if self.course_id and self.created_by_id:
            if (
                self.created_by.role != "LECTURER"
                or self.course.lecturer_id != self.created_by_id
            ):
                raise ValidationError({
                    "created_by":
                    "The assignment creator must be "
                    "the lecturer assigned to this course."
                })

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
        limit_choices_to={"role": "STUDENT"},
    )

    file = models.FileField(
        upload_to=submission_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "docx"]
            ),
            validate_submission_size,
        ],
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student"],
                name="unique_assignment_student_submission",
            )
        ]

    def clean(self):
        super().clean()

        if self.assignment_id and self.student_id:
            enrolled = Enrollment.objects.filter(
                course_id=self.assignment.course_id,
                student_id=self.student_id,
            ).exists()

            if self.student.role != "STUDENT" or not enrolled:
                raise ValidationError({
                    "student":
                    "Only students enrolled in this course "
                    "can submit this assignment."
                })

    def __str__(self):
        return (
            f"{self.student.username} - "
            f"{self.assignment.title}"
        )


class Grade(models.Model):
    submission = models.OneToOneField(
        Submission,
        on_delete=models.CASCADE,
        related_name="grade",
    )

    marks = models.PositiveIntegerField()

    feedback = models.TextField(blank=True)

    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grades_given",
    )

    graded_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()

        if self.submission_id:
            assignment = self.submission.assignment

            if self.marks > assignment.max_marks:
                raise ValidationError({
                    "marks": "Marks cannot exceed the maximum."
                })

            if (
                self.graded_by_id
                and assignment.course.lecturer_id
                != self.graded_by_id
            ):
                raise ValidationError({
                    "graded_by": "Only the assigned lecturer can grade."
                })

    def __str__(self):
        return f"{self.submission.student.username}: {self.marks}"
