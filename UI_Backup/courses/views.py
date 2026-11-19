
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils.text import slugify
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
)

from .forms import CourseMaterialForm
from .models import Course, CourseMaterial


def accessible_courses(user):
    if user.is_superuser or (
        user.is_staff and user.role == "ADMIN"
    ):
        return Course.objects.all()

    if user.role == "LECTURER":
        return Course.objects.filter(lecturer=user)

    if user.role == "STUDENT":
        return Course.objects.filter(
            enrollments__student=user
        )

    raise PermissionDenied("Access denied.")


@login_required
def my_courses(request):
    user = request.user

    if user.role == "LECTURER" and not user.is_superuser:
        courses = Course.objects.filter(
            lecturer=user
        ).order_by("code")
        heading = "My Teaching Courses"

    elif user.role == "STUDENT" and not user.is_superuser:
        courses = Course.objects.filter(
            enrollments__student=user
        ).select_related("lecturer").order_by("code")
        heading = "My Enrolled Courses"

    else:
        raise PermissionDenied(
            "This page is for lecturers and students."
        )

    return render(
        request,
        "courses/my_courses.html",
        {"courses": courses, "heading": heading},
    )


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(
        accessible_courses(request.user),
        pk=course_id,
    )

    materials = course.materials.select_related(
        "uploaded_by"
    ).order_by("-uploaded_at")

    can_upload = (
        request.user.role == "LECTURER"
        and course.lecturer_id == request.user.pk
    )

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "materials": materials,
            "can_upload": can_upload,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def upload_material(request, course_id):
    if request.user.role != "LECTURER":
        raise PermissionDenied(
            "Only lecturers can upload materials."
        )

    course = get_object_or_404(
        Course,
        pk=course_id,
        lecturer=request.user,
    )

    if request.method == "POST":
        form = CourseMaterialForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.uploaded_by = request.user
            material.save()

            return redirect(
                "courses:course_detail",
                course_id=course.id,
            )
    else:
        form = CourseMaterialForm()

    return render(
        request,
        "courses/upload_material.html",
        {"form": form, "course": course},
    )


@login_required
@require_GET
def download_material(request, course_id, material_id):
    course = get_object_or_404(
        accessible_courses(request.user),
        pk=course_id,
    )

    material = get_object_or_404(
        CourseMaterial,
        pk=material_id,
        course=course,
    )

    extension = Path(material.file.name).suffix.lower()
    filename = (
        (slugify(material.title) or "material")
        + extension
    )

    return FileResponse(
        material.file.open("rb"),
        as_attachment=True,
        filename=filename,
    )
