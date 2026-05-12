from django.conf import settings


def user_theme(request):
    """Club UI uses one palette site-wide (see static/css/theme.css)."""
    return {'ui_theme': 'classic'}


def admin_log_nav(request):
    """Expose log-viewer policy to admin templates (nav link visibility)."""
    return {
        'app_log_admin_superuser_only': getattr(settings, 'APP_LOG_ADMIN_SUPERUSER_ONLY', True),
    }
