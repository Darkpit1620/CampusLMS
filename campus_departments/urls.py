from django.urls import path
from . import views

app_name = 'campus_departments'
urlpatterns = [
    path('eligible-programmes/', views.eligible_programmes, name='eligible_programmes'),
    path('units/', views.unit_options, name='unit_options'),
    path('my-teaching/', views.my_teaching, name='my_teaching'),
]
