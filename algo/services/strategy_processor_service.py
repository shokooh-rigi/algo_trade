import logging
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional

from algo.models import StrategyConfig, Deal, Market, AdminSystemConfig
from algo.strategies.strategy_factory import StrategyFactory
from algo.strategies.enums import StrategyState, StrategyEnum
from providers.provider_factory import ProviderFactory
from providers.providers_enum import ProviderEnum
from algo_trade import settings

logger = logging.getLogger(__name__)


class StrategyProcessorService:
    """
    Service responsible for processing all active strategies.
    Fetches market data, executes strategies, and generates deals.
    """

    def __init__(self):
        self.system_configs = AdminSystemConfig.get_instance()

    def process_all_strategies(self) -> Dict[str, Any]:
        """
        Process all active strategy configurations.
        
        Returns:
            Dict containing processing results and statistics.
        """
        logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Starting strategy processing.")

        # Check global kill switch
        if self.system_configs.kill_switch:
            logger.warning(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Global kill switch is ON. Skipping strategy processing.")
            return {"status": "disabled", "reason": "Global kill switch is ON"}

        # Get active strategies
        active_strategies = self._get_active_strategies()
        if not active_strategies:
            logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} No active strategies found.")
            return {"status": "no_strategies", "count": 0}

        results = {
            "status": "success",
            "total_strategies": len(active_strategies),
            "processed": 0,
            "errors": 0,
            "deals_generated": 0,
            "details": []
        }

        # Process each strategy
        for strategy_config in active_strategies:
            try:
                result = self._process_single_strategy(strategy_config)
                results["processed"] += 1
                results["details"].append(result)
                
                if result.get("deal_generated"):
                    results["deals_generated"] += 1
                    
            except Exception as e:
                logger.error(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Error processing strategy {strategy_config.id}: {e}", exc_info=True)
                results["errors"] += 1
                results["details"].append({
                    "strategy_id": strategy_config.id,
                    "status": "error",
                    "error": str(e)
                })
                # Mark strategy as stopped on critical error
                StrategyConfig.update_state(strategy_config.id, StrategyState.STOPPED)

        logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Strategy processing completed. "
                   f"Processed: {results['processed']}, Errors: {results['errors']}, Deals: {results['deals_generated']}")
        
        return results

    def _get_active_strategies(self) -> List[StrategyConfig]:
        """Get all active strategy configurations."""
        return StrategyConfig.objects.filter(
            is_active=True,
            state__in=[StrategyState.STARTED.value, StrategyState.RUNNING.value, StrategyState.UPDATED.value]
        ).select_related('market', 'store_client')

    def _process_single_strategy(self, strategy_config: StrategyConfig) -> Dict[str, Any]:
        """
        Process a single strategy configuration.
        
        Args:
            strategy_config: The strategy configuration to process
            
        Returns:
            Dict containing processing result
        """
        logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Processing strategy {strategy_config.id} "
                   f"({strategy_config.strategy}) for market: {strategy_config.market.symbol}")

        # Validate required relationships
        if not strategy_config.market or not strategy_config.store_client:
            logger.error(f"StrategyConfig {strategy_config.id} missing Market or StoreClient. Skipping.")
            StrategyConfig.update_state(strategy_config.id, StrategyState.STOPPED)
            return {
                "strategy_id": strategy_config.id,
                "status": "error",
                "error": "Missing Market or StoreClient"
            }

        try:
            # Create strategy instance
            strategy_instance = StrategyFactory.create_strategy(
                strategy_config_id=strategy_config.id,
                provider=ProviderEnum(strategy_config.store_client.provider),
                market=strategy_config.market.symbol
            )

            # Initialize strategy
            strategy_instance.initialize()

            # Fetch latest market data
            latest_data = self._fetch_latest_market_data(strategy_config)
            if not latest_data:
                return {
                    "strategy_id": strategy_config.id,
                    "status": "error",
                    "error": "Failed to fetch market data"
                }

            # Execute strategy
            signal_result = strategy_instance.execute(latest_data)
            
            result = {
                "strategy_id": strategy_config.id,
                "market": strategy_config.market.symbol,
                "signal_result": signal_result,
                "deal_generated": False
            }

            # Check if deal was generated
            if strategy_instance.current_deal and not strategy_instance.current_deal.is_processed:
                result["deal_generated"] = True
                result["deal_id"] = strategy_instance.current_deal.id
                logger.info(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Deal {strategy_instance.current_deal.client_deal_id} "
                           f"generated for strategy {strategy_config.id}")

            return result

        except Exception as e:
            logger.error(f"{settings.STRATEGY_PROCESSOR_LOG_PREFIX} Error in strategy {strategy_config.id}: {e}", exc_info=True)
            raise

    def _fetch_latest_market_data(self, strategy_config: StrategyConfig) -> Optional[Dict[str, Any]]:
        """
        Fetch latest market data for a strategy.
        
        Args:
            strategy_config: The strategy configuration
            
        Returns:
            Dict containing latest market data or None if failed
        """
        try:
            # Create provider instance
            provider_instance = ProviderFactory.create_provider(
                provider_name=strategy_config.store_client.provider,
                provider_config={}
            )

            # Fetch order book
            order_book_response = provider_instance.fetch_order_book_by_symbol(strategy_config.market.symbol)
            order_book = order_book_response.get('result', {}) if isinstance(order_book_response, dict) else {}

            # Fetch latest OHLCV data
            current_time_ts = int(time.time())
            raw_ohlcv = provider_instance.fetch_ohlcv_data(
                symbol=strategy_config.market.symbol,
                resolution=strategy_config.resolution,
                from_timestamp=current_time_ts - (5 * 60),  # Last 5 minutes
                to_timestamp=current_time_ts
            )

            if not raw_ohlcv:
                logger.warning(f"Could not fetch OHLCV data for {strategy_config.market.symbol}")
                return None

            latest_candle = raw_ohlcv[-1]
            
            # Validate data
            if latest_candle.get('close', 0) <= 0:
                logger.error(f"Invalid close price for {strategy_config.market.symbol}: {latest_candle.get('close')}")
                return None

            return {
                'time': latest_candle['time'],
                'open': Decimal(str(latest_candle['open'])),
                'high': Decimal(str(latest_candle['high'])),
                'low': Decimal(str(latest_candle['low'])),
                'close': Decimal(str(latest_candle['close'])),
                'volume': Decimal(str(latest_candle['volume'])),
                'order_book': order_book
            }

        except Exception as e:
            logger.error(f"Error fetching market data for {strategy_config.market.symbol}: {e}", exc_info=True)
            return None
