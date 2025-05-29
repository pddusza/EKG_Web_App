# accounts/urls.py
app_name = 'accounts'

from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register,      name='register'),
    path('mainscreen/', views.mainscreen_view, name='mainscreen'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('add-result/', views.add_result_view, name='add_result'),
    path('your-results/', views.your_results_view, name='your_results'),
    path('results/<int:pk>/', views.result_detail_view, name='result_detail'),
]