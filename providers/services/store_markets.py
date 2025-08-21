import logging
from typing import Dict, Any

from algo.models import Market
from providers.provider_factory import ProviderFactory
from providers.provider_interface import IProvider

logger = logging.getLogger(__name__)

class StoreMarketsFetcherService:
    """
    Service for fetching and storing market data from the provider.
    """

    def __init__(self, provider_name: str, provider_config: Dict[str, Any]):
        """
        Initialize StoreMarketsFetcherService with provider information.

        Args:
            provider_name (str): Name of the provider.
            provider_config (Dict[str, Any]): Configuration dictionary for the provider.
        """
        try:
            self.provider: IProvider = ProviderFactory.create_provider(provider_name, provider_config)
            logger.info(f"Initialized provider: {provider_name}")
        except ValueError as e:
            logger.error(f"StoreMarketsFetcherService initialization failed: {e}")
            raise

    def store_data(self):
        """
        Fetches market data from the provider and stores it in the Market model.
        """
        try:
            # Fetch markets data
            markets_data: dict = self.provider.fetch_markets()
            symbols = markets_data.get('result', {}).get('symbols', {})

            # Iterate over symbols and store in the Market model
            for symbol_name, symbol_data in symbols.items():
                market, created = Market.objects.get_or_create(
                    name=symbol_name
                )
                if created:
                    logger.info(f"Created new Market record for symbol: {symbol_name}")
                else:
                    logger.info(f"Market symbol '{symbol_name}' already exists.")

        except Exception as e:
            logger.error(f"Failed to store market data: {e}")
            raise
