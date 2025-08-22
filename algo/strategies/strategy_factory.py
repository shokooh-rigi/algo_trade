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
    def create_strategy(strategy_name: str, config: dict, provider: ProviderEnum, market: str) -> StrategyInterface:
        """
        Creates and returns an instance of a specified trading strategy.

        Args:
            strategy_name (str): The name of the strategy to create (from StrategyEnum).
            config (dict): Configuration parameters specific to the strategy.
            provider (ProviderEnum): The enum representing the trading provider (e.g., WALLEX, NOBITEX).
            market (str): The trading pair symbol (e.g., "BTCUSDT").

        Returns:
            StrategyInterface: An instance of the requested strategy.

        Raises:
            ValueError: If an unknown strategy_name is provided.
        """
        if strategy_name == StrategyEnum.StrategyMacdEmaCross.name:
            # Pass the provider (enum) and market (string) directly to the constructor
            return StrategyMacdEmaCross(config, provider, market)

        logger.error(f"Unknown strategy: {strategy_name}")
        raise ValueError(f"Unknown strategy: {strategy_name}")