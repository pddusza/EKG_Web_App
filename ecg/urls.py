from django.urls import path
from . import views

app_name = 'ecg'
urlpatterns = [
    path('upload/', views.upload_ecg, name='upload'),
    path('history/', views.history, name='history'),
    path('detail/<int:pk>/', views.detail, name='detail'),
]