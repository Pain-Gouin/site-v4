#!/bin/bash
# Run migrations
python manage.py migrate

# Create cache table if doesnt already exist
python manage.py createcachetable

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:8000 --workers 3 paingouin.wsgi:application
