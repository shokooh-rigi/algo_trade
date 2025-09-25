# 🎛️ Admin Control Panel Documentation

## 📋 Table of Contents

- [Admin Interface Overview](#admin-interface-overview)
- [Dashboard Features](#dashboard-features)
- [Strategy Management](#strategy-management)
- [Deal Management](#deal-management)
- [Order Management](#order-management)
- [Risk Management Controls](#risk-management-controls)
- [Emergency Controls](#emergency-controls)
- [System Monitoring](#system-monitoring)
- [User Management](#user-management)
- [Reporting & Analytics](#reporting--analytics)

## 🖥️ Admin Interface Overview

The admin control panel provides comprehensive management capabilities for the algorithmic trading platform. Access the admin interface at:

**URL**: http://localhost:8000/admin/

### Key Features

- **Real-time Dashboard**: Live trading metrics and system status
- **Strategy Control**: Start, stop, pause, and configure trading strategies
- **Deal Management**: Monitor and control active trading positions
- **Order Oversight**: Track and manage exchange orders
- **Risk Controls**: Monitor and adjust risk management settings
- **Emergency Controls**: Kill switches and emergency procedures
- **System Monitoring**: Health checks and performance metrics

## 📊 Dashboard Features

### Main Dashboard

The admin dashboard provides a comprehensive overview of the trading platform:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Platform Dashboard                    │
├─────────────────────────────────────────────────────────────────┤
│ System Status: 🟢 Running | 🚨 Emergency Stop                  │
├─────────────────────────────────────────────────────────────────┤
│ Quick Actions                                                   │
│ [⚙️ Manage Strategies] [📊 View Deals] [📋 View Orders]        │
│ [🚨 Emergency Stop] [✅ Resume Trading]                        │
├─────────────────────────────────────────────────────────────────┤
│ Trading Metrics                                                 │
│ Total Deals: 1,245 | Active Deals: 8 | Orders: 2,890          │
│ Active Strategies: 3 | Risk Coverage: 95%                     │
├─────────────────────────────────────────────────────────────────┤
│ Recent Activity (Last 24h)                                     │
│ • BreakoutStrategy - BTCUSDT BUY 0.1 @ $42,150 (2h ago)       │
│ • BreakoutStrategy - ETHUSDT SELL 1.0 @ $2,650 (4h ago)       │
└─────────────────────────────────────────────────────────────────┘
```

### Dashboard Metrics

| Metric | Description | Status Indicators |
|--------|-------------|-------------------|
| **Total Deals** | All-time trading opportunities | Blue (Info) |
| **Active Deals** | Currently open positions | Orange (Warning) if > 0 |
| **Total Orders** | Orders placed on exchanges | Blue (Info) |
| **Active Strategies** | Strategies currently running | Green (Success) if > 0 |

### Real-time Updates

- **Auto-refresh**: Dashboard updates every 60 seconds
- **Live Metrics**: Real-time trading statistics
- **Status Indicators**: Color-coded system health
- **Recent Activity**: Latest trading events

## ⚙️ Strategy Management

### Strategy Configuration

#### Creating a New Strategy

1. **Navigate to**: `Strategy Configs` → `Add Strategy Config`
2. **Configure Basic Settings**:
   ```python
   Strategy: BreakoutStrategy
   Market: BTCUSDT
   Provider: WALLEX
   Store Client: [Select API credentials]
   Is Active: ✅
   ```

3. **Set Strategy Parameters**:
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

#### Strategy Actions

| Action | Description | Use Case |
|--------|-------------|----------|
| **Start** | Activate strategy and begin trading | Initial deployment |
| **Stop** | Deactivate strategy and halt trading | Maintenance or issues |
| **Pause** | Stop new trades but keep existing positions | Temporary halt |
| **Reset** | Reset strategy state to initial | After configuration changes |

#### Strategy Performance Monitoring

```python
# Performance Summary Display
{
    "strategy": "BreakoutStrategy",
    "market": "BTCUSDT",
    "total_trades": 45,
    "active_trades": 3,
    "processed_trades": 42,
    "state": "RUNNING",
    "win_rate": 68.9,
    "last_signal": "2024-01-15T14:30:00Z"
}
```

### Strategy Controls

#### Bulk Actions

- **Start Multiple Strategies**: Select strategies and use "Start selected strategies"
- **Stop Multiple Strategies**: Select strategies and use "Stop selected strategies"
- **Pause Multiple Strategies**: Select strategies and use "Pause selected strategies"
- **Reset Multiple Strategies**: Select strategies and use "Reset selected strategies"

#### Individual Strategy Management

```python
# Strategy Control API
POST /admin/algo/strategyconfig/{id}/start/
POST /admin/algo/strategyconfig/{id}/stop/
POST /admin/algo/strategyconfig/{id}/pause/
POST /admin/algo/strategyconfig/{id}/reset/
```

## 📈 Deal Management

### Deal Overview

The deal management interface provides comprehensive control over trading positions:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Deal Management                          │
├─────────────────────────────────────────────────────────────────┤
│ Filters: [Strategy] [Market] [Status] [Risk Management]        │
│ Search: [Deal ID] [Market Symbol] [Strategy Name]              │
├─────────────────────────────────────────────────────────────────┤
│ Deal ID | Strategy | Market | Side | Status | Risk | Actions   │
│ DEAL001 | Breakout | BTCUSDT| BUY  | Active | ✓ SL&TP | [Close]│
│ DEAL002 | Breakout | ETHUSDT| SELL | Active | ⚠ SL Only | [Close]│
│ DEAL003 | Breakout | XRPUSDT| BUY  | Closed | ✗ None | [View] │
└─────────────────────────────────────────────────────────────────┘
```

### Deal Status Indicators

| Status | Description | Color Code |
|--------|-------------|------------|
| **✓ Stop Loss & Take Profit** | Full risk management | Green |
| **⚠ Stop Loss Only** | Partial risk management | Orange |
| **✗ No Risk Management** | No protection | Red |

### Deal Actions

#### Individual Deal Controls

- **Close Deal**: Manually close active positions
- **Activate Deal**: Reactivate closed deals
- **Deactivate Deal**: Temporarily disable deals
- **Cancel Stop Orders**: Remove stop-loss and take-profit orders

#### Bulk Deal Actions

```python
# Bulk Deal Management
def close_deal(self, request, queryset):
    """Close selected deals manually."""
    closed_count = 0
    for deal in queryset:
        if deal.is_active:
            deal.is_active = False
            deal.status = StrategyState.STOPPED.value
            deal.save()
            closed_count += 1

def cancel_stop_orders(self, request, queryset):
    """Cancel stop-loss and take-profit orders."""
    cancelled_count = 0
    monitor_service = StopOrderMonitorService()
    
    for deal in queryset:
        if deal.stop_loss_order_id or deal.take_profit_order_id:
            if monitor_service.cancel_all_stop_orders(deal):
                cancelled_count += 1
```

### Risk Management Fields

Each deal displays comprehensive risk management information:

- **Stop Loss Price**: Automatic exit price for losses
- **Take Profit Price**: Automatic exit price for profits
- **Stop Loss Order ID**: Exchange order ID for stop-loss
- **Take Profit Order ID**: Exchange order ID for take-profit
- **Trailing Stop Enabled**: Dynamic stop-loss adjustment
- **Trailing Stop Distance**: Percentage for trailing stops

## 📋 Order Management

### Order Tracking

The order management interface provides complete visibility into exchange orders:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Order Management                         │
├─────────────────────────────────────────────────────────────────┤
│ Order ID | Deal | Symbol | Type | Side | Status | Actions       │
│ ORD001   | DEAL001 | BTCUSDT | LIMIT | BUY | FILLED | [View]   │
│ ORD002   | DEAL001 | BTCUSDT | STOP_MARKET | SELL | ACTIVE | [Cancel]│
│ ORD003   | DEAL001 | BTCUSDT | LIMIT | SELL | ACTIVE | [Cancel]│
└─────────────────────────────────────────────────────────────────┘
```

### Order Types

| Order Type | Description | Use Case |
|------------|-------------|----------|
| **LIMIT** | Buy/sell at specific price | Take-profit orders |
| **MARKET** | Buy/sell at current price | Immediate execution |
| **STOP_MARKET** | Triggered market order | Stop-loss orders |

### Order Status

| Status | Description | Action Required |
|--------|-------------|-----------------|
| **NEW** | Order created but not sent | Monitor |
| **PENDING** | Order sent to exchange | Monitor |
| **ACTIVE** | Order active on exchange | Monitor |
| **FILLED** | Order completely executed | Close position |
| **CANCELLED** | Order cancelled | None |
| **REJECTED** | Order rejected by exchange | Investigate |

### Order Controls

#### Individual Order Actions

- **View Order Details**: Complete order information
- **Cancel Order**: Cancel active orders
- **Modify Order**: Change price or quantity
- **View Deal**: Link to associated deal

#### Order Monitoring

```python
# Order Status Tracking
{
    "order_id": "ORD001",
    "deal_id": "DEAL001",
    "symbol": "BTCUSDT",
    "type": "LIMIT",
    "side": "BUY",
    "price": 42150.0,
    "quantity": 0.1,
    "status": "FILLED",
    "executed_price": 42150.0,
    "executed_quantity": 0.1,
    "created_at": "2024-01-15T14:30:00Z",
    "filled_at": "2024-01-15T14:30:05Z"
}
```

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
│ Risk Coverage: 95% of positions protected                      │
│ Trailing Stops: 3 Active                                      │
│ Risk Alerts: 0 Active                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Position Risk Management

#### Risk Status Indicators

- **🟢 Protected**: Stop-loss and take-profit active
- **🟡 Partial Protection**: Only stop-loss active
- **🔴 Unprotected**: No risk management

#### Risk Actions

- **Adjust Stop Loss**: Modify stop-loss price
- **Modify Take Profit**: Change take-profit target
- **Enable Trailing Stop**: Activate dynamic stop-loss
- **Close Position**: Immediate position closure

### Risk Alerts

#### Alert Types

| Alert Type | Description | Action Required |
|------------|-------------|-----------------|
| **Position Risk** | Position approaching stop-loss | Monitor closely |
| **Daily Loss** | Approaching daily loss limit | Consider reducing exposure |
| **System Risk** | System-wide risk threshold | Review all positions |
| **Exchange Risk** | Exchange API issues | Check connectivity |

## 🚨 Emergency Controls

### Kill Switch System

#### Global Kill Switch

The emergency kill switch provides immediate system-wide trading halt:

```python
# Emergency Stop Activation
{
    "action": "activate",
    "reason": "Market volatility too high",
    "duration": "1h",
    "notify_users": True,
    "affected_strategies": 5,
    "affected_positions": 8
}
```

#### Kill Switch Status

```
┌─────────────────────────────────────────────────────────────────┐
│                    Emergency Controls                           │
├─────────────────────────────────────────────────────────────────┤
│ System Status: 🔴 EMERGENCY STOP ACTIVE                        │
│ Activated: 2024-01-15T14:30:00Z                                │
│ Reason: Market volatility too high                              │
│ Affected: 5 strategies, 8 positions                            │
├─────────────────────────────────────────────────────────────────┤
│ Actions:                                                        │
│ [✅ Resume Trading] [📊 View Impact] [📋 Generate Report]       │
└─────────────────────────────────────────────────────────────────┘
```

#### Selective Kill Switches

- **Stop Specific Strategy**: Halt individual strategy
- **Stop Market Trading**: Stop all trading for specific market
- **Stop Provider Trading**: Halt trading via specific exchange

### Emergency Procedures

#### Incident Response Workflow

1. **Assess Situation**
   - Check system health
   - Review recent trades
   - Analyze market conditions
   - Identify root cause

2. **Immediate Actions**
   - Activate kill switch if needed
   - Close risky positions
   - Notify stakeholders
   - Document incident

3. **Investigation**
   - Review logs
   - Analyze trade data
   - Check system metrics
   - Identify patterns

4. **Resolution**
   - Fix underlying issue
   - Test solution
   - Gradually resume trading
   - Monitor closely

5. **Post-Incident**
   - Generate report
   - Update procedures
   - Train team
   - Implement improvements

## 📊 System Monitoring

### Health Monitoring

#### System Status Dashboard

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

#### Health Check Endpoints

- **System Health**: `/admin/system-health/`
- **Risk Dashboard**: `/admin/risk-dashboard/`
- **Emergency Controls**: `/admin/kill-switch/`

### Performance Metrics

#### Key Performance Indicators

```python
# System Performance Metrics
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

### Log Monitoring

#### Log Categories

| Log Type | Description | Location | Retention |
|----------|-------------|----------|-----------|
| **Strategy** | Strategy execution logs | `/logs/strategy.log` | 30 days |
| **Orders** | Order placement and execution | `/logs/orders.log` | 90 days |
| **Risk** | Risk management events | `/logs/risk.log` | 1 year |
| **System** | System and service logs | `/logs/system.log` | 30 days |
| **Errors** | Error and exception logs | `/logs/errors.log` | 1 year |

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

## 📈 Reporting & Analytics

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
        }
    },
    "by_market": {
        "BTCUSDT": {
            "trades": 25,
            "pnl": 1200.75,
            "volume": 2.5
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

---

This comprehensive admin control panel documentation provides administrators with complete guidance for managing the algorithmic trading platform. The interface is designed for both technical and non-technical administrators to effectively control and monitor the trading system with institutional-grade oversight capabilities.
