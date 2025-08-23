import os
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab

from providers.providers_enum import ProviderEnum

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algo_trade.settings')

# Create the Celery application instance
app = Celery('algo_trade')

# Load configuration from Django settings, using the 'CELERY_' namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks from all installed apps
app.autodiscover_tasks()

app.conf.update(
    worker_prefetch_multiplier=1,
    timezone="Asia/Tehran",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=100,
    task_soft_time_limit=60,
    worker_proc_alive_timeout=30,
    worker_soft_shutdown_timeout=10,
    worker_enable_soft_shutdown_on_idle=True,
    worker_max_tasks_per_child=100,
)

# Use the Django database scheduler for beat to avoid race conditions in distributed setups
app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

# Scaling best practices:
# - Run only one beat instance (multiple beats can cause duplicate tasks)
# - Scale workers horizontally for throughput (use concurrency/autoscale env vars)
# - Use a robust broker (Redis/RabbitMQ) and monitor queue length

app.conf.beat_schedule = {
    'market_data_store_wallex': { # Specific name for Wallex
        'task': 'algo.tasks.fetch_and_store_markets',
        'schedule': timedelta(minutes=2),  # Run all active strategies every 2 minutes
        'args': (ProviderEnum.WALLEX.value, {}), # Pass empty config dict for now
    },
    'market_data_store_nobitex': { # Specific name for Nobitex
        'task': 'algo.tasks.fetch_and_store_markets',
        'schedule': timedelta(minutes=2),  # Run all active strategies every 2 minutes
        'args': (ProviderEnum.NOBITEX.value, {}), # Pass empty config dict for now
    },
    'asset_data_store_wallex': { # Specific name for Wallex
        'task': 'algo.tasks.fetch_and_store_assets',
        'schedule': crontab(day_of_week='1', hour='13', minute='30'), # Example: Monday 1:30 PM
        'args': (ProviderEnum.WALLEX.value, {}),
    },
    'asset_data_store_nobitex': { # Specific name for Nobitex
        'task': 'algo.tasks.fetch_and_store_assets',
        'schedule': crontab(day_of_week='1', hour='13', minute='45'), # Example: Monday 1:45 PM
        'args': (ProviderEnum.NOBITEX.value, {}),
    },
    'strategy_processor_run_all': {
        'task': 'algo.tasks.run_all_strategies',
        'schedule': timedelta(minutes=2), # Run all active strategies every 2 minutes
    },
    'deal_processing_fallback': { # Renamed to clarify its fallback role
        'task': 'algo.tasks.dispatch_deal_processing_task',
        'schedule': timedelta(minutes=2), # Periodically check for unprocessed deals
    },
    'inquiry_order_status_periodic': { # Renamed for clarity
        'task': 'algo.tasks.inquiry_orders_task',
        'schedule': timedelta(minutes=3), # Periodically inquire about order statuses
    },
}

# For Django compatibility (so manage.py shell and others can use the app)
from celery import current_app as celery_app
__all__ = ('app', 'celery_app')