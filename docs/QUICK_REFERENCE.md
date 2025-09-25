# 🚀 Quick Reference Guide

## 📋 Table of Contents

- [Essential Commands](#essential-commands)
- [Configuration Quick Setup](#configuration-quick-setup)
- [Strategy Development](#strategy-development)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Useful Scripts](#useful-scripts)

## ⚡ Essential Commands

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart django_app

# Scale celery workers
docker-compose up -d --scale celery_worker=3

# Stop all services
docker-compose down

# Clean up
docker-compose down -v
```

### Django Management Commands

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Start development server
python manage.py runserver

# Django shell
python manage.py shell

# Check project
python manage.py check
```

### Celery Commands

```bash
# Start celery worker
celery -A algo_trade worker --loglevel=info

# Start celery beat
celery -A algo_trade beat --loglevel=info

# Monitor tasks
celery -A algo_trade flower

# Inspect active tasks
celery -A algo_trade inspect active

# Purge all tasks
celery -A algo_trade purge
```

## ⚙️ Configuration Quick Setup

### Environment Variables (.env)

```bash
# Essential settings
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/algo_trade
REDIS_URL=redis://localhost:6379/0

# Exchange APIs
WALLEX_API_KEY=your_wallex_key
NOBITEX_API_KEY=your_nobitex_key

# Risk Management
DEFAULT_STOP_LOSS_PERCENT=0.3
DEFAULT_TAKE_PROFIT_PERCENT=0.6
MAX_POSITION_SIZE_PERCENT=50.0
```

### Strategy Configuration

```json
{
  "ema_fast_period": 5,
  "ema_slow_period": 13,
  "rsi_period": 14,
  "rsi_overbought": 75.0,
  "rsi_oversold": 25.0,
  "volume_threshold": 1.2,
  "breakout_period": 20,
  "stop_loss_percent": 0.3,
  "take_profit_percent": 0.6,
  "max_position_size_percent": 50.0,
  "trade_cooldown_minutes": 30,
  "max_daily_trades": 10
}
```

## 📈 Strategy Development

### Creating a New Strategy

```python
from algo.strategies.strategy_interface import StrategyInterface
from algo.strategies.enums import ProcessedSideEnum
from typing import Dict, Any, Optional

class MyStrategy(StrategyInterface):
    """Custom trading strategy."""
    
    def initialize(self) -> bool:
        """Initialize strategy."""
        # Load configuration
        # Fetch historical data
        # Calculate indicators
        return True
    
    def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute strategy logic."""
        # Generate signals
        # Apply risk management
        # Return trade signal
        return {
            'side': ProcessedSideEnum.BUY,
            'price': market_data['mid_price'],
            'quantity': 0.1,
            'reason': 'Custom signal',
            'confidence': 0.8
        }
    
    def get_results(self) -> Dict[str, Any]:
        """Return strategy results."""
        return {
            'strategy_id': self.strategy_config_id,
            'market': self.market_symbol,
            'state': self.state.value,
            'trades_count': 0
        }
```

### Adding Strategy to Factory

```python
# In algo/strategies/strategy_factory.py
from algo.strategies.my_strategy import MyStrategy

@staticmethod
def create_strategy(strategy_config_id: int, provider: ProviderEnum, market: str) -> StrategyInterface:
    strategy_config = StrategyConfig.objects.get(id=strategy_config_id)
    strategy_name = strategy_config.strategy
    
    if strategy_name == "MyStrategy":
        return MyStrategy(strategy_config_id, provider, market)
    # ... existing strategies
```

### Creating Strategy Schema

```python
# In algo/strategies/schemas.py
class MyStrategySchema(PydanticBaseModel):
    """Schema for MyStrategy configuration."""
    
    param1: int = Field(10, description="Parameter 1", gt=0)
    param2: float = Field(0.5, description="Parameter 2", ge=0, le=1)
    
    @validator('param1')
    def validate_param1(cls, v):
        if v > 100:
            raise ValueError("param1 must be <= 100")
        return v
```

## 🔌 API Reference

### Strategy API

```python
# Get all strategies
GET /api/strategies/

# Get strategy by ID
GET /api/strategies/{id}/

# Create strategy
POST /api/strategies/
{
    "strategy": "BreakoutStrategy",
    "market": "BTCUSDT",
    "provider": "WALLEX",
    "strategy_configs": {...}
}

# Update strategy
PUT /api/strategies/{id}/

# Delete strategy
DELETE /api/strategies/{id}/
```

### Deal API

```python
# Get all deals
GET /api/deals/

# Get deal by ID
GET /api/deals/{id}/

# Get deals by strategy
GET /api/deals/?strategy=BreakoutStrategy

# Get deals by market
GET /api/deals/?market=BTCUSDT
```

### Order API

```python
# Get all orders
GET /api/orders/

# Get order by ID
GET /api/orders/{id}/

# Get orders by deal
GET /api/orders/?deal={deal_id}

# Cancel order
POST /api/orders/{id}/cancel/
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Database Connection Error

```bash
# Check database status
docker-compose ps postgres_db

# Check database logs
docker-compose logs postgres_db

# Reset database
docker-compose down -v
docker-compose up -d postgres_db
python manage.py migrate
```

#### 2. Celery Worker Not Starting

```bash
# Check celery logs
docker-compose logs celery_worker

# Restart celery
docker-compose restart celery_worker celery_beat

# Check Redis connection
docker-compose exec redis redis-cli ping
```

#### 3. Strategy Not Generating Signals

```python
# Check strategy configuration
from algo.models import StrategyConfig
config = StrategyConfig.objects.get(id=1)
print(config.strategy_configs)

# Check market data
from algo.services.strategy_processor_service import StrategyProcessorService
processor = StrategyProcessorService()
data = processor._fetch_latest_market_data(config)
print(data)
```

#### 4. Orders Not Being Placed

```python
# Check deal processing
from algo.models import Deal
deals = Deal.objects.filter(is_processed=False)
print(f"Unprocessed deals: {deals.count()}")

# Check order management
from algo.services.order_management_service import OrderManagementService
order_service = OrderManagementService()
```

### Debug Commands

```python
# Django shell debugging
python manage.py shell

# Check strategy state
from algo.strategies.strategy_factory import StrategyFactory
strategy = StrategyFactory.create_strategy(1, ProviderEnum.WALLEX, 'BTCUSDT')
strategy.initialize()
print(strategy.get_results())

# Test market data
from providers.provider_factory import ProviderFactory
provider = ProviderFactory.create_provider('Wallex', {})
order_book = provider.get_order_book('BTCUSDT')
print(order_book)
```

## 🛠️ Useful Scripts

### Database Backup Script

```bash
#!/bin/bash
# backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="algo_trade_backup_$DATE.sql"

docker-compose exec -T postgres_db pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE
gzip $BACKUP_FILE
echo "Backup created: $BACKUP_FILE.gz"
```

### Strategy Performance Script

```python
# performance_check.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algo_trade.settings')
django.setup()

from algo.models import Deal
from datetime import datetime, timedelta

# Check deals from last 24 hours
yesterday = datetime.now() - timedelta(days=1)
deals = Deal.objects.filter(created_at__gte=yesterday)

print(f"Deals in last 24h: {deals.count()}")
print(f"Successful deals: {deals.filter(is_processed=True).count()}")
print(f"Active deals: {deals.filter(is_active=True).count()}")

# Check strategy performance
for deal in deals:
    print(f"Deal {deal.id}: {deal.side} {deal.market_symbol} at {deal.price}")
```

### Log Analysis Script

```bash
#!/bin/bash
# analyze_logs.sh

echo "=== Error Analysis ==="
grep "ERROR" logs/django.log | tail -10

echo "=== Performance Analysis ==="
grep "Slow operation" logs/django.log | tail -5

echo "=== Strategy Performance ==="
grep "Strategy processing completed" logs/django.log | tail -5
```

### Health Check Script

```python
# health_check.py
import requests
import json

def check_service(name, url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name}: Healthy")
            return True
        else:
            print(f"❌ {name}: Unhealthy (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False

# Check all services
services = {
    "Django App": "http://localhost:8000/health/",
    "Flower": "http://localhost:5555/",
    "Redis": "http://localhost:6379/",
}

all_healthy = True
for name, url in services.items():
    if not check_service(name, url):
        all_healthy = False

if all_healthy:
    print("🎉 All services are healthy!")
else:
    print("⚠️ Some services are unhealthy!")
```

### Strategy Testing Script

```python
# test_strategy.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algo_trade.settings')
django.setup()

from algo.strategies.strategy_factory import StrategyFactory
from providers.providers_enum import ProviderEnum

def test_strategy():
    """Test strategy with sample data."""
    
    # Create strategy instance
    strategy = StrategyFactory.create_strategy(1, ProviderEnum.WALLEX, 'BTCUSDT')
    
    # Initialize strategy
    if not strategy.initialize():
        print("❌ Strategy initialization failed")
        return
    
    print("✅ Strategy initialized successfully")
    
    # Test with sample market data
    sample_data = {
        'time': '2024-01-01T00:00:00Z',
        'open': 50000.0,
        'high': 51000.0,
        'low': 49000.0,
        'close': 50500.0,
        'volume': 1000.0,
        'mid_price': 50000.0,
        'order_book': {
            'bids': [{'price': 49950, 'quantity': 1.0}],
            'asks': [{'price': 50050, 'quantity': 1.0}]
        }
    }
    
    # Execute strategy
    result = strategy.execute(sample_data)
    
    if result:
        print(f"✅ Signal generated: {result}")
    else:
        print("ℹ️ No signal generated")
    
    # Get results
    results = strategy.get_results()
    print(f"📊 Strategy results: {results}")

if __name__ == "__main__":
    test_strategy()
```

## 📚 Quick Links

### Documentation
- [Main README](../README.md)
- [Technical Documentation](TECHNICAL_DOCUMENTATION.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

### Key Files
- `algo/strategies/breakout_strategy.py` - Main strategy implementation
- `algo/services/order_management_service.py` - Order management
- `algo/services/strategy_processor_service.py` - Strategy processing
- `algo/models.py` - Database models
- `algo_trade/settings.py` - Django settings

### Important URLs
- Django Admin: http://localhost:8000/admin/
- Flower (Celery): http://localhost:5555/
- API Docs: http://localhost:8000/api/
- Health Check: http://localhost:8000/health/

---

This quick reference guide provides essential commands, configurations, and troubleshooting tips for efficient development and maintenance of the algorithmic trading platform.
