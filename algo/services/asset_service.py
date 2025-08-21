import logging

from algo.models import Asset
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AssetService:
    """
    Service class for fetching and storing asset data.
    """

    @staticmethod
    def fetch_and_store_assets(provider_name: str, provider_config: dict):
        """
        Fetches assets data from the provider and stores it in the database.

        Args:
            provider_name (str): Name of the provider.
            provider_config (dict): Configuration dictionary for the provider.
        """
        logger.info(f"Starting fetch_and_store_assets for {provider_name}")

        try:
            provider = ProviderFactory.create_provider(provider_name, provider_config)
            logger.info(f"Initialized provider: {provider_name}")

            asset_data: dict = provider.fetch_assets()
            assets = asset_data.get('result', {})

            if not assets:
                logger.warning(f"No assets found for provider: {provider_name}")
                return

            for asset_key, asset_details in assets.items():
                asset, created = Asset.objects.update_or_create(
                    name=asset_key,
                    provider_name=provider_name,
                    defaults={
                        "name": asset_key,
                        "provider_name": provider_name,
                    }
                )
                logger.info(f"{'Created' if created else 'Updated'} Asset record for asset: {asset_key}")

        except Exception as e:
            logger.error(f"Failed to fetch and store asset names: {e}")
            raise e