from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("programmes/", views.programme_list, name="programme_list"),
    path("programmes/<str:code>/", views.programme_detail, name="programme_detail"),
    path("my-units/", views.my_units, name="my_units"),
]
