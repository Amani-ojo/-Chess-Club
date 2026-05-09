"""
chess_club URL Configuration

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from club import views as club_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Self-service registration must come before the django auth URLs
    # so 'register' resolves to our view rather than any future built-in.
    path('accounts/register/', club_views.register, name='register'),
    # Built-in login, logout, password change/reset views
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('club.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
