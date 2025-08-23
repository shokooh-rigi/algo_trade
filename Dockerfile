FROM python:3.9-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose any necessary ports (if applicable)
EXPOSE 8000 5555

# Define the default command for the container
# This can be overridden in docker-compose.yml
CMD ["tail", "-f", "/dev/null"]