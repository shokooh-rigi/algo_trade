import logging
import time
import sentry_sdk

from celery import shared_task
from django.db import models
from django.utils import timezone
from pytz import timezone as pytz_timezone
from datetime import timedelta
from celery.exceptions import MaxRetriesExceededError

from algo.models import AdminSystemConfig
from algo.services.asset_service import AssetService
from algo.services.inquiry_order_service import InquiryOrderService
from algo_trade import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def inquiry_orders_task(self):
    """
    Celery task to process inquiry orders.
    """
    logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Start inquiry orders task.")
    try:
        system_configs = AdminSystemConfig.get_instance()
        system_kill_switch = system_configs.get_value("kill_switch")
        if system_kill_switch:
            logger.warning(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Inquiry orders task is disabled by kill switch")
            return 'Inquiry orders task is disabled by kill switch.'

        inquiry_order_service = InquiryOrderService()
        inquiry_order_service.inquiry_all_orders()
        logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Inquiry orders task completed successfully.")

    except Exception as e:
        logger.error(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Inquiry orders task encountered an error: {e}",
                     exc_info=True)


@shared_task(bind=True, max_retries=5, default_retry_delay=300)
def fetch_and_store_assets(self,provider_name:str, provider_config:dict):
    """
    Celery task to fetch asset data from the provider.
    """
    logger.info(f"{settings.ASSET_LOG_PREFIX} Starting fetch_asset_data task.")
    try:
        system_configs = AdminSystemConfig.get_instance()
        system_kill_switch = system_configs.get_value("kill_switch")
        if system_kill_switch:
            logger.warning(f"{settings.ASSET_LOG_PREFIX} Asset data fetching is disabled by kill switch")
            return 'Asset data fetching is disabled by kill switch.'

        AssetService.fetch_and_store_assets(
            provider_name=provider_name,
            provider_config=provider_config,
        )

        logger.info(f"{settings.ASSET_LOG_PREFIX} Asset data fetched successfully.")

    except Exception as e:
        logger.error(f"{settings.ASSET_LOG_PREFIX} Error fetching asset data: {e}", exc_info=True)
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error(f"{settings.ASSET_LOG_PREFIX} Task retry limit exceeded.")
