# Start from official Python 3.11 image (slim = smaller, no extras we don't need)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Disable Python output buffering — ensures logs appear immediately in Railway
# Without this, crash output gets stuck in the buffer and never reaches Railway logs
ENV PYTHONUNBUFFERED=1

# Install system dependencies PostgreSQL needs to compile
# (psycopg2-binary mostly handles this but this ensures it)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# If requirements haven't changed, Docker skips reinstalling them on the next build
# This makes rebuilds much faster
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY backend/ .

# Collect static files at build time so gunicorn can start immediately at runtime.
# Uses base settings to avoid needing DATABASE_URL during build.
# WhiteNoise at runtime will serve these files.
RUN DJANGO_SETTINGS_MODULE=config.settings.base \
    DJANGO_SECRET_KEY=build-only-not-real \
    python manage.py collectstatic --noinput

# Make start script executable
RUN chmod +x start.sh

# Don't run as root inside the container — security best practice
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# Railway injects $PORT dynamically. Expose is informational only.
EXPOSE 8000

# Default command: start Django development server
# Railway's startCommand overrides this in production
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
