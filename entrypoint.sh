#!/bin/bash

# Wait for the database to be ready
echo "Waiting for the database to be ready..."
while ! nc -z postgres 5432; do # Use 'postgres' not 'postgres_db'
  sleep 1
done

# Run migrations
echo "Running makemigrations and migrate..."
python /app/manage.py makemigrations --noinput
python /app/manage.py migrate --noinput
echo "Database migrations complete."

echo "Collecting static files..."
python /app/manage.py collectstatic --noinput
echo "Static files collected."

# Now execute the command passed to the script
exec "$@"