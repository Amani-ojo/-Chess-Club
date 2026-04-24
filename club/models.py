from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    display_name = models.CharField(max_length=150)
    lichess_username = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name


class UserProfile(models.Model):
    THEME_CHOICES = [
        ('classic', 'Classic Light'),
        ('midnight', 'Midnight Dark'),
        ('forest', 'Forest Green'),
        ('royal', 'Royal Blue'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    lichess_username = models.CharField(max_length=100, blank=True)
    lichess_api_key = models.CharField(max_length=255, blank=True)
    theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default='classic')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f'Profile<{self.user.username}>'
