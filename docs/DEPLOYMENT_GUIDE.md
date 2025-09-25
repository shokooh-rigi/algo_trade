# 🚀 Deployment Guide

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Production Configuration](#production-configuration)
- [Database Setup](#database-setup)
- [Monitoring Setup](#monitoring-setup)
- [Security Hardening](#security-hardening)
- [Scaling Considerations](#scaling-considerations)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / macOS 10.15+
- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ recommended
- **Storage**: 50GB+ SSD recommended
- **Network**: Stable internet connection for API calls

### Software Requirements

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.9+
- **PostgreSQL**: 13+
- **Redis**: 6+

## ⚙️ Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd algo_trade
```

### 2. Environment Variables

Create `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://algo_user:secure_password@postgres_db:5432/algo_trade_db
POSTGRES_DB=algo_trade_db
POSTGRES_USER=algo_user
POSTGRES_PASSWORD=secure_password

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Django Configuration
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Exchange API Keys
WALLEX_API_KEY=your_wallex_api_key_here
WALLEX_API_SECRET=your_wallex_api_secret_here
NOBITEX_API_KEY=your_nobitex_api_key_here
NOBITEX_API_SECRET=your_nobitex_api_secret_here

# Risk Management Settings
DEFAULT_STOP_LOSS_PERCENT=0.3
DEFAULT_TAKE_PROFIT_PERCENT=0.6
MAX_POSITION_SIZE_PERCENT=50.0
MAX_DAILY_TRADES=10
TRADE_COOLDOWN_MINUTES=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs/

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_SERIALIZER=json
CELERY_ACCEPT_CONTENT=json
CELERY_RESULT_SERIALIZER=json
CELERY_TIMEZONE=UTC

# Email Configuration (for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# Security Settings
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 3. Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 🐳 Docker Deployment

### 1. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres_db:
    image: postgres:13
    container_name: algo_trade_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:6-alpine
    container_name: algo_trade_redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  django_app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: algo_trade_django
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=${DEBUG}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      postgres_db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: algo_trade_celery_worker
    command: celery -A algo_trade worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres_db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: algo_trade_celery_beat
    command: celery -A algo_trade beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres_db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  flower:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: algo_trade_flower
    command: celery -A algo_trade flower --port=5555
    environment:
      - REDIS_URL=${REDIS_URL}
    ports:
      - "5555:5555"
    depends_on:
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: algo_trade_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - django_app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### 2. Production Dockerfile

Create `Dockerfile.prod`:

```dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "algo_trade.wsgi:application"]
```

### 3. Nginx Configuration

Create `nginx.conf`:

```nginx
upstream django_app {
    server django_app:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    client_max_body_size 20M;

    location / {
        proxy_pass http://django_app;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /flower/ {
        proxy_pass http://flower:5555/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🚀 Production Configuration

### 1. Django Settings for Production

Update `algo_trade/settings.py`:

```python
import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST', 'postgres_db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 60,
            'options': '-c default_transaction_isolation=read_committed'
        }
    }
}

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'algo': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = '/app/media'

# Security
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### 2. Health Check Endpoint

Create `algo/views.py`:

```python
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """Health check endpoint for monitoring."""
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Redis check
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        health_status['checks']['redis'] = 'healthy'
    except Exception as e:
        health_status['checks']['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    return JsonResponse(health_status)
```

## 🗄️ Database Setup

### 1. Database Migration

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec django_app python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec django_app python manage.py createsuperuser

# Load initial data
docker-compose -f docker-compose.prod.yml exec django_app python manage.py loaddata initial_data.json
```

### 2. Database Backup

Create backup script `scripts/backup_db.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="algo_trade_backup_$DATE.sql"

# Create backup
docker-compose -f docker-compose.prod.yml exec -T postgres_db pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "algo_trade_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### 3. Database Monitoring

```python
# Add to Django admin
class DatabaseHealthAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        # Monitor database performance
        return super().get_queryset(request)
```

## 📊 Monitoring Setup

### 1. Application Monitoring

Create monitoring script `scripts/monitor.sh`:

```bash
#!/bin/bash

# Check service health
check_service() {
    local service=$1
    local port=$2
    
    if curl -f http://localhost:$port/health/ > /dev/null 2>&1; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is unhealthy"
        # Send alert
        curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"🚨 '$service' is down!"}' \
            $SLACK_WEBHOOK_URL
    fi
}

# Check all services
check_service "Django App" 8000
check_service "Flower" 5555
check_service "Nginx" 80
```

### 2. Log Monitoring

```bash
# Monitor logs in real-time
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Check error logs
docker-compose -f docker-compose.prod.yml logs --tail=1000 | grep ERROR

# Monitor specific service
docker-compose -f docker-compose.prod.yml logs -f celery_worker
```

### 3. Performance Monitoring

```python
# Add performance monitoring
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        if execution_time > 5:  # Log slow operations
            logger.warning(f"Slow operation: {func.__name__} took {execution_time:.2f}s")
        
        return result
    return wrapper
```

## 🔒 Security Hardening

### 1. SSL Certificate Setup

```bash
# Generate SSL certificate with Let's Encrypt
certbot certonly --standalone -d your-domain.com

# Copy certificates to nginx
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem
```

### 2. Firewall Configuration

```bash
# Configure UFW firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 5432/tcp   # PostgreSQL (internal only)
ufw deny 6379/tcp   # Redis (internal only)
ufw enable
```

### 3. API Key Security

```python
# Encrypt API keys
from cryptography.fernet import Fernet

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    key = Fernet.generate_key()
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """Decrypt sensitive data."""
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data.encode())
    return decrypted_data.decode()
```

## 📈 Scaling Considerations

### 1. Horizontal Scaling

```yaml
# Scale celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=3

# Load balancer configuration
upstream django_app {
    server django_app_1:8000;
    server django_app_2:8000;
    server django_app_3:8000;
}
```

### 2. Database Optimization

```python
# Database connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    }
}
```

### 3. Redis Clustering

```yaml
# Redis cluster setup
redis_cluster:
  image: redis:6-alpine
  command: redis-cli --cluster create redis1:6379 redis2:6379 redis3:6379 --cluster-replicas 1
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database connectivity
docker-compose -f docker-compose.prod.yml exec django_app python manage.py dbshell

# Reset database
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d postgres_db
docker-compose -f docker-compose.prod.yml exec django_app python manage.py migrate
```

#### 2. Celery Task Issues

```bash
# Check celery worker status
docker-compose -f docker-compose.prod.yml exec celery_worker celery -A algo_trade inspect active

# Restart celery workers
docker-compose -f docker-compose.prod.yml restart celery_worker celery_beat
```

#### 3. Memory Issues

```bash
# Monitor memory usage
docker stats

# Clean up unused containers
docker system prune -a

# Increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Performance Optimization

```python
# Optimize database queries
from django.db import connection

def optimize_queries():
    """Monitor and optimize database queries."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10")
        slow_queries = cursor.fetchall()
        
        for query, time in slow_queries:
            if time > 1000:  # Queries taking more than 1 second
                logger.warning(f"Slow query detected: {query} (avg: {time}ms)")
```

### Log Analysis

```bash
# Analyze error patterns
grep "ERROR" /app/logs/django.log | cut -d' ' -f1-3 | sort | uniq -c | sort -nr

# Monitor API response times
grep "API" /app/logs/django.log | awk '{print $NF}' | sort -n | tail -10
```

---

This deployment guide provides comprehensive instructions for deploying the algorithmic trading platform in a production environment with proper security, monitoring, and scaling considerations.
