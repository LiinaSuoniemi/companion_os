# Start from official Python 3.11 image (slim = smaller, no extras we don't need)
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies PostgreSQL needs to compile
# (psycopg2-binary mostly handles this but this ensures it)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# If requirements haven't changed, Docker skips reinstalling them on the next build
# This makes rebuilds much faster
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY backend/ .

# Don't run as root inside the container — security best practice
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Expose port 8000 (Django's default)
EXPOSE 8000

# Default command: start Django development server
# docker-compose.yml will override this for production
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
