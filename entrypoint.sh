#!/bin/bash

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Run server
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --log-level debug --workers=8
