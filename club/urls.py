from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('matches/', views.matches, name='matches'),
    path('matches/<int:pk>/', views.match_detail, name='match_detail'),
    path('members/<int:pk>/', views.member_profile, name='member_profile'),
    path('about/', views.about, name='about'),
]
