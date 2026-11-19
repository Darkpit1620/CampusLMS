
from django.contrib import admin

from .models import Assignment, Submission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "created_by",
        "due_at",
        "max_marks",
    )

    list_filter = ("course",)

    search_fields = (
        "title",
        "course__code",
    )


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "assignment",
        "submitted_at",
    )

    list_filter = ("assignment__course",)

    search_fields = (
        "student__username",
        "assignment__title",
    )
"""  """