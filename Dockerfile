# Use a Python base image
FROM python:3.9-slim-buster

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

# Create and set working directory
WORKDIR $APP_HOME

# Install system dependencies (if any, e.g., for psycopg2-binary)
# RUN apt-get update && apt-get install -y \
#     postgresql-client \
#     # libpq-dev # Might be needed for psycopg2-binary build
#     # gcc # Might be needed for some python packages
#     # && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt $APP_HOME/
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire project
COPY . $APP_HOME/

# Expose ports if needed (e.g., for Django server if it were in Docker)
# EXPOSE 8000

# No CMD here, as docker-compose.yml will override it with specific commands
