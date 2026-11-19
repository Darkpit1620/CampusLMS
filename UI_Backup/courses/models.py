from pathlib import Path
from uuid import uuid4

from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_taught",
        limit_choices_to={"role": "LECTURER"},
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.lecturer_id:
            if self.lecturer.role != "LECTURER":
                raise ValidationError({
                    "lecturer": "Select a lecturer account."
                })

    def __str__(self):
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
        limit_choices_to={"role": "STUDENT"},
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]

    def clean(self):
        super().clean()
        if self.student_id:
            if self.student.role != "STUDENT":
                raise ValidationError({
                    "student": "Select a student account."
                })

    def __str__(self):
        return f"{self.student.username} - {self.course.code}"


def material_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()

    return (
        f"courses/{instance.course_id}/"
        f"{uuid4().hex}{extension}"
    )


def validate_material_size(value):
    max_size = 10 * 1024 * 1024

    if value.size > max_size:
        raise ValidationError(
            "The file must not exceed 10 MB."
        )


class CourseMaterial(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="materials",
    )

    title = models.CharField(max_length=200)

    description = models.TextField(blank=True)

    file = models.FileField(
        upload_to=material_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf", "docx", "pptx"
                ]
            ),
            validate_material_size,
        ],
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_materials",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.course.code} - {self.title}"
