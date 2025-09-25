# 🚀 Algorithmic Trading Platform

A sophisticated Django-based algorithmic trading platform that implements automated trading strategies with advanced risk management, real-time market data processing, and exchange-level stop-loss orders.

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Strategy Implementation](#strategy-implementation)
- [Risk Management](#risk-management)
- [API Integration](#api-integration)
- [Configuration](#configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🎯 Overview

This platform provides a complete solution for algorithmic trading with:

- **Automated Strategy Execution**: Breakout trading strategies with technical indicators
- **Exchange-Level Risk Management**: True stop-loss and take-profit orders
- **Real-Time Data Processing**: Live market data from multiple providers
- **Scalable Architecture**: Django + Celery + Redis + PostgreSQL
- **Advanced Monitoring**: Comprehensive logging and performance tracking

## ✨ Key Features

### 🛡️ Advanced Risk Management
- **Exchange-Level Stop-Loss Orders**: Automatic STOP_MARKET orders placed directly on exchanges
- **Take-Profit Orders**: LIMIT orders for automatic profit taking
- **Trailing Stops**: Dynamic stop-loss adjustment as price moves favorably
- **Position Sizing**: Confidence-based position sizing (max 50% of balance)
- **Cooldown Periods**: Prevents overtrading with configurable cooldowns
- **Daily Trade Limits**: Maximum trades per day to control risk

### 📊 Technical Analysis
- **EMA Crossovers**: Fast (5) and Slow (13) Exponential Moving Averages
- **RSI Momentum**: Relative Strength Index for overbought/oversold conditions
- **Volume Analysis**: Volume ratio thresholds for signal confirmation
- **Breakout Detection**: High/Low breakout patterns with momentum confirmation
- **Order Book Analysis**: Real-time order book imbalance detection

### 🔄 Real-Time Processing
- **Live Market Data**: Real-time OHLCV and order book data
- **Strategy Execution**: Automated signal generation and trade execution
- **Order Management**: Complete order lifecycle management
- **Performance Monitoring**: Real-time strategy performance tracking

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django App    │    │   Celery Beat   │    │  Celery Worker  │
│                 │    │                 │    │                 │
│ • Strategy      │    │ • Scheduling    │    │ • Task          │
│   Processing    │    │ • Cron Jobs     │    │   Execution     │
│ • Order         │    │ • Periodic      │    │ • Strategy      │
│   Management    │    │   Tasks         │    │   Running       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │                 │
                    │ • Message Queue │
                    │ • Task Broker   │
                    │ • Caching       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │                 │
                    │ • Strategy      │
                    │   Configs       │
                    │ • Deal History  │
                    │ • Order Data    │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Exchange      │
                    │   APIs          │
                    │                 │
                    │ • Wallex        │
                    │ • Nobitex       │
                    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- PostgreSQL 13+
- Redis 6+

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd algo_trade
```

2. **Set up environment**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

4. **Run with Docker**
```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

5. **Access the application**
- Django Admin: http://localhost:8000/admin/
- Flower (Celery Monitor): http://localhost:5555/
- API Documentation: http://localhost:8000/api/

## 📈 Strategy Implementation

### Breakout Strategy

The platform implements a sophisticated breakout trading strategy:

```python
class BreakoutStrategy(StrategyInterface):
    """
    Breakout trading strategy with advanced risk management.
    
    Features:
    - EMA crossover signals (5/13 periods)
    - RSI momentum confirmation
    - Volume analysis
    - Breakout pattern detection
    - Automatic stop-loss and take-profit
    """
```

#### Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ema_fast_period` | 5 | Fast EMA period for quick signals |
| `ema_slow_period` | 13 | Slow EMA period for trend direction |
| `rsi_period` | 14 | RSI calculation period |
| `rsi_overbought` | 75.0 | RSI overbought level |
| `rsi_oversold` | 25.0 | RSI oversold level |
| `volume_threshold` | 1.2 | Volume ratio threshold (120% of average) |
| `breakout_period` | 20 | High/Low breakout detection period |
| `stop_loss_percent` | 0.3 | Stop loss percentage |
| `take_profit_percent` | 0.6 | Take profit percentage |
| `max_position_size_percent` | 50.0 | Maximum position size percentage |
| `trade_cooldown_minutes` | 30 | Cooldown between trades |
| `max_daily_trades` | 10 | Maximum trades per day |

#### Signal Generation

The strategy generates signals based on multiple confirmations:

1. **Breakout Signals**:
   - Price breaks above/below 20-period high/low
   - EMA crossover confirmation
   - RSI not in extreme territory
   - Volume above threshold

2. **Momentum Signals**:
   - Strong momentum in trend direction
   - EMA crossover with previous confirmation
   - RSI momentum confirmation

3. **Order Book Signals**:
   - Order book imbalance detection
   - Real-time bid/ask pressure analysis

## 🛡️ Risk Management

### Exchange-Level Protection

The platform implements true exchange-level risk management:

#### Stop-Loss Orders
```python
# Automatic stop-loss order placement
stop_loss_request = CreateOrderRequestSchema(
    symbol=deal.market_symbol,
    side=stop_loss_side,
    type="STOP_MARKET",  # Immediate execution
    quantity=str(adjusted_quantity),
    stopPrice=str(adjusted_stop_price)
)
```

#### Take-Profit Orders
```python
# Automatic take-profit order placement
take_profit_request = CreateOrderRequestSchema(
    symbol=deal.market_symbol,
    side=take_profit_side,
    type="LIMIT",  # Better price control
    quantity=str(adjusted_quantity),
    price=str(adjusted_take_profit_price)
)
```

#### Trailing Stops
```python
# Dynamic trailing stop updates
def update_trailing_stop(self, deal: Deal, current_price: float):
    if deal.side == "BUY":
        new_stop_price = current_price * (1 - deal.trailing_stop_distance / 100)
        if new_stop_price > deal.stop_loss_price:
            return self._update_stop_loss_price(deal, new_stop_price)
```

### Risk Controls

1. **Position Sizing**: Based on signal confidence (max 50% of balance)
2. **Cooldown Periods**: 30-minute minimum between trades
3. **Daily Limits**: Maximum 10 trades per day
4. **Stop-Loss**: Automatic 0.3% stop-loss on all positions
5. **Take-Profit**: Automatic 0.6% take-profit on all positions

## 🔌 API Integration

### Supported Exchanges

#### Wallex (Primary Trading)
- Real-time order book data
- Order placement and management
- Account balance queries
- Trade execution

#### Nobitex (Historical Data)
- OHLCV historical data
- Technical indicator calculations
- Market analysis

### Data Flow

```
Market Data Sources
├── Wallex API (Real-time)
│   ├── Order Book Data
│   ├── Current Prices
│   └── Trade Execution
└── Nobitex API (Historical)
    ├── OHLCV Data
    ├── Technical Indicators
    └── Market Analysis

Strategy Processing
├── Signal Generation
├── Risk Assessment
├── Order Placement
└── Position Management
```

## ⚙️ Configuration

### Django Settings

Key configuration options in `algo_trade/settings.py`:

```python
# Provider Configuration
WALLEX_BASE_URL = "https://api.wallex.ir"
NOBITEX_BASE_URL = "https://api.nobitex.ir"

# Risk Management
DEFAULT_STOP_LOSS_PERCENT = 0.3
DEFAULT_TAKE_PROFIT_PERCENT = 0.6
MAX_POSITION_SIZE_PERCENT = 50.0

# Celery Configuration
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
```

### Strategy Configuration

Configure strategies through Django Admin:

1. **Access Admin**: http://localhost:8000/admin/
2. **Navigate to**: Strategy Configs
3. **Create New Strategy**:
   - Select market (e.g., BTCUSDT)
   - Choose provider (Wallex)
   - Configure parameters
   - Enable historical data if needed

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/algo_trade

# Redis
REDIS_URL=redis://localhost:6379/0

# Exchange APIs
WALLEX_API_KEY=your_wallex_api_key
NOBITEX_API_KEY=your_nobitex_api_key

# Security
SECRET_KEY=your_django_secret_key
DEBUG=False
```

## 📊 Monitoring & Logging

### Logging System

The platform uses structured logging with prefixes:

```python
# Log prefixes for different components
STRATEGY_PROCESSOR_LOG_PREFIX = 'PROCESSOR => '
DEAL_PROCESSING_LOG_PREFIX = 'DEAL_PROCESSOR => '
ORDER_MANAGEMENT_LOG_PREFIX = 'ORDER_MGMT => '
STOP_ORDER_MONITOR_LOG_PREFIX = 'STOP_MONITOR => '
```

### Monitoring Tools

1. **Flower**: Celery task monitoring
   - URL: http://localhost:5555/
   - Monitor task execution
   - View task history
   - Performance metrics

2. **Django Admin**: Strategy and order management
   - URL: http://localhost:8000/admin/
   - View strategy configurations
   - Monitor deal history
   - Manage orders

3. **Application Logs**: Comprehensive logging
   ```bash
   # View logs
   docker-compose logs -f celery_worker
   docker-compose logs -f django_app
   ```

### Performance Metrics

Track strategy performance through:

- **Deal History**: All executed trades
- **Order Status**: Order execution tracking
- **Strategy Results**: Performance metrics
- **Risk Metrics**: Stop-loss and take-profit statistics

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
```bash
# Set production environment variables
export DEBUG=False
export SECRET_KEY=your_production_secret_key
export DATABASE_URL=postgresql://user:pass@host:5432/db
```

2. **Docker Deployment**
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

3. **Database Migration**
```bash
# Run migrations
docker-compose exec django_app python manage.py migrate

# Create superuser
docker-compose exec django_app python manage.py createsuperuser
```

### Scaling Considerations

- **Horizontal Scaling**: Multiple Celery workers
- **Database Optimization**: Connection pooling
- **Redis Clustering**: High availability
- **Load Balancing**: Multiple Django instances

## 🔧 Development

### Adding New Strategies

1. **Create Strategy Class**
```python
class MyStrategy(StrategyInterface):
    def initialize(self) -> bool:
        # Strategy initialization
        pass
    
    def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Signal generation logic
        pass
```

2. **Add to Factory**
```python
# In strategy_factory.py
if strategy_name == "MyStrategy":
    return MyStrategy(strategy_config_id, provider, market)
```

3. **Create Schema**
```python
# In schemas.py
class MyStrategySchema(PydanticBaseModel):
    param1: int = Field(10, description="Parameter 1")
    param2: float = Field(0.5, description="Parameter 2")
```

### Testing

```bash
# Run tests
python manage.py test

# Run specific test
python manage.py test algo.tests.StrategyTests
```

## 📚 Advanced Features

### Custom Indicators

Add custom technical indicators:

```python
def calculate_custom_indicator(df: pd.DataFrame) -> pd.Series:
    """Calculate custom technical indicator."""
    # Your indicator logic here
    return indicator_values
```

### Webhook Integration

Set up webhooks for external notifications:

```python
@shared_task
def send_webhook_notification(deal_data: Dict[str, Any]):
    """Send webhook notification for trade execution."""
    # Webhook logic here
```

### Backtesting

Run strategy backtests:

```bash
# Backtest strategy
python manage.py backtest_strategy --strategy BreakoutStrategy --symbol BTCUSDT --days 30
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the logs for debugging

## 🎯 Roadmap

- [ ] Additional exchange integrations
- [ ] More trading strategies
- [ ] Advanced backtesting
- [ ] Machine learning integration
- [ ] Mobile application
- [ ] Real-time dashboard

---

**Built with ❤️ for algorithmic trading ,   
Hope for the best,     
Shokooh Rigi**
