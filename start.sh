#!/usr/bin/env bash
# start.sh
# Start celery worker in background
celery -A config worker -l info &

# Start gunicorn in foreground
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
