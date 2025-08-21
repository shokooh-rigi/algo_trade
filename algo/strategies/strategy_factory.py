import logging

from algo.strategies.enums import StrategyEnum
from algo.strategies.sterategy_macd_ema_cross import StrategyMacdEmaCross
from algo.strategies.strategy_interface import StrategyInterface
from providers.providers_enum import ProviderEnum

logger = logging.getLogger(__name__)


class StrategyFactory:
    """
       Factory class responsible for creating strategy instances based on the strategy name.
       """
    @staticmethod
    def create_strategy(strategy_name: str, config: dict, provider:ProviderEnum, market: str) -> StrategyInterface:
        if strategy_name == StrategyEnum.StrategyMacdEmaCross.name:
            return StrategyMacdEmaCross(config, provider, market)

        logger.error(f"Unknown strategy: {strategy_name}")
        raise ValueError(f"Unknown strategy: {strategy_name}")