import logging
import time
from decimal import Decimal
from typing import Dict, Any

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from algo.models import AdminSystemConfig, StrategyConfig, Market, Deal
from algo.services.asset_service import AssetService  # Assuming this is in algo.services
from algo.services.deal_processor import DealProcessor
from algo.services.inquiry_order_service import InquiryOrderService  # Assuming this is in algo.services
from algo.services.store_markets_service import StoreMarketsFetcherService
from algo.strategies.strategy_factory import StrategyFactory
from algo.strategies.enums import StrategyState, StrategyEnum
from providers.provider_factory import ProviderFactory
from providers.providers_enum import ProviderEnum  # Assuming this is where ProviderEnum is defined
from algo_trade import settings  # For log prefixes and other settings

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_all_strategies(self):
    """
    Celery task to iterate through all active strategy configurations,
    initialize and execute each strategy.
    This task is triggered periodically by Celery Beat.
    """
    logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Starting run_all_strategies task.")

    system_configs = AdminSystemConfig.get_instance()
    if system_configs.kill_switch:
        logger.warning(
            f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Global kill switch is ON. Skipping strategy execution.")
        return "Global kill switch is ON."

    active_strategy_configs = StrategyConfig.objects.filter(
        is_active=True,
        state__in=[StrategyState.STARTED.value, StrategyState.RUNNING.value, StrategyState.UPDATED.value]
    ).select_related('market', 'store_client')  # Optimize queries to fetch related objects

    if not active_strategy_configs.exists():
        logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} No active strategy configurations found to run.")
        return "No active strategies."

    for strategy_config in active_strategy_configs:
        logger.info(
            f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Processing strategy config ID: {strategy_config.id} ({strategy_config.strategy}) for market: {strategy_config.market.symbol}")

        if not strategy_config.market or not strategy_config.store_client:
            logger.error(f"StrategyConfig {strategy_config.id} is missing linked Market or StoreClient. Skipping.")
            StrategyConfig.update_state(strategy_config.id,
                                        StrategyState.STOPPED)  # Mark as stopped due to config error
            continue

        try:
            # 1. Create strategy instance using the factory
            strategy_instance = StrategyFactory.create_strategy(
                strategy_config_id=strategy_config.id,
                provider=ProviderEnum(strategy_config.store_client.provider),  # Convert string to Enum
                market=strategy_config.market.symbol
            )

            # 2. Initialize the strategy (fetches historical data, loads params)
            # The initialize method in StrategyMacdEmaCross now takes no args, it loads from self.strategy_config_id
            strategy_instance.initialize()  # No arguments needed here anymore

            # 3. Fetch latest market data (e.g., current candle, order book)
            # This is a conceptual step. You need to implement a service to fetch real-time data.
            # In a real-world scenario, this would likely come from a WebSocket feed or a frequent REST poll.

            provider_instance = ProviderFactory.create_provider(
                provider_name=strategy_config.store_client.provider,
                provider_config={}
            )

            # Fetch latest order book
            latest_order_book_response = provider_instance.fetch_order_book_by_symbol(strategy_config.market.symbol)
            latest_order_book = latest_order_book_response.get('result', {}) if isinstance(latest_order_book_response,
                                                                                           dict) else {}

            # Fetch latest candle data (e.g., a 1-minute candle or ticker)
            # This is a placeholder. You'll need to implement a method in your provider
            # to get the *latest single candle* or *ticker price*.
            # For now, let's try to fetch the most recent 1-minute candle
            # This might return multiple candles, we just need the latest one.
            current_time_ts = int(time.time())
            # Fetch last 5 minutes of data to ensure we get at least one recent candle
            raw_latest_ohlcv = provider_instance.fetch_ohlcv_data(
                symbol=strategy_config.market.symbol,
                resolution=strategy_config.resolution,  # Use the strategy's configured resolution
                from_timestamp=current_time_ts - (5 * 60),  # Last 5 minutes
                to_timestamp=current_time_ts
            )

            latest_candle_data = {}
            if raw_latest_ohlcv:
                # Assuming raw_latest_ohlcv is a list of dicts, get the very last one
                latest_candle_data = raw_latest_ohlcv[-1]
            else:
                logger.warning(
                    f"Could not fetch latest OHLCV data for {strategy_config.market.symbol}. Using mock data.")
                # Fallback to mock data if no real data is fetched
                latest_candle_data = {
                    'time': current_time_ts,
                    'open': Decimal('10000.0'),
                    'high': Decimal('10000.0'),
                    'low': Decimal('10000.0'),
                    'close': Decimal('10000.0'),
                    'volume': Decimal('0')
                }

            # Combine latest data for strategy execution
            latest_market_data = {
                'time': latest_candle_data['time'],
                'open': Decimal(str(latest_candle_data['open'])),
                'high': Decimal(str(latest_candle_data['high'])),
                'low': Decimal(str(latest_candle_data['low'])),
                'close': Decimal(str(latest_candle_data['close'])),
                'volume': Decimal(str(latest_candle_data['volume'])),
                'order_book': latest_order_book
            }

            # IMPORTANT: Ensure 'close' price is valid and non-zero for strategy calculations
            if latest_market_data['close'] <= Decimal('0'):
                logger.error(
                    f"Latest close price is invalid ({latest_market_data['close']}) for {strategy_config.market.symbol}. Skipping strategy execution for this cycle.")
                continue  # Skip to next strategy if critical data is bad

            # 4. Execute the strategy with the latest data
            signal_result = strategy_instance.execute(latest_market_data)
            logger.info(
                f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Strategy {strategy_config.id} execution result: {signal_result}")

            # If a deal was generated by the strategy, trigger its immediate processing
            # `current_deal` is an attribute on the strategy_instance that holds the Deal object
            if strategy_instance.current_deal and not strategy_instance.current_deal.is_processed:
                logger.info(
                    f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Deal {strategy_instance.current_deal.client_deal_id} generated. Triggering immediate processing.")
                process_single_deal_task.delay(strategy_instance.current_deal.id)

        except Exception as e:
            logger.error(
                f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Error running strategy config {strategy_config.id}: {e}",
                exc_info=True)
            # Update strategy state to STOPPED if a critical error occurs
            StrategyConfig.update_state(strategy_config.id, StrategyState.STOPPED)


@shared_task(bind=True)
def fetch_and_store_markets(self, provider_name_str: str, provider_config: Dict[str, Any]):
    """
    Celery task to fetch market data from a specific provider and store it.
    This task is triggered periodically by Celery Beat.
    """
    logger.info(f"{settings.MARKET_DATA_LOG_PREFIX} Starting fetch_and_store_markets task for {provider_name_str}.")
    try:
        system_configs = AdminSystemConfig.get_instance()
        if system_configs.kill_switch:
            logger.warning(f"{settings.MARKET_DATA_LOG_PREFIX} Market data fetching is disabled by kill switch.")
            return 'Market data fetching is disabled by kill switch.'


        # Create an instance of the service and store data
        service = StoreMarketsFetcherService(provider_name=provider_name_str, provider_config=provider_config)
        service.store_data()

        logger.info(
            f"{settings.MARKET_DATA_LOG_PREFIX} Market data fetched and stored successfully for {provider_name_str}.")

    except Exception as e:
        logger.error(
            f"{settings.MARKET_DATA_LOG_PREFIX} Error fetching and storing market data for {provider_name_str}: {e}",
            exc_info=True)
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.critical(
                f"{settings.MARKET_DATA_LOG_PREFIX} Task retry limit exceeded for market data fetch for {provider_name_str}.")


@shared_task(bind=True)
def process_single_deal_task(self, deal_id: int):
    """
    Celery task to process a single deal immediately.
    """
    try:
        deal = Deal.objects.get(id=deal_id)
        from algo.services.deal_processor import DealProcessor  # Import here to avoid circular dependency
        deal_processor = DealProcessor()
        deal_processor._place_order_for_deal(deal)
        logger.info(f"Successfully processed single deal {deal_id}.")
    except Deal.DoesNotExist:
        logger.error(f"Deal with ID {deal_id} not found for single processing.")
    except Exception as e:
        logger.error(f"Error processing single deal {deal_id}: {e}", exc_info=True)

        try:
            self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            logger.critical(f"Failed to process single deal {deal_id} after multiple retries.")


@shared_task(bind=True)
def dispatch_deal_processing_task(self):
    """
    Celery task to dispatch the main DealProcessor to check for and process
    any unprocessed deals. This acts as a fallback/periodic check.
    """
    logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Starting dispatch_deal_processing_task.")
    try:
        system_configs = AdminSystemConfig.get_instance()
        if system_configs.kill_switch:
            logger.warning(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Global kill switch is ON. Skipping deal processing.")
            return "Global kill switch is ON."

        deal_processor = DealProcessor()
        deal_processor.process_unprocessed_deals() # This will find and process any deals not yet handled
        logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Dispatch deal processing task completed.")

    except Exception as e:
        logger.error(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Error in dispatch_deal_processing_task: {e}", exc_info=True)


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
            logger.critical(f"{settings.ASSET_LOG_PREFIX} Task retry limit exceeded.")


@shared_task(bind=True)
def strategy_processor_task(self):
    """
    Celery task to run the strategy processor service.
    Processes all active strategies and generates deals.
    """
    logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Starting strategy processor task.")
    try:
        from algo.services.strategy_processor_service import StrategyProcessorService
        
        processor = StrategyProcessorService()
        result = processor.process_all_strategies()
        
        logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Strategy processor task completed. "
                   f"Result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Error in strategy processor task: {e}", exc_info=True)
        try:
            self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            logger.critical(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Strategy processor task retry limit exceeded.")


@shared_task(bind=True)
def deal_processor_task(self):
    """
    Celery task to run the deal processor service.
    Processes all unprocessed deals and places orders.
    """
    logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Starting deal processor task.")
    try:
        from algo.services.deal_processor_service import DealProcessorService
        
        processor = DealProcessorService()
        result = processor.process_unprocessed_deals()
        
        logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Deal processor task completed. "
                   f"Result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Error in deal processor task: {e}", exc_info=True)
        try:
            self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            logger.critical(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Deal processor task retry limit exceeded.")


@shared_task(bind=True)
def order_inquiry_task(self):
    """
    Celery task to check order statuses and update them.
    """
    logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Starting order inquiry task.")
    try:
        from algo.services.order_management_service import OrderManagementService
        
        order_service = OrderManagementService()
        
        # Get active orders for all providers
        active_orders = order_service.get_active_orders()
        
        updated_count = 0
        for order in active_orders:
            try:
                # Check order status with provider
                provider = ProviderFactory.create_provider(
                    provider_name=order.store_client.provider,
                    provider_config={}
                )
                
                order_info = provider.order_info(
                    api_key=order.store_client.api_key,
                    client_order_id=order.client_order_id
                )
                
                # Update order status if changed
                if order_info and 'status' in order_info:
                    new_status = order_info['status']
                    if order.status != new_status:
                        order.status = new_status
                        order.save()
                        updated_count += 1
                        logger.info(f"Updated order {order.client_order_id} status to {new_status}")
                        
            except Exception as e:
                logger.error(f"Error checking order {order.client_order_id}: {e}")
                continue
        
        logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Order inquiry task completed. "
                   f"Updated {updated_count} orders.")
        return {"status": "success", "updated_orders": updated_count}
        
    except Exception as e:
        logger.error(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Error in order inquiry task: {e}", exc_info=True)
        try:
            self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            logger.critical(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Order inquiry task retry limit exceeded.")
