
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
