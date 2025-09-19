import logging
from django.core.management.base import BaseCommand

from algo.services.asset_service import AssetService
from providers.providers_enum import ProviderEnum

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetches and stores initial asset data for all providers using Celery tasks.'

    def handle(self, *args, **options):
        self.stdout.write("Dispatching Celery tasks to fetch asset data...")

        for provider in ProviderEnum:
            self.stdout.write(f"  -> Dispatching task for provider: {provider.name}")
            AssetService.fetch_and_store_assets(
                provider_name=provider.value,
                provider_config={},
            )

        self.stdout.write(self.style.SUCCESS('Successfully dispatched all asset data tasks.'))