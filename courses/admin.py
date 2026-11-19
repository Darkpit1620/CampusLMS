
from django.contrib import admin
from .models import Course, Enrollment, CourseMaterial


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "lecturer",
        "created_at",
    )

    search_fields = (
        "code",
        "title",
        "lecturer__username",
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "course",
        "enrolled_at",
    )

    list_filter = ("course",)

    search_fields = (
        "student__username",
        "course__code",
        "course__title",
    )


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = ("course",)

    search_fields = (
        "title",
        "course__code",
        "course__title",
    )
