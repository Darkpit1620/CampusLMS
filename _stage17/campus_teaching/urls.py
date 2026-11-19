from django.urls import path
from . import views

app_name = 'campus_teaching'
urlpatterns = [
    path('', views.teaching_dashboard, name='dashboard'),
    path('unit/<int:placement_id>/', views.unit_workspace, name='unit'),
    path('unit/<int:placement_id>/upload/', views.upload_resource, name='upload'),
    path('unit/<int:placement_id>/assignment/new/', views.create_assignment, name='assignment_create'),
]
