#!/bin/bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers=2
