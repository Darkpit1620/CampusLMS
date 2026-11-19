from django.urls import path
from . import views

app_name = "campus_admissions_units"
urlpatterns = [
    path("find-programmes/", views.programme_finder, name="programme_finder"),
    path("register-units/", views.register_units, name="register_units"),
    path("lecturer/approvals/", views.lecturer_queue, name="lecturer_queue"),
    path("lecturer/approvals/<int:unit_id>/", views.lecturer_review, name="lecturer_review"),
]
