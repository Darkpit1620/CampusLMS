from django.urls import path
from . import views

app_name = "campus_access"

urlpatterns = [
    path("", views.access_home, name="home"),
    path("student/signup/", views.student_signup, name="student_signup"),
    path("lecturer/signup/", views.employee_signup, {"role": "lecturer"}, name="lecturer_signup"),
    path("staff/signup/", views.employee_signup, {"role": "staff"}, name="staff_signup"),
    path("<str:role>/login/", views.RoleLoginView.as_view(), name="role_login"),
    path("pending/", views.pending, name="pending"),
    path("staff/workspace/", views.staff_workspace, name="staff_workspace"),
]
