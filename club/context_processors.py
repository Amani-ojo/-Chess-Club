def user_theme(request):
    """Club UI uses one palette site-wide (see static/css/theme.css)."""
    return {'ui_theme': 'classic'}
