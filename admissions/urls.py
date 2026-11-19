from django.urls import path
from . import views

app_name = "admissions"

urlpatterns = [
    path("", views.register_student, name="register"),
    path("pending/", views.registration_pending, name="pending"),
]
