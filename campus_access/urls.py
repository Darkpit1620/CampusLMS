from django.urls import path
from . import views
from staff_portal import views as staff_views
from campus_admissions_units import views as enrolment_views

app_name = "campus_access"

urlpatterns = [
    path("staff/departments/", staff_views.staff_departments, name="staff_departments"),
    path("", views.access_home, name="home"),
    path("student/signup/", enrolment_views.student_signup, name="student_signup"),
    path("lecturer/signup/", views.employee_signup, {"role": "lecturer"}, name="lecturer_signup"),
    path("staff/signup/", staff_views.staff_signup, name="staff_signup"),
    path("<str:role>/login/", views.RoleLoginView.as_view(), name="role_login"),
    path("pending/", views.pending, name="pending"),
    path("staff/workspace/", staff_views.staff_dashboard, name="staff_workspace"),
]
