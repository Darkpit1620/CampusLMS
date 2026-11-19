from django.urls import path
from . import views

app_name = "campus_services"
urlpatterns = [
    path("", views.student_hub, name="home"),
    path("fees/", views.finances, name="fees"),
    path("hostel/", views.accommodation, name="accommodation"),
    path("graduation/", views.graduation, name="graduation"),
]
