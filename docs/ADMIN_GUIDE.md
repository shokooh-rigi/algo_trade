# 👨‍💼 Admin Control Guide

## 📋 Table of Contents

- [Admin Overview](#admin-overview)
- [Django Admin Interface](#django-admin-interface)
- [Strategy Management](#strategy-management)
- [Risk Management Controls](#risk-management-controls)
- [Order Management](#order-management)
- [System Monitoring](#system-monitoring)
- [User Management](#user-management)
- [Configuration Management](#configuration-management)
- [Emergency Controls](#emergency-controls)
- [Reporting & Analytics](#reporting--analytics)

## 🎯 Admin Overview

The admin interface provides comprehensive control over the algorithmic trading platform, allowing administrators to:

- **Monitor** all trading activities in real-time
- **Control** strategy execution and risk parameters
- **Manage** user access and permissions
- **Configure** system settings and exchange connections
- **Respond** to emergencies with kill switches and manual overrides
- **Analyze** performance and generate reports

## 🖥️ Django Admin Interface

### Accessing Admin Panel

1. **Navigate to**: http://localhost:8000/admin/
2. **Login** with superuser credentials
3. **Dashboard** shows system overview and key metrics

### Admin Dashboard Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Admin Dashboard                               │
├─────────────────────────────────────────────────────────────────┤
│ System Status │ Active Strategies │ Recent Trades │ Alerts      │
│ ✅ Healthy    │ 3 Running         │ 15 Today      │ 2 Warnings  │
├─────────────────────────────────────────────────────────────────┤
│ Quick Actions                                                   │
│ [Start Strategy] [Stop Strategy] [Kill Switch] [View Logs]     │
├─────────────────────────────────────────────────────────────────┤
│ Performance Metrics                                             │
│ Total P&L: +$2,450 | Win Rate: 68% | Active Orders: 8          │
└─────────────────────────────────────────────────────────────────┘
```

## 📈 Strategy Management

### Strategy Configuration

#### Creating a New Strategy

1. **Navigate to**: `Strategy Configs` → `Add Strategy Config`
2. **Fill Required Fields**:
   ```python
   Strategy Name: BreakoutStrategy
   Market: BTCUSDT
   Provider: WALLEX
   Store Client: [Select API credentials]
   Is Active: ✅
   Need Historical Data: ✅
   Initial History Period Days: 250
   ```

3. **Configure Strategy Parameters**:
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
     "max_daily_trades": 10,
     "order_book_depth_threshold": 1.5
   }
   ```

#### Strategy Status Management

| Status | Description | Action Required |
|--------|-------------|-----------------|
| **Active** | Strategy is running and processing signals | Monitor performance |
| **Paused** | Strategy is stopped but configuration preserved | Resume when ready |
| **Error** | Strategy encountered an error | Check logs and fix |
| **Disabled** | Strategy is permanently disabled | Re-enable if needed |

#### Strategy Controls

```python
# Start Strategy
POST /admin/algo/strategyconfig/{id}/start/

# Stop Strategy  
POST /admin/algo/strategyconfig/{id}/stop/

# Pause Strategy
POST /admin/algo/strategyconfig/{id}/pause/

# Reset Strategy
POST /admin/algo/strategyconfig/{id}/reset/
```

### Strategy Performance Monitoring

#### Key Metrics Dashboard

```python
# Strategy Performance Metrics
{
    "total_trades": 45,
    "winning_trades": 31,
    "losing_trades": 14,
    "win_rate": 68.9,
    "total_pnl": 2450.75,
    "max_drawdown": -320.50,
    "sharpe_ratio": 1.85,
    "avg_trade_duration": "2h 15m",
    "last_signal_time": "2024-01-15T14:30:00Z",
    "current_position": "LONG BTCUSDT @ $42,150"
}
```

#### Performance Filters

- **Time Range**: Last 24h, 7d, 30d, 90d, 1y
- **Market**: Filter by trading pair
- **Strategy**: Filter by strategy type
- **Performance**: Profitable/Loss-making strategies
- **Status**: Active/Inactive strategies

## 🛡️ Risk Management Controls

### Global Risk Settings

#### System-Wide Risk Parameters

```python
# Admin System Configuration
{
    "kill_switch": False,  # Emergency stop all trading
    "max_total_exposure": 100000.0,  # Maximum total exposure
    "max_daily_loss": 5000.0,  # Maximum daily loss limit
    "max_position_size": 10000.0,  # Maximum single position
    "risk_check_interval": 60,  # Risk check frequency (seconds)
    "auto_stop_loss": True,  # Automatic stop-loss enforcement
    "position_sizing_enabled": True,  # Enable position sizing
    "cooldown_enabled": True  # Enable trade cooldowns
}
```

#### Risk Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                    Risk Management Dashboard                    │
├─────────────────────────────────────────────────────────────────┤
│ Current Exposure: $45,230 / $100,000 (45.2%)                  │
│ Daily P&L: +$1,250 / -$5,000 (Safe)                           │
│ Active Positions: 8 / 20 (40%)                                │
│ Stop Orders: 12 Active                                        │
├─────────────────────────────────────────────────────────────────┤
│ Risk Alerts                                                     │
│ ⚠️  ETHUSDT position approaching stop-loss                     │
│ ✅ All risk limits within normal range                         │
└─────────────────────────────────────────────────────────────────┘
```

### Position Management

#### Active Positions Overview

| Symbol | Side | Entry Price | Current Price | P&L | Stop Loss | Take Profit | Status |
|--------|------|-------------|---------------|-----|-----------|-------------|---------|
| BTCUSDT | LONG | $42,150 | $42,890 | +$740 | $41,950 | $42,450 | Active |
| ETHUSDT | SHORT | $2,650 | $2,620 | +$30 | $2,680 | $2,580 | Active |
| XRPUSDT | LONG | $0.58 | $0.57 | -$10 | $0.57 | $0.59 | Stop Loss Hit |

#### Manual Position Controls

```python
# Close Position Manually
POST /admin/algo/deal/{id}/close/
{
    "reason": "Manual intervention",
    "force_close": true
}

# Adjust Stop Loss
POST /admin/algo/deal/{id}/adjust_stop_loss/
{
    "new_stop_loss": 42000.0,
    "reason": "Risk management adjustment"
}

# Modify Take Profit
POST /admin/algo/deal/{id}/adjust_take_profit/
{
    "new_take_profit": 43000.0,
    "reason": "Profit target adjustment"
}
```

## 📋 Order Management

### Order Status Monitoring

#### Order Lifecycle Tracking

```
Order Created → Pending → Submitted → Filled → Completed
     ↓              ↓         ↓         ↓         ↓
   Logged        Queued    Sent to    Executed  Closed
                 for       Exchange   on        Position
                 Processing           Exchange
```

#### Order Management Interface

| Order ID | Symbol | Type | Side | Quantity | Price | Status | Created | Actions |
|----------|--------|------|------|----------|-------|--------|---------|---------|
| ORD001 | BTCUSDT | LIMIT | BUY | 0.1 | $42,150 | FILLED | 14:30 | View |
| ORD002 | BTCUSDT | STOP_MARKET | SELL | 0.1 | $41,950 | ACTIVE | 14:30 | Cancel |
| ORD003 | ETHUSDT | LIMIT | SELL | 1.0 | $2,650 | FILLED | 15:45 | View |

#### Order Controls

```python
# Cancel Order
POST /admin/algo/order/{id}/cancel/
{
    "reason": "Manual cancellation",
    "force_cancel": true
}

# Modify Order
POST /admin/algo/order/{id}/modify/
{
    "new_price": 42100.0,
    "new_quantity": 0.15,
    "reason": "Price adjustment"
}

# View Order Details
GET /admin/algo/order/{id}/details/
```

### Exchange Connection Management

#### Provider Status Monitoring

| Provider | Status | Last Check | API Calls/Min | Rate Limit | Actions |
|----------|--------|------------|---------------|------------|---------|
| Wallex | ✅ Connected | 2s ago | 45/60 | Normal | Test |
| Nobitex | ✅ Connected | 5s ago | 12/60 | Normal | Test |

#### API Key Management

```python
# Test API Connection
POST /admin/algo/storeclient/{id}/test_connection/

# Rotate API Keys
POST /admin/algo/storeclient/{id}/rotate_keys/
{
    "new_api_key": "new_key_here",
    "new_api_secret": "new_secret_here"
}

# Disable API Access
POST /admin/algo/storeclient/{id}/disable/
{
    "reason": "Security breach suspected"
}
```

## 📊 System Monitoring

### Health Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                    System Health Status                        │
├─────────────────────────────────────────────────────────────────┤
│ Services Status                                                │
│ ✅ Django App (Port 8000) - Healthy                           │
│ ✅ Celery Worker (3 instances) - Running                      │
│ ✅ Celery Beat - Active                                       │
│ ✅ Redis (Port 6379) - Connected                              │
│ ✅ PostgreSQL (Port 5432) - Connected                         │
│ ✅ Flower (Port 5555) - Monitoring                            │
├─────────────────────────────────────────────────────────────────┤
│ Performance Metrics                                            │
│ CPU Usage: 45% | Memory: 2.1GB/8GB | Disk: 15GB/100GB        │
│ Active Tasks: 12 | Queue Length: 3 | Error Rate: 0.1%        │
└─────────────────────────────────────────────────────────────────┘
```

### Log Monitoring

#### Log Categories

| Log Type | Description | Location | Retention |
|----------|-------------|----------|-----------|
| **Strategy** | Strategy execution logs | `/logs/strategy.log` | 30 days |
| **Orders** | Order placement and execution | `/logs/orders.log` | 90 days |
| **Risk** | Risk management events | `/logs/risk.log` | 1 year |
| **System** | System and service logs | `/logs/system.log` | 30 days |
| **Errors** | Error and exception logs | `/logs/errors.log` | 1 year |

#### Log Analysis Tools

```python
# View Recent Errors
GET /admin/logs/errors/?hours=24

# Search Logs
POST /admin/logs/search/
{
    "query": "ERROR",
    "time_range": "last_24h",
    "log_type": "strategy"
}

# Export Logs
GET /admin/logs/export/?type=errors&format=csv&date=2024-01-15
```

### Performance Metrics

#### System Performance Dashboard

```python
# Key Performance Indicators
{
    "response_time": {
        "api_avg": "45ms",
        "strategy_execution": "120ms",
        "order_placement": "250ms"
    },
    "throughput": {
        "requests_per_minute": 1250,
        "trades_per_hour": 45,
        "signals_generated": 89
    },
    "reliability": {
        "uptime": "99.9%",
        "error_rate": "0.1%",
        "failed_orders": "0.5%"
    }
}
```

## 👥 User Management

### User Roles and Permissions

#### Role Hierarchy

```
Super Admin
├── Full system access
├── User management
├── System configuration
└── Emergency controls

Admin
├── Strategy management
├── Order oversight
├── Risk monitoring
└── Reporting access

Trader
├── Strategy configuration
├── Position monitoring
├── Order history
└── Performance reports

Viewer
├── Read-only access
├── Performance reports
└── System status
```

#### Permission Matrix

| Feature | Super Admin | Admin | Trader | Viewer |
|---------|-------------|-------|--------|--------|
| Strategy Management | ✅ | ✅ | ✅ | ❌ |
| Order Management | ✅ | ✅ | ❌ | ❌ |
| Risk Controls | ✅ | ✅ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ |
| System Config | ✅ | ❌ | ❌ | ❌ |
| Reports | ✅ | ✅ | ✅ | ✅ |
| Emergency Controls | ✅ | ❌ | ❌ | ❌ |

### User Administration

#### Creating Users

1. **Navigate to**: `Users` → `Add User`
2. **Fill User Details**:
   ```python
   Username: trader_john
   Email: john@company.com
   First Name: John
   Last Name: Smith
   Is Active: ✅
   Is Staff: ✅ (for admin access)
   Is Superuser: ❌
   ```

3. **Assign Groups**:
   - Select appropriate role group
   - Set specific permissions
   - Configure API access if needed

#### User Activity Monitoring

```python
# User Activity Dashboard
{
    "active_users": 12,
    "last_login": "2024-01-15T14:30:00Z",
    "failed_logins": 3,
    "suspicious_activity": 0,
    "api_usage": {
        "user_john": 1250,
        "user_mary": 890,
        "user_bob": 2100
    }
}
```

## ⚙️ Configuration Management

### System Configuration

#### Global Settings

```python
# System Configuration Panel
{
    "trading_hours": {
        "start": "00:00",
        "end": "23:59",
        "timezone": "UTC",
        "weekend_trading": True
    },
    "risk_limits": {
        "max_daily_loss": 5000.0,
        "max_position_size": 10000.0,
        "max_total_exposure": 100000.0,
        "stop_loss_enforcement": True
    },
    "notifications": {
        "email_alerts": True,
        "slack_integration": True,
        "sms_alerts": False,
        "alert_thresholds": {
            "daily_loss": 0.8,
            "position_size": 0.9,
            "system_error": True
        }
    }
}
```

#### Exchange Configuration

```python
# Exchange Settings
{
    "wallex": {
        "base_url": "https://api.wallex.ir",
        "rate_limit": 60,
        "timeout": 30,
        "retry_attempts": 3,
        "api_version": "v1"
    },
    "nobitex": {
        "base_url": "https://api.nobitex.ir",
        "rate_limit": 120,
        "timeout": 30,
        "retry_attempts": 3,
        "api_version": "v1"
    }
}
```

### Environment Management

#### Environment Variables

```bash
# Production Environment
DEBUG=False
SECRET_KEY=production_secret_key
DATABASE_URL=postgresql://user:pass@prod-db:5432/algo_trade
REDIS_URL=redis://prod-redis:6379/0

# Staging Environment  
DEBUG=True
SECRET_KEY=staging_secret_key
DATABASE_URL=postgresql://user:pass@staging-db:5432/algo_trade
REDIS_URL=redis://staging-redis:6379/0

# Development Environment
DEBUG=True
SECRET_KEY=dev_secret_key
DATABASE_URL=postgresql://user:pass@dev-db:5432/algo_trade
REDIS_URL=redis://dev-redis:6379/0
```

## 🚨 Emergency Controls

### Kill Switch System

#### Global Kill Switch

```python
# Emergency Stop All Trading
POST /admin/emergency/kill_switch/
{
    "action": "activate",
    "reason": "Market volatility too high",
    "duration": "1h",
    "notify_users": True
}

# Kill Switch Status
{
    "active": True,
    "activated_at": "2024-01-15T14:30:00Z",
    "activated_by": "admin_user",
    "reason": "Market volatility too high",
    "estimated_duration": "1h",
    "affected_strategies": 5,
    "affected_positions": 8
}
```

#### Selective Kill Switches

```python
# Stop Specific Strategy
POST /admin/emergency/stop_strategy/
{
    "strategy_id": 3,
    "reason": "Strategy underperforming",
    "close_positions": False
}

# Stop All Strategies for Market
POST /admin/emergency/stop_market/
{
    "market": "BTCUSDT",
    "reason": "Market manipulation detected",
    "close_positions": True
}

# Stop All Strategies for Provider
POST /admin/emergency/stop_provider/
{
    "provider": "WALLEX",
    "reason": "Exchange API issues",
    "close_positions": False
}
```

### Emergency Procedures

#### Incident Response Workflow

```
1. Assess Situation
   ├── Check system health
   ├── Review recent trades
   ├── Analyze market conditions
   └── Identify root cause

2. Immediate Actions
   ├── Activate kill switch if needed
   ├── Close risky positions
   ├── Notify stakeholders
   └── Document incident

3. Investigation
   ├── Review logs
   ├── Analyze trade data
   ├── Check system metrics
   └── Identify patterns

4. Resolution
   ├── Fix underlying issue
   ├── Test solution
   ├── Gradually resume trading
   └── Monitor closely

5. Post-Incident
   ├── Generate report
   ├── Update procedures
   ├── Train team
   └── Implement improvements
```

## 📊 Reporting & Analytics

### Performance Reports

#### Daily Performance Report

```python
# Daily Report Template
{
    "date": "2024-01-15",
    "summary": {
        "total_trades": 45,
        "winning_trades": 31,
        "losing_trades": 14,
        "win_rate": 68.9,
        "total_pnl": 2450.75,
        "max_drawdown": -320.50
    },
    "by_strategy": {
        "BreakoutStrategy": {
            "trades": 28,
            "pnl": 1850.25,
            "win_rate": 71.4
        },
        "MeanReversionStrategy": {
            "trades": 17,
            "pnl": 600.50,
            "win_rate": 64.7
        }
    },
    "by_market": {
        "BTCUSDT": {
            "trades": 25,
            "pnl": 1200.75,
            "volume": 2.5
        },
        "ETHUSDT": {
            "trades": 20,
            "pnl": 1250.00,
            "volume": 15.8
        }
    }
}
```

#### Risk Report

```python
# Risk Assessment Report
{
    "risk_metrics": {
        "var_95": -1250.0,
        "var_99": -2100.0,
        "max_drawdown": -320.50,
        "sharpe_ratio": 1.85,
        "sortino_ratio": 2.1
    },
    "exposure_analysis": {
        "total_exposure": 45230.0,
        "by_market": {
            "BTCUSDT": 25000.0,
            "ETHUSDT": 15000.0,
            "XRPUSDT": 5230.0
        },
        "by_strategy": {
            "BreakoutStrategy": 30000.0,
            "MeanReversionStrategy": 15230.0
        }
    },
    "risk_alerts": [
        "ETHUSDT position approaching stop-loss",
        "Daily loss limit at 80%"
    ]
}
```

### Custom Reports

#### Report Builder

```python
# Custom Report Configuration
{
    "report_name": "Weekly Strategy Performance",
    "frequency": "weekly",
    "metrics": [
        "total_trades",
        "win_rate",
        "total_pnl",
        "max_drawdown",
        "sharpe_ratio"
    ],
    "filters": {
        "strategy": "BreakoutStrategy",
        "market": "BTCUSDT",
        "date_range": "last_7_days"
    },
    "format": "pdf",
    "recipients": ["admin@company.com", "trader@company.com"]
}
```

#### Export Options

- **PDF Reports**: Formatted reports for stakeholders
- **CSV Data**: Raw data for analysis
- **JSON API**: Programmatic access to data
- **Excel Files**: Spreadsheet-compatible format

---

This comprehensive admin guide provides administrators with complete control over the algorithmic trading platform, from strategy management to emergency response procedures. The interface is designed for both technical and non-technical administrators to effectively manage and monitor the trading system.
