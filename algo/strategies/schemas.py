# algo/strategies/schemas.py (Pydantic v1 syntax)
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from typing import Dict, Any, Optional

# Import StrategyEnum from algo.strategies.enums
from algo.strategies.enums import StrategyEnum

class BreakoutStrategySchema(PydanticBaseModel):
    # Breakout Strategy Parameters
    ema_fast_period: int = Field(5, description="Fast EMA period for quick signals", gt=0)
    ema_slow_period: int = Field(13, description="Slow EMA period for trend", gt=0)
    rsi_period: int = Field(14, description="RSI period for momentum confirmation", gt=0)
    rsi_overbought: float = Field(75.0, description="RSI overbought level", gt=50, le=100)
    rsi_oversold: float = Field(25.0, description="RSI oversold level", ge=0, lt=50)
    
    # Volume Analysis
    volume_period: int = Field(5, description="Volume SMA period", gt=0)
    volume_threshold: float = Field(1.2, description="Volume ratio threshold (120% of average)", gt=0)
    
    # Breakout Parameters
    breakout_period: int = Field(20, description="High/Low breakout detection period", gt=0)
    momentum_period: int = Field(3, description="Momentum calculation period", gt=0)
    
    # Risk Management
    stop_loss_percent: float = Field(0.3, description="Stop loss percentage", gt=0, le=5)
    take_profit_percent: float = Field(0.6, description="Take profit percentage", gt=0, le=10)
    max_position_size_percent: float = Field(50.0, description="Maximum position size percentage", gt=0, le=100)
    
    # Trade Management
    trade_cooldown_minutes: int = Field(30, description="Cooldown in minutes between trades", ge=0)
    max_daily_trades: int = Field(10, description="Maximum trades per day", gt=0, le=50)
    
    # Order Book Analysis (for simple signals)
    order_book_depth_threshold: float = Field(1.5, description="Order book imbalance threshold", gt=1.0)

    @validator('ema_fast_period')
    def check_ema_fast_period(cls, v, values):
        if 'ema_slow_period' in values and v >= values['ema_slow_period']:
            raise ValueError("ema_fast_period must be less than ema_slow_period")
        return v
    
    @validator('ema_slow_period')
    def check_ema_slow_period(cls, v, values):
        if 'ema_fast_period' in values and values['ema_fast_period'] >= v:
            raise ValueError("ema_fast_period must be less than ema_slow_period")
        return v
    
    @validator('take_profit_percent')
    def check_take_profit_percent(cls, v, values):
        if 'stop_loss_percent' in values and v <= values['stop_loss_percent']:
            raise ValueError("take_profit_percent must be greater than stop_loss_percent")
        return v

def get_strategy_schema(strategy_name: str):
    """
    Returns the Pydantic schema for a given strategy name.
    """
    schemas = {
        'BreakoutStrategy': BreakoutStrategySchema,
        StrategyEnum.StrategyMacdEmaCross.name: BreakoutStrategySchema,  # Map old name to new schema
    }
    return schemas.get(strategy_name, PydanticBaseModel)