from enum import Enum


class StrategyEnum(Enum):
    """
    Enum for specifying the name of Strategies.
    """
    StrategyMacdEmaCross = 'StrategyMacdEmaCross'


class StrategyState(Enum):
    STARTED = 0
    RUNNING = 1
    UPDATED = 2
    STOPPED = 3
    NOT_ORDERING = 4


class ProcessedSideEnum(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    BUY_AND_SELL = 'BUY_AND_SELL'
    NONE = 'NONE'

