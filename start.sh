#!/bin/bash
celery -A config worker -l info -P solo &
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers=1
