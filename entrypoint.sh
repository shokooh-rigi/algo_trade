#!/bin/bash

# A robust way to wait for the database
# Use 'postgres_db' which is the correct container name
echo "Waiting for PostgreSQL to become available..."
while ! nc -z postgres_db 5432; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up and running!"

# This block will run only for the Django app service
if [ "$1" = "gunicorn" ]; then
  # Run migrations and collect static files only on the web server
  python manage.py makemigrations
  python manage.py migrate --noinput
   python manage.py init_market_data
  python manage.py init_asset_data
  python manage.py collectstatic --noinput
fi

# Finally, execute the main command passed to the script (gunicorn, celery, etc.)
exec "$@"