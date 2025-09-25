# algo/strategies/schemas.py (Pydantic v1 syntax)
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from typing import Dict, Any, Optional

# Import StrategyEnum from algo.strategies.enums
from algo.strategies.enums import StrategyEnum

class StrategyMacdEmaCrossSchema(PydanticBaseModel):
    fast_ema_period: int = Field(12, description="Fast EMA period for MACD", gt=0)
    slow_ema_period: int = Field(26, description="Slow EMA period for MACD", gt=0)
    signal_ema_period: int = Field(9, description="Signal EMA period for MACD", gt=0)
    short_ema_period: int = Field(50, description="Short EMA period for EMA cross", gt=0)
    long_ema_period: int = Field(200, description="Long EMA period for EMA cross", gt=0)
    order_book_depth_threshold: float = Field(0.8, description="Order book buy/sell ratio threshold", gt=0, lt=1)

    # New optional tuning fields
    htf_resolution: str = Field('4h', description="Higher timeframe resolution for confirmation")
    htf_ema_length: int = Field(50, description="EMA length on higher timeframe", gt=1)
    min_adx: float = Field(18.0, description="Minimum ADX to consider trend valid", ge=0)
    min_atr_percent: float = Field(0.15, description="Minimum ATR% of price to consider volatility acceptable", ge=0)
    volume_percentile_window: int = Field(50, description="Lookback window for volume percentile", gt=5)
    volume_percentile_threshold: int = Field(70, description="Percentile threshold (0-100) for volume confirmation", ge=0, le=100)
    trade_cooldown_minutes: int = Field(45, description="Cooldown in minutes between opposite trades", ge=0)

    @validator('fast_ema_period')
    def check_fast_ema_period(cls, v, values):
        if 'slow_ema_period' in values and v >= values['slow_ema_period']:
            raise ValueError("fast_ema_period must be less than slow_ema_period")
        return v
    
    @validator('short_ema_period')
    def check_short_ema_period(cls, v, values):
        if 'long_ema_period' in values and v >= values['long_ema_period']:
            raise ValueError("short_ema_period must be less than long_ema_period")
        return v
    
    @validator('slow_ema_period')
    def check_slow_ema_period(cls, v, values):
        if 'fast_ema_period' in values and values['fast_ema_period'] >= v:
            raise ValueError("fast_ema_period must be less than slow_ema_period")
        return v
    
    @validator('long_ema_period')
    def check_long_ema_period(cls, v, values):
        if 'short_ema_period' in values and values['short_ema_period'] >= v:
            raise ValueError("short_ema_period must be less than long_ema_period")
        return v


def get_strategy_schema(strategy_name: str):
    """
    Returns the Pydantic schema for a given strategy name.
    """
    schemas = {
        StrategyEnum.StrategyMacdEmaCross.name: StrategyMacdEmaCrossSchema
        # Add other strategy schemas here
    }
    return schemas.get(strategy_name, PydanticBaseModel)