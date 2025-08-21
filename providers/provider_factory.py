import logging

from providers.provider_interface import IProvider
from providers.providers_enum import ProviderEnum
from providers.wallex_provider import WallexProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory class responsible for creating provider instances based on the provider name.
    """

    @staticmethod
    def create_provider(provider_name: str, provider_config: dict) -> IProvider:
        """
        Create and return an instance of a provider based on the provider name.

        Args:
            provider_name (str): The name of the provider.
            provider_config (dict): Configuration for the provider, such as API keys.

        Returns:
            IProvider: An instance of a provider that implements IProvider.

        Raises:
            ValueError: If the provider name is not recognized.
        """
        if provider_name == ProviderEnum.WALLEX.value:
            return WallexProvider(provider_config)

        logger.error(f"Unknown provider: {provider_name}")
        raise ValueError(f"Unknown provider: {provider_name}")
