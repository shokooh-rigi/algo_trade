# Use a slim Python base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies, including PostgreSQL libraries
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    pkg-config \
    curl \
    iputils-ping \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy dependency requirements first to leverage Docker's cache
COPY requirements.txt /app/

# Install Python dependencies with increased timeout and no cache
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt --timeout=120

# Copy project files
COPY . /app/

# Add a script to handle database migrations and app startup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Healthcheck for ensuring the Django app is up and running
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Default command
