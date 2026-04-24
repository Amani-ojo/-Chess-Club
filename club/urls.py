from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'club'

urlpatterns = [
    path('', views.home, name='home'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
