
from pathlib import Path

from django.http import FileResponse
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
)

from .forms import GradeForm
from .models import Grade
from django.http import HttpResponseForbidden
from django.utils import timezone
from .models import Assignment, Submission
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from courses.models import Course
from .forms import AssignmentForm, SubmissionForm


@login_required
def course_assignments(request, course_id):
    user = request.user

    if user.is_superuser:
        raise PermissionDenied("Access denied.")

    if user.role == "LECTURER":
        course = get_object_or_404(
            Course,
            pk=course_id,
            lecturer=user,
        )
        can_create = True

    elif user.role == "STUDENT":
        course = get_object_or_404(
            Course.objects.filter(
                enrollments__student=user
            ),
            pk=course_id,
        )
        can_create = False

    else:
        raise PermissionDenied("Access denied.")

    assignments = course.assignments.order_by(
        "due_at"
    )

    return render(
        request,
        "assignments/course_assignments.html",
        {
            "course": course,
            "assignments": assignments,
            "can_create": can_create,
        },
    )


@login_required
def create_assignment(request, course_id):
    user = request.user

    if user.is_superuser or user.role != "LECTURER":
        raise PermissionDenied(
            "Only assigned lecturers can create assignments."
        )

    course = get_object_or_404(
        Course,
        pk=course_id,
        lecturer=user,
    )

    if request.method == "POST":
        form = AssignmentForm(request.POST)

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.created_by = user

            assignment.full_clean()
            assignment.save()

            return redirect(
                "assignments:course_assignments",
                course_id=course.id,
            )
    else:
        form = AssignmentForm()

    return render(
        request,
        "assignments/create_assignment.html",
        {
            "form": form,
            "course": course,
        },
    )


@login_required
def submit_assignment(request, assignment_id):
    user = request.user

    # Only ordinary student accounts can submit.
    if (
        user.role != "STUDENT"
        or user.is_superuser
        or user.is_staff
    ):
        raise PermissionDenied(
            "Only students can submit assignments."
        )

    # Students must be enrolled in the course.
    assignment = get_object_or_404(
        Assignment.objects.select_related("course"),
        pk=assignment_id,
        course__enrollments__student=user,
    )

    # Check whether the student already submitted.
    submission = Submission.objects.filter(
        assignment=assignment,
        student=user,
    ).first()

    deadline_passed = timezone.now() >= assignment.due_at

    if request.method == "POST":
        if submission:
            return HttpResponseForbidden(
                "You have already submitted this assignment."
            )

        if deadline_passed:
            return HttpResponseForbidden(
                "The assignment deadline has passed."
            )

        form = SubmissionForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            new_submission = form.save(commit=False)
            new_submission.assignment = assignment
            new_submission.student = user

            new_submission.full_clean()
            new_submission.save()

            return redirect(
                "assignments:submit_assignment",
                assignment_id=assignment.id,
            )
    else:
        form = SubmissionForm()

   
    return render(
        request,
        "assignments/submit_assignment.html",
        {
            "assignment": assignment,
            "form": form,
            "submission": submission,
            "deadline_passed": deadline_passed,
            "grade": (
                Grade.objects.filter(
                    submission=submission
                ).first()
                if submission else None
            ),
        },
    )



@login_required
@require_GET
def assignment_submissions(request, assignment_id):
    user = request.user

    if (
        user.is_superuser
        or user.is_staff
        or user.role != "LECTURER"
    ):
        raise PermissionDenied("Lecturer access required.")

    assignment = get_object_or_404(
        Assignment,
        pk=assignment_id,
        course__lecturer=user,
    )

    submissions = (
        Submission.objects.filter(assignment=assignment)
        .select_related("student", "grade")
        .order_by("-submitted_at")
    )

    return render(
        request,
        "assignments/submissions_list.html",
        {
            "assignment": assignment,
            "submissions": submissions,
        },
    )


@login_required
@require_GET
def download_submission(request, submission_id):
    submission = get_object_or_404(
        Submission.objects.select_related(
            "assignment__course"
        ),
        pk=submission_id,
    )

    user = request.user

    lecturer_allowed = (
        user.role == "LECTURER"
        and submission.assignment.course.lecturer_id == user.pk
        and not user.is_staff
        and not user.is_superuser
    )

    student_allowed = (
        user.role == "STUDENT"
        and submission.student_id == user.pk
        and not user.is_staff
        and not user.is_superuser
    )

    if not (
        lecturer_allowed
        or student_allowed
        or user.is_superuser
    ):
        raise PermissionDenied("Access denied.")

    extension = Path(submission.file.name).suffix.lower()

    return FileResponse(
        submission.file.open("rb"),
        as_attachment=True,
        filename=f"submission-{submission.pk}{extension}",
    )


@login_required
@require_http_methods(["GET", "POST"])
def grade_submission(request, submission_id):
    user = request.user

    if (
        user.is_superuser
        or user.is_staff
        or user.role != "LECTURER"
    ):
        raise PermissionDenied("Lecturer access required.")

    submission = get_object_or_404(
        Submission.objects.select_related(
            "student", "assignment__course"
        ),
        pk=submission_id,
        assignment__course__lecturer=user,
    )

    existing_grade = Grade.objects.filter(
        submission=submission
    ).first()

    form = GradeForm(
        request.POST or None,
        instance=existing_grade,
        submission=submission,
    )

    if request.method == "POST" and form.is_valid():
        grade = form.save(commit=False)
        grade.submission = submission
        grade.graded_by = user
        grade.full_clean()
        grade.save()

        return redirect(
            "assignments:assignment_submissions",
            assignment_id=submission.assignment_id,
        )

    return render(
        request,
        "assignments/grade_submission.html",
        {
            "submission": submission,
            "form": form,
        },
    )
