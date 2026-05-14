"""
chess_club URL Configuration

The `urlpatterns` list routes URLs to views.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
feature/stockfish-analysis-improvements
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from club.admin_log_view import application_log_view
=======
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
 develop

urlpatterns = [
    path(
        'admin/diagnostics/application-logs/',
        admin.site.admin_view(application_log_view),
        name='admin_application_logs',
    ),
    path('admin/', admin.site.urls),
 feature/stockfish-analysis-improvements
    path('accounts/', include('allauth.urls')),
    path('', include('club.urls')),
    path('ai/', include('ai_pipeline.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/', include('ai_pipeline.api_urls')),
]

=======
    path('', include('club.urls')),
]

# Serve media files during development
 develop
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
