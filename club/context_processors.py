def user_theme(request):
    theme = 'classic'
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        theme = request.user.profile.theme_preference
    return {'ui_theme': theme}
