#!/bin/sh
set -e

# Ensure the data + media directories exist on the mounted volume
mkdir -p "$(dirname "${DJANGO_DATABASE_PATH:-/app/db.sqlite3}")"
mkdir -p "${DJANGO_MEDIA_ROOT:-/app/media}"

# Apply database migrations on the machine that actually has the volume
python manage.py migrate --noinput

# Hand off to CMD (gunicorn)
exec "$@"
