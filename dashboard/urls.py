
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "grades/",
        views.student_gradebook,
        name="student_gradebook",
    ),
    path(
    "lecturer/reports/",
    views.lecturer_reports,
    name="lecturer_reports",
    ),
]
