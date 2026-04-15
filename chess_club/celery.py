"""
Celery application configuration for the chess_club project.

Copy this file to:  chess_club/celery.py

Then add to chess_club/__init__.py:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_club.settings')

app = Celery('chess_club')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
