
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET
from courses.models import Course
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET
from assignments.models import Submission
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "dashboard/home.html")


@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser or (
        user.is_staff and user.role == "ADMIN"
    ):
        role_title = "Administrator Dashboard"
        features = [
            "Manage Students",
            "Manage Lecturers",
            "Manage Courses",
            "View Reports",
        ]

    elif user.role == "LECTURER":
        role_title = "Lecturer Dashboard"
        features = [
            "My Courses",
            "Upload Learning Materials",
            "Manage Assignments",
            "Grade Students",
        ]

    else:
        role_title = "Student Dashboard"
        features = [
            "My Courses",
            "Learning Materials",
            "Submit Assignments",
            "View Grades",
        ]

    return render(
        request,
        "dashboard/role_dashboard.html",
        {
            "role_title": role_title,
            "features": features,
        },
    )


@login_required
@require_GET
def student_gradebook(request):
    user = request.user

    # Only student accounts may view this gradebook.
    if (
        user.role != "STUDENT"
        or user.is_staff
        or user.is_superuser
    ):
        raise PermissionDenied(
            "Only students can view their gradebook."
        )

    submissions = (
        Submission.objects
        .filter(student=user)
        .select_related(
            "assignment__course",
            "grade",
        )
        .order_by("-submitted_at")
    )

    records = []
    graded_count = 0
    percentage_total = 0

    for submission in submissions:
        grade = getattr(submission, "grade", None)
        percentage = None

        if grade:
            maximum = submission.assignment.max_marks

            if maximum > 0:
                percentage = round(
                    (grade.marks / maximum) * 100, 1
                )
                percentage_total += percentage
                graded_count += 1

        records.append({
            "submission": submission,
            "grade": grade,
            "percentage": percentage,
        })

    average_percentage = (
        round(percentage_total / graded_count, 1)
        if graded_count else None
    )

    return render(
        request,
        "dashboard/student_gradebook.html",
        {
            "records": records,
            "total_count": len(records),
            "graded_count": graded_count,
            "average_percentage": average_percentage,
        },
    )


@login_required
@require_GET
def lecturer_reports(request):
    user = request.user

    if (
        user.role != "LECTURER"
        or user.is_staff
        or user.is_superuser
    ):
        raise PermissionDenied(
            "Only lecturers can view these reports."
        )

    courses = (
        Course.objects.filter(lecturer=user)
        .prefetch_related(
            "enrollments",
            "assignments__submissions__grade",
        )
        .order_by("code")
    )

    course_reports = []
    all_percentages = []

    total_enrollments = 0
    total_assignments = 0
    total_submissions = 0
    total_graded = 0

    for course in courses:
        enrolled = len(course.enrollments.all())
        assignments = list(course.assignments.all())

        total_enrollments += enrolled
        total_assignments += len(assignments)

        assignment_rows = []
        course_submissions = 0
        course_graded = 0
        course_percentages = []

        for assignment in assignments:
            submissions = list(
                assignment.submissions.all()
            )

            submitted = len(submissions)
            graded = 0
            percentages = []

            for submission in submissions:
                grade = getattr(
                    submission, "grade", None
                )

                if grade is not None:
                    graded += 1

                    percentage = (
                        grade.marks
                        / assignment.max_marks
                    ) * 100

                    percentages.append(percentage)
                    course_percentages.append(percentage)
                    all_percentages.append(percentage)

            course_submissions += submitted
            course_graded += graded

            assignment_rows.append({
                "assignment": assignment,
                "submitted": submitted,
                "graded": graded,
                "pending": submitted - graded,
                "not_submitted": max(
                    enrolled - submitted, 0
                ),
                "average": (
                    round(
                        sum(percentages)
                        / len(percentages), 1
                    )
                    if percentages else None
                ),
            })

        total_submissions += course_submissions
        total_graded += course_graded

        course_reports.append({
            "course": course,
            "enrolled": enrolled,
            "assignment_count": len(assignments),
            "submitted": course_submissions,
            "graded": course_graded,
            "pending": (
                course_submissions - course_graded
            ),
            "average": (
                round(
                    sum(course_percentages)
                    / len(course_percentages), 1
                )
                if course_percentages else None
            ),
            "assignment_rows": assignment_rows,
        })

    overall_average = (
        round(
            sum(all_percentages)
            / len(all_percentages), 1
        )
        if all_percentages else None
    )

    return render(
        request,
        "dashboard/lecturer_reports.html",
        {
            "course_reports": course_reports,
            "course_count": len(course_reports),
            "total_enrollments": total_enrollments,
            "total_assignments": total_assignments,
            "total_submissions": total_submissions,
            "total_graded": total_graded,
            "pending_grading": (
                total_submissions - total_graded
            ),
            "overall_average": overall_average,
        },
    )
