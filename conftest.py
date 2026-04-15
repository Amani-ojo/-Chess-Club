"""
pytest configuration for the chess_club project.

Boots Django and Celery from test_settings so that @shared_task tasks
run in ALWAYS_EAGER mode — synchronously, no broker or Redis required.
"""

import os
import webbrowser
from pathlib import Path

import django

REPORT_PATH = Path(__file__).parent / 'test_report.html'


def pytest_configure(config):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')
    django.setup()

    from celery import Celery
    app = Celery('chess_club')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()


def pytest_sessionfinish(session, exitstatus):
    """Open the HTML test report in the browser after the run (local dev only)."""
    if REPORT_PATH.exists() and not os.environ.get('CI'):
        webbrowser.open(REPORT_PATH.as_uri())
