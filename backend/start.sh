#!/bin/sh
# Companion OS — production start script
# Runs migrations then starts gunicorn.
# This is a single script so Railway's startCommand is one command (no && chain issues).

echo "=== Running migrations ==="
python manage.py migrate --noinput

# Create superuser if DJANGO_SUPERUSER_USERNAME is set and user doesn't exist yet.
# Uses Django's built-in --noinput flag which reads from environment variables.
# Safe to run on every deploy — does nothing if user already exists.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "=== Ensuring superuser ==="
    python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser already exists"
    # createsuperuser skips an existing user, so an auto-created superuser can end up
    # with no usable password (unable to log in). Ensure the password and superuser
    # flags match the env var on every deploy. Idempotent and safe.
    if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
U = get_user_model()
u = U.objects.filter(username=os.environ['DJANGO_SUPERUSER_USERNAME']).first()
if u:
    u.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print('=== Superuser password ensured for', u.username, '===')
"
    fi
fi

echo "=== Starting gunicorn on port $PORT ==="
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 1
