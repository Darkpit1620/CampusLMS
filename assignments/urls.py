
from django.urls import path
from . import views

app_name = "assignments"

urlpatterns = [
    path(
        "courses/<int:course_id>/",
        views.course_assignments,
        name="course_assignments",
    ),
    path(
    "submit/<int:assignment_id>/",
    views.submit_assignment,
    name="submit_assignment",
    ),

    path(
        "courses/<int:course_id>/create/",
        views.create_assignment,
        name="create_assignment",
    ),

path(
    "submissions/<int:assignment_id>/",
    views.assignment_submissions,
    name="assignment_submissions",
    ),

path(
    "download/<int:submission_id>/",
    views.download_submission,
    name="download_submission",
    ),

path(
    "grade/<int:submission_id>/",
    views.grade_submission,
    name="grade_submission",
    )
]
