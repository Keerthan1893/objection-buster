from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/start/', views.start_run, name='start_run'),
    path('api/status/<uuid:run_id>/', views.check_status, name='check_status'),
]