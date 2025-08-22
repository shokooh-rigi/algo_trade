# algo/strategies/schemas.py (Pydantic v1 syntax)
from pydantic import BaseModel as PydanticBaseModel, Field, validator
from typing import Dict, Any

# Import StrategyEnum from algo.strategies.enums
from algo.strategies.enums import StrategyEnum

class StrategyMacdEmaCrossSchema(PydanticBaseModel):
    fast_ema_period: int = Field(12, description="Fast EMA period for MACD", gt=0)
    slow_ema_period: int = Field(26, description="Slow EMA period for MACD", gt=0)
    signal_ema_period: int = Field(9, description="Signal EMA period for MACD", gt=0)
    short_ema_period: int = Field(50, description="Short EMA period for EMA cross", gt=0)
    long_ema_period: int = Field(200, description="Long EMA period for EMA cross", gt=0)
    order_book_depth_threshold: float = Field(0.8, description="Order book buy/sell ratio threshold", gt=0, lt=1)

    @validator('fast_ema_period', 'short_ema_period')
    def check_ema_periods(cls, v, values):
        if 'slow_ema_period' in values and v >= values['slow_ema_period']:
            raise ValueError("fast_ema_period must be less than slow_ema_period")
        if 'long_ema_period' in values and v >= values['long_ema_period']:
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