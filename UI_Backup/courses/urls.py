
from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path(
        "my/",
        views.my_courses,
        name="my_courses",
    ),

    path(
        "<int:course_id>/",
        views.course_detail,
        name="course_detail",
    ),

    path(
        "<int:course_id>/upload/",
        views.upload_material,
        name="upload_material",
    ),

    path(
        "<int:course_id>/materials/<int:material_id>/download/",
        views.download_material,
        name="download_material",
    ),
]
