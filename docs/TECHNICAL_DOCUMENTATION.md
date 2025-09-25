# 🔧 Technical Documentation

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Strategy Framework](#strategy-framework)
- [Risk Management System](#risk-management-system)
- [Order Management](#order-management)
- [API Integration](#api-integration)
- [Database Schema](#database-schema)
- [Celery Tasks](#celery-tasks)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Security Considerations](#security-considerations)

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Django Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Strategy Layer  │  Service Layer  │  Model Layer  │  API Layer  │
│                  │                 │               │             │
│ • Breakout       │ • Strategy      │ • Deal        │ • REST API  │
│   Strategy       │   Processor     │ • Order       │ • Admin     │
│ • Strategy       │ • Order         │ • Market      │   Interface │
│   Interface      │   Management    │ • Strategy    │             │
│ • Strategy       │ • Deal          │   Config      │             │
│   Factory        │   Processor     │ • Store       │             │
│                  │ • Stop Order    │   Client      │             │
│                  │   Monitor       │               │             │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Celery Task Queue                          │
├─────────────────────────────────────────────────────────────────┤
│ • Strategy Processing  │ • Deal Processing  │ • Order Monitoring │
│ • Market Data Fetching │ • Stop Order       │ • System Health    │
│ • Asset Management     │   Monitoring       │   Checks           │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      External Services                          │
├─────────────────────────────────────────────────────────────────┤
│ • Redis (Message Broker)  │ • PostgreSQL (Database)           │
│ • Wallex API (Trading)    │ • Nobitex API (Historical Data)    │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. Strategy Framework

#### StrategyInterface (Abstract Base Class)

```python
class StrategyInterface(ABC):
    """
    Abstract base class for all trading strategies.
    Defines the contract that all strategies must implement.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the strategy with configuration and historical data."""
        pass
    
    @abstractmethod
    def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute strategy logic and generate trading signals."""
        pass
    
    @abstractmethod
    def get_results(self) -> Dict[str, Any]:
        """Return strategy execution results and performance metrics."""
        pass
```

#### StrategyFactory

```python
class StrategyFactory:
    """
    Factory pattern implementation for creating strategy instances.
    Handles strategy instantiation based on configuration.
    """
    
    @staticmethod
    def create_strategy(strategy_config_id: int, provider: ProviderEnum, market: str) -> StrategyInterface:
        """Create strategy instance based on configuration."""
        strategy_config = StrategyConfig.objects.get(id=strategy_config_id)
        strategy_name = strategy_config.strategy
        
        if strategy_name == StrategyEnum.BreakoutStrategy.name:
            return BreakoutStrategy(strategy_config_id, provider, market)
        
        raise ValueError(f"Unknown strategy: {strategy_name}")
```

### 2. Service Layer

#### StrategyProcessorService

```python
class StrategyProcessorService:
    """
    Orchestrates strategy execution across all active strategies.
    Handles market data fetching and strategy lifecycle management.
    """
    
    def process_all_strategies(self) -> Dict[str, Any]:
        """Process all active strategies."""
        active_strategies = self._get_active_strategies()
        results = []
        
        for strategy_config in active_strategies:
            result = self._process_single_strategy(strategy_config)
            results.append(result)
        
        return {
            "status": "success",
            "total_strategies": len(active_strategies),
            "processed": len([r for r in results if r.get("status") == "success"]),
            "errors": len([r for r in results if r.get("status") == "error"]),
            "details": results
        }
```

#### OrderManagementService

```python
class OrderManagementService:
    """
    Handles order placement, tracking, and execution.
    Manages the complete order lifecycle from creation to completion.
    """
    
    def place_order_for_deal(self, deal: Deal) -> Dict[str, Any]:
        """Place an order for a given deal with risk management."""
        # 1. Validate deal and get market info
        # 2. Create provider instance
        # 3. Place main order
        # 4. Place stop-loss order (if configured)
        # 5. Place take-profit order (if configured)
        # 6. Update deal status
        pass
    
    def _place_stop_loss_order(self, deal: Deal, market: Market, store_client: StoreClient, handler) -> Optional[Dict[str, Any]]:
        """Place stop-loss order on exchange."""
        # Create STOP_MARKET order for immediate execution
        pass
    
    def update_trailing_stop(self, deal: Deal, current_price: float) -> Optional[Dict[str, Any]]:
        """Update trailing stop based on current price."""
        # Cancel old stop-loss order
        # Place new stop-loss order at updated price
        pass
```

### 3. Risk Management System

#### Stop Order Monitor Service

```python
class StopOrderMonitorService:
    """
    Monitors and manages stop-loss and take-profit orders.
    Handles trailing stops and order execution detection.
    """
    
    def monitor_active_deals(self) -> Dict[str, Any]:
        """Monitor all active deals with stop orders."""
        active_deals = Deal.objects.filter(
            is_active=True,
            is_processed=True,
            stop_loss_price__isnull=False
        )
        
        for deal in active_deals:
            # Update trailing stops
            # Check order execution
            # Manage position closure
            pass
```

#### Risk Controls Implementation

```python
# Position Sizing
position_size_percent = min(confidence * 50, 50)  # Max 50%

# Cooldown Management
def _is_in_cooldown(self) -> bool:
    cooldown_minutes = getattr(self.strategy_params, 'trade_cooldown_minutes', 30)
    time_since_last_trade = datetime.now() - self.last_trade_time
    return time_since_last_trade.total_seconds() < (cooldown_minutes * 60)

# Daily Trade Limits
def _get_today_trade_count(self) -> int:
    today = datetime.now().date()
    return Deal.objects.filter(
        strategy_name=self.strategy_config.strategy,
        market_symbol=self.market_symbol,
        created_at__date=today
    ).count()
```

## 📊 Data Flow

### 1. Strategy Execution Flow

```
Market Data Request
        │
        ▼
┌─────────────────┐
│   Fetch Data    │
│ • OHLCV Data    │
│ • Order Book    │
│ • Current Price │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Strategy Init  │
│ • Load Config   │
│ • Fetch History │
│ • Calculate     │
│   Indicators    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Signal Generation│
│ • EMA Cross     │
│ • RSI Check     │
│ • Volume Check  │
│ • Breakout      │
│   Detection     │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Risk Assessment │
│ • Position Size │
│ • Cooldown      │
│ • Daily Limits  │
│ • Stop Loss     │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  Deal Creation  │
│ • Save to DB    │
│ • Queue for     │
│   Processing    │
└─────────────────┘
```

### 2. Order Processing Flow

```
Deal Created
        │
        ▼
┌─────────────────┐
│ Deal Processor  │
│ • Validate Deal │
│ • Check Rules   │
│ • Queue Order   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Order Management│
│ • Get Market    │
│   Info          │
│ • Create        │
│   Provider      │
│ • Place Orders  │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Exchange API    │
│ • Main Order    │
│ • Stop Loss     │
│ • Take Profit   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Order Tracking  │
│ • Save Order    │
│ • Update Deal   │
│ • Monitor       │
│   Execution     │
└─────────────────┘
```

## 🎯 Strategy Framework

### Breakout Strategy Implementation

```python
class BreakoutStrategy(StrategyInterface):
    """
    Breakout trading strategy with advanced risk management.
    
    Signal Generation:
    1. Price breaks above/below 20-period high/low
    2. EMA crossover confirmation (5/13)
    3. RSI not in extreme territory
    4. Volume above threshold (120% of average)
    
    Risk Management:
    - Automatic stop-loss (0.3%)
    - Automatic take-profit (0.6%)
    - Position sizing based on confidence
    - Cooldown periods between trades
    - Daily trade limits
    """
    
    def _generate_breakout_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate breakout trading signals."""
        current_price = market_data.get('mid_price', 0)
        latest_data = self.price_history.iloc[-1]
        
        # BUY signal: Price breaks above high + EMA cross + RSI not overbought
        if (current_price > latest_data['high_20'] and 
            latest_data['ema_5'] > latest_data['ema_13'] and 
            latest_data['rsi'] < 75 and 
            latest_data['volume_ratio'] > 1.2):
            
            return {
                'side': ProcessedSideEnum.BUY,
                'reason': 'High breakout + EMA cross',
                'confidence': 0.8
            }
        
        # SELL signal: Price breaks below low + EMA cross + RSI not oversold
        elif (current_price < latest_data['low_20'] and 
              latest_data['ema_5'] < latest_data['ema_13'] and 
              latest_data['rsi'] > 25 and 
              latest_data['volume_ratio'] > 1.2):
            
            return {
                'side': ProcessedSideEnum.SELL,
                'reason': 'Low breakout + EMA cross',
                'confidence': 0.8
            }
        
        return None
```

### Technical Indicators

```python
def _calculate_breakout_indicators(self) -> bool:
    """Calculate technical indicators for breakout strategy."""
    try:
        # EMA calculations
        self.price_history['ema_5'] = ta.ema(self.price_history['close'], length=5)
        self.price_history['ema_13'] = ta.ema(self.price_history['close'], length=13)
        
        # RSI calculation
        self.price_history['rsi'] = ta.rsi(self.price_history['close'], length=14)
        
        # Volume analysis
        self.price_history['volume_sma'] = ta.sma(self.price_history['volume'], length=5)
        self.price_history['volume_ratio'] = self.price_history['volume'] / self.price_history['volume_sma']
        
        # Breakout levels
        self.price_history['high_20'] = self.price_history['high'].rolling(window=20).max()
        self.price_history['low_20'] = self.price_history['low'].rolling(window=20).min()
        
        # Momentum
        self.price_history['momentum'] = self.price_history['close'].pct_change(periods=3)
        
        return True
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return False
```

## 🛡️ Risk Management System

### Exchange-Level Stop Orders

```python
def _place_stop_loss_order(self, deal: Deal, market: Market, store_client: StoreClient, handler) -> Optional[Dict[str, Any]]:
    """Place stop-loss order on exchange."""
    try:
        # Determine stop-loss side (opposite of main order)
        stop_loss_side = "SELL" if deal.side == "BUY" else "BUY"
        
        # Adjust prices according to market rules
        adjusted_stop_price = market.adjust_price(float(deal.stop_loss_price))
        adjusted_quantity = market.adjust_quantity(float(deal.quantity))
        
        # Create STOP_MARKET order for immediate execution
        stop_loss_request = CreateOrderRequestSchema(
            symbol=deal.market_symbol,
            side=stop_loss_side,
            type="STOP_MARKET",  # Immediate execution when triggered
            quantity=str(adjusted_quantity),
            stopPrice=str(adjusted_stop_price)  # Trigger price
        )
        
        # Place order on exchange
        stop_loss_response = handler.create_order(
            api_key=store_client.api_key,
            request=stop_loss_request
        )
        
        # Save order to database
        stop_loss_order = Order.objects.create(
            store_client=store_client,
            deal=deal,
            symbol=deal.market_symbol,
            type="STOP_MARKET",
            side=stop_loss_side,
            price=deal.stop_loss_price,
            quantity=deal.quantity,
            status="NEW",
            active=True,
            client_order_id=stop_loss_response.order_id
        )
        
        # Update deal with stop-loss order ID
        deal.stop_loss_order_id = stop_loss_response.order_id
        deal.save()
        
        return {
            "status": "success",
            "order_id": stop_loss_order.id,
            "client_order_id": stop_loss_response.order_id,
            "price": adjusted_stop_price,
            "side": stop_loss_side
        }
        
    except Exception as e:
        logger.error(f"Error placing stop-loss order: {e}")
        return None
```

### Trailing Stop Implementation

```python
def update_trailing_stop(self, deal: Deal, current_price: float) -> Optional[Dict[str, Any]]:
    """Update trailing stop based on current price movement."""
    try:
        if not deal.trailing_stop_enabled or not deal.trailing_stop_distance:
            return None
        
        # Calculate new stop-loss price based on trailing distance
        if deal.side == "BUY":
            # For long positions, trail upward
            new_stop_price = current_price * (1 - deal.trailing_stop_distance / 100)
            # Only update if new stop is higher than current
            if new_stop_price > deal.stop_loss_price:
                return self._update_stop_loss_price(deal, new_stop_price)
        else:
            # For short positions, trail downward
            new_stop_price = current_price * (1 + deal.trailing_stop_distance / 100)
            # Only update if new stop is lower than current
            if new_stop_price < deal.stop_loss_price:
                return self._update_stop_loss_price(deal, new_stop_price)
        
        return None
        
    except Exception as e:
        logger.error(f"Error updating trailing stop: {e}")
        return None
```

## 📊 Database Schema

### Deal Model

```python
class Deal(BaseModel):
    """Represents a trading opportunity generated by a strategy."""
    
    # Basic Information
    client_deal_id = models.UUIDField(default=uuid.uuid4, unique=True)
    strategy_name = models.CharField(max_length=100)
    provider_name = models.CharField(max_length=50)
    market_symbol = models.CharField(max_length=20)
    
    # Trade Details
    side = models.CharField(max_length=5, choices=OrderSide.CHOICES)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    quantity = models.DecimalField(max_digits=20, decimal_places=8)
    
    # State Management
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=StrategyState.choices())
    is_processed = models.BooleanField(default=False)
    processed_side = models.CharField(max_length=35, choices=ProcessedSideEnum.choices())
    
    # Risk Management Fields
    stop_loss_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_loss_order_id = models.CharField(max_length=100, null=True, blank=True)
    take_profit_order_id = models.CharField(max_length=100, null=True, blank=True)
    trailing_stop_enabled = models.BooleanField(default=False)
    trailing_stop_distance = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
```

### Order Model

```python
class Order(BaseModel):
    """Represents an order placed on an exchange."""
    
    # Relationships
    deal = models.ForeignKey(Deal, on_delete=CASCADE, related_name='orders')
    store_client = models.ForeignKey(StoreClient, on_delete=CASCADE)
    
    # Order Details
    symbol = models.CharField(max_length=20)
    type = models.CharField(max_length=20, choices=OrderType.CHOICES)
    side = models.CharField(max_length=5, choices=OrderSide.CHOICES)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    # Execution Details
    orig_qty = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    orig_sum = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    executed_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    executed_qty = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    executed_sum = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    executed_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=OrderStatus.CHOICES)
    active = models.BooleanField(default=True)
    client_order_id = models.CharField(max_length=100, unique=True)
    timestamp_created_at = models.CharField(max_length=50)
```

## ⚡ Celery Tasks

### Task Architecture

```python
# Strategy Processing Task
@shared_task(bind=True)
def strategy_processor_task(self):
    """Process all active strategies."""
    processor = StrategyProcessorService()
    return processor.process_all_strategies()

# Deal Processing Task
@shared_task(bind=True)
def deal_processor_task(self):
    """Process unprocessed deals."""
    processor = DealProcessorService()
    return processor.process_unprocessed_deals()

# Stop Order Monitoring Task
@shared_task(bind=True)
def monitor_stop_orders_task(self):
    """Monitor stop-loss and take-profit orders."""
    monitor = StopOrderMonitorService()
    return monitor.monitor_active_deals()
```

### Task Scheduling

```python
# Celery Beat Configuration
CELERY_BEAT_SCHEDULE = {
    'strategy-processor': {
        'task': 'algo.tasks.strategy_processor_task',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'deal-processor': {
        'task': 'algo.tasks.deal_processor_task',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
    'stop-order-monitor': {
        'task': 'algo.tasks.monitor_stop_orders_task',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
}
```

## 🔌 API Integration

### Provider Interface

```python
class IProvider(ABC):
    """Abstract base class for exchange providers."""
    
    @abstractmethod
    def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """Get order book data for a symbol."""
        pass
    
    @abstractmethod
    def create_order(self, api_key: str, order_request_schema: CreateOrderRequestSchema) -> OrderResponseSchema:
        """Create an order on the exchange."""
        pass
    
    @abstractmethod
    def cancel_order(self, api_key: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order on the exchange."""
        pass
```

### Wallex Provider Implementation

```python
class WallexProvider(IProvider):
    """Wallex exchange provider implementation."""
    
    def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """Get order book data from Wallex."""
        url = f"{settings.WALLEX_BASE_URL}/v1/market/orderbook/{symbol}"
        response = requests.get(url)
        return response.json()
    
    def create_order(self, api_key: str, order_request_schema: CreateOrderRequestSchema) -> OrderResponseSchema:
        """Create order on Wallex."""
        url = f"{settings.WALLEX_BASE_URL}/v1/account/orders"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'symbol': order_request_schema.symbol,
            'side': order_request_schema.side,
            'type': order_request_schema.type,
            'quantity': order_request_schema.quantity,
            'price': order_request_schema.price
        }
        
        response = requests.post(url, json=data, headers=headers)
        return OrderResponseSchema(**response.json())
```

## 🚨 Error Handling

### Exception Handling Strategy

```python
class TradingException(Exception):
    """Base exception for trading-related errors."""
    pass

class InsufficientDataException(TradingException):
    """Raised when insufficient data is available for strategy execution."""
    pass

class OrderExecutionException(TradingException):
    """Raised when order execution fails."""
    pass

class RiskManagementException(TradingException):
    """Raised when risk management rules are violated."""
    pass
```

### Error Recovery

```python
def execute_strategy_with_retry(self, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Execute strategy with retry logic."""
    for attempt in range(max_retries):
        try:
            return self.execute(market_data)
        except InsufficientDataException as e:
            logger.warning(f"Attempt {attempt + 1}: Insufficient data - {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(5)  # Wait before retry
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return None
    
    return None
```

## ⚡ Performance Optimization

### Database Optimization

```python
# Use select_related for foreign key optimization
active_strategies = StrategyConfig.objects.select_related('market', 'store_client').filter(
    is_active=True
)

# Use prefetch_related for many-to-many relationships
deals_with_orders = Deal.objects.prefetch_related('orders').filter(
    is_active=True
)

# Use database indexes for frequently queried fields
class Deal(BaseModel):
    market_symbol = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
```

### Caching Strategy

```python
from django.core.cache import cache

def get_market_data_cached(symbol: str, provider: str) -> Dict[str, Any]:
    """Get market data with caching."""
    cache_key = f"market_data_{provider}_{symbol}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # Fetch fresh data
    market_data = fetch_market_data(symbol, provider)
    
    # Cache for 30 seconds
    cache.set(cache_key, market_data, 30)
    
    return market_data
```

### Memory Management

```python
def cleanup_price_history(self):
    """Clean up old price history data to manage memory."""
    if len(self.price_history) > 1000:  # Keep only last 1000 candles
        self.price_history = self.price_history.tail(500)
        logger.info(f"Cleaned up price history for {self.market_symbol}")
```

## 🔒 Security Considerations

### API Key Management

```python
class StoreClient(BaseModel):
    """Store client credentials securely."""
    
    provider = models.CharField(max_length=50)
    api_key = models.CharField(max_length=500)
    api_secret = models.CharField(max_length=500, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Encrypt sensitive data before saving
        if self.api_key:
            self.api_key = encrypt_data(self.api_key)
        if self.api_secret:
            self.api_secret = encrypt_data(self.api_secret)
        super().save(*args, **kwargs)
```

### Input Validation

```python
class BreakoutStrategySchema(PydanticBaseModel):
    """Pydantic schema for strategy validation."""
    
    ema_fast_period: int = Field(5, gt=0, le=50)
    ema_slow_period: int = Field(13, gt=0, le=200)
    stop_loss_percent: float = Field(0.3, gt=0, le=5)
    take_profit_percent: float = Field(0.6, gt=0, le=10)
    
    @validator('ema_fast_period')
    def check_ema_fast_period(cls, v, values):
        if 'ema_slow_period' in values and v >= values['ema_slow_period']:
            raise ValueError("ema_fast_period must be less than ema_slow_period")
        return v
```

### Rate Limiting

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h', method='POST')
def create_strategy_config(request):
    """Rate limit strategy configuration creation."""
    # Strategy creation logic
    pass
```

---

This technical documentation provides comprehensive insights into the system architecture, implementation details, and best practices for maintaining and extending the algorithmic trading platform.
