"""
Django settings used exclusively by the test suite.

Keeps tests fast and self-contained:
  - SQLite :memory: database
  - Celery runs synchronously (no broker required)
  - Stockfish path resolved from env var or OS-specific defaults
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'club',
    'ai_pipeline',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

LICHESS_API_BASE_URL = 'https://lichess.org/api'
LICHESS_API_TOKEN    = os.environ.get('LICHESS_API_TOKEN', 'test-token')

# Stockfish: prefer env var, then OS-specific local dev path, then system path
def _default_stockfish_path():
    if os.environ.get('STOCKFISH_PATH'):
        return os.environ['STOCKFISH_PATH']
    if sys.platform == 'win32':
        return os.path.join(
            BASE_DIR, 'bin', 'stockfish_extracted', 'stockfish',
            'stockfish-windows-x86-64-avx2.exe',
        )
    return '/usr/local/bin/stockfish'

STOCKFISH_PATH    = _default_stockfish_path()
STOCKFISH_DEPTH   = 10
STOCKFISH_THREADS = 1
STOCKFISH_HASH_MB = 64

CELERY_TASK_ALWAYS_EAGER     = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL            = 'memory://'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ             = True
SECRET_KEY         = 'test-secret-key-not-for-production'
