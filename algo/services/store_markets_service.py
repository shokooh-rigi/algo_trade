import logging

from algo.models import Market
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class StoreMarketsFetcherService:
    def __init__(self, provider_name: str, provider_config: dict):
        self.provider_name = provider_name
        self.provider = ProviderFactory.create_provider(provider_name, provider_config)

    def store_data(self):
        """
        Fetches market data, maps it to a standard schema, and stores it.
        """
        try:
            # Step 1: Fetch the raw data from the provider
            markets_data: dict = self.provider.fetch_markets()

            # Step 2: Use a mapping function to convert the raw data to a standard format
            # This is where you would call the specific mapper for each provider
            standardized_markets = self.provider.map_markets_to_schema(markets_data)

            # Step 3: Iterate over the standardized data and save to the database
            for market_data in standardized_markets:
                market, created = Market.objects.get_or_create(
                    symbol=market_data['symbol'],
                    provider=self.provider_name,
                    defaults=market_data
                )

                if created:
                    logger.info(
                        f"Created new Market record for symbol: {market_data['symbol']} from {self.provider_name}")
                else:
                    logger.info(f"Market symbol '{market_data['symbol']}' already exists. Updating data...")
                    for key, value in market_data.items():
                        setattr(market, key, value)
                    market.save()

        except Exception as e:
            logger.error(f"Failed to store market data for {self.provider_name}: {e}", exc_info=True)
            raise
