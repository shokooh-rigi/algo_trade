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
    def create_strategy(strategy_config_id: int, provider: ProviderEnum, market: str) -> StrategyInterface:
        # Fetch the StrategyConfig instance to get the strategy_name
        try:
            strategy_config = StrategyConfig.objects.get(id=strategy_config_id)
            strategy_name = strategy_config.strategy
        except StrategyConfig.DoesNotExist:
            raise ValueError(f"StrategyConfig with ID {strategy_config_id} not found.")

        if strategy_name == StrategyEnum.StrategyMacdEmaCross.name:
            return StrategyMacdEmaCross(strategy_config_id, provider, market)
        logger.error(f"Unknown strategy: {strategy_name}")
        raise ValueError(f"Unknown strategy: {strategy_name}")