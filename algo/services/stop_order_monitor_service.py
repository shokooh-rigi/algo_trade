import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

from algo.models import Deal, Order
from algo.services.order_management_service import OrderManagementService
from providers.services.provider_handler import ProviderHandler
from providers.provider_factory import ProviderFactory
from algo_trade import settings

logger = logging.getLogger(__name__)


class StopOrderMonitorService:
    """
    Service responsible for monitoring and managing stop-loss and take-profit orders.
    Handles trailing stops, order updates, and position management.
    """

    def __init__(self):
        self.order_management = OrderManagementService()

    def monitor_active_deals(self) -> Dict[str, Any]:
        """
        Monitor all active deals with stop orders and update trailing stops.
        
        Returns:
            Dict containing monitoring results
        """
        logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Starting stop order monitoring")
        
        try:
            # Get all active deals with stop-loss or take-profit orders
            active_deals = Deal.objects.filter(
                is_active=True,
                is_processed=True,
                stop_loss_price__isnull=False
            ).exclude(stop_loss_price=0)
            
            results = {
                "status": "success",
                "total_deals": len(active_deals),
                "updated_trailing_stops": 0,
                "canceled_orders": 0,
                "errors": 0,
                "details": []
            }
            
            for deal in active_deals:
                try:
                    result = self._monitor_single_deal(deal)
                    results["details"].append(result)
                    
                    if result.get("trailing_stop_updated"):
                        results["updated_trailing_stops"] += 1
                    if result.get("order_canceled"):
                        results["canceled_orders"] += 1
                    if result.get("error"):
                        results["errors"] += 1
                        
                except Exception as e:
                    logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error monitoring deal {deal.client_deal_id}: {e}", exc_info=True)
                    results["errors"] += 1
                    results["details"].append({
                        "deal_id": deal.id,
                        "client_deal_id": deal.client_deal_id,
                        "error": str(e)
                    })
            
            logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Monitoring completed. "
                       f"Deals: {results['total_deals']}, Updated: {results['updated_trailing_stops']}, "
                       f"Canceled: {results['canceled_orders']}, Errors: {results['errors']}")
            
            return results
            
        except Exception as e:
            logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error in stop order monitoring: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _monitor_single_deal(self, deal: Deal) -> Dict[str, Any]:
        """Monitor a single deal for trailing stop updates."""
        try:
            result = {
                "deal_id": deal.id,
                "client_deal_id": deal.client_deal_id,
                "trailing_stop_updated": False,
                "order_canceled": False,
                "error": None
            }
            
            # Get current market price
            current_price = self._get_current_market_price(deal)
            if not current_price:
                result["error"] = "Could not get current market price"
                return result
            
            # Update trailing stop if enabled
            if deal.trailing_stop_enabled:
                trailing_result = self.order_management.update_trailing_stop(deal, current_price)
                if trailing_result:
                    result["trailing_stop_updated"] = True
                    result["trailing_stop_details"] = trailing_result
            
            # Check if stop-loss or take-profit orders were executed
            self._check_order_execution(deal, result)
            
            return result
            
        except Exception as e:
            logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error monitoring deal {deal.client_deal_id}: {e}")
            return {
                "deal_id": deal.id,
                "client_deal_id": deal.client_deal_id,
                "error": str(e)
            }

    def _get_current_market_price(self, deal: Deal) -> Optional[float]:
        """Get current market price for a deal's symbol."""
        try:
            # Create provider to get current price
            provider = ProviderFactory.create_provider(
                provider_name=deal.provider_name,
                provider_config={}
            )
            
            # Get latest price (this would need to be implemented in the provider)
            # For now, return None - this would need actual market data integration
            return None
            
        except Exception as e:
            logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error getting market price for {deal.market_symbol}: {e}")
            return None

    def _check_order_execution(self, deal: Deal, result: Dict[str, Any]) -> None:
        """Check if stop-loss or take-profit orders were executed."""
        try:
            # Check stop-loss order status
            if deal.stop_loss_order_id:
                stop_loss_status = self._get_order_status(deal, deal.stop_loss_order_id)
                if stop_loss_status in ["FILLED", "EXECUTED"]:
                    logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Stop-loss executed for deal {deal.client_deal_id}")
                    deal.status = "STOPPED"
                    deal.is_active = False
                    deal.save()
                    result["order_canceled"] = True
            
            # Check take-profit order status
            if deal.take_profit_order_id:
                take_profit_status = self._get_order_status(deal, deal.take_profit_order_id)
                if take_profit_status in ["FILLED", "EXECUTED"]:
                    logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Take-profit executed for deal {deal.client_deal_id}")
                    deal.status = "STOPPED"
                    deal.is_active = False
                    deal.save()
                    result["order_canceled"] = True
                    
        except Exception as e:
            logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error checking order execution for deal {deal.client_deal_id}: {e}")

    def _get_order_status(self, deal: Deal, order_id: str) -> Optional[str]:
        """Get order status from exchange."""
        try:
            # This would need to be implemented to query the exchange for order status
            # For now, return None
            return None
            
        except Exception as e:
            logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error getting order status for {order_id}: {e}")
            return None

    def cancel_all_stop_orders(self, deal: Deal) -> Dict[str, Any]:
        """
        Cancel all stop-loss and take-profit orders for a deal.
        
        Args:
            deal: The deal to cancel orders for
            
        Returns:
            Dict with cancellation results
        """
        logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Canceling all stop orders for deal {deal.client_deal_id}")
        
        try:
            results = {
                "status": "success",
                "stop_loss_canceled": False,
                "take_profit_canceled": False,
                "errors": []
            }
            
            # Get store client
            from algo.models import StoreClient
            store_client = StoreClient.objects.get(provider=deal.provider_name)
            
            # Create provider and handler
            provider = ProviderFactory.create_provider(
                provider_name=deal.provider_name,
                provider_config={}
            )
            handler = ProviderHandler(provider)
            
            # Cancel stop-loss order
            if deal.stop_loss_order_id:
                try:
                    handler.cancel_order(
                        api_key=store_client.api_key,
                        order_id=deal.stop_loss_order_id
                    )
                    deal.stop_loss_order_id = None
                    results["stop_loss_canceled"] = True
                    logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Canceled stop-loss order {deal.stop_loss_order_id}")
                except Exception as e:
                    results["errors"].append(f"Stop-loss cancellation failed: {e}")
            
            # Cancel take-profit order
            if deal.take_profit_order_id:
                try:
                    handler.cancel_order(
                        api_key=store_client.api_key,
                        order_id=deal.take_profit_order_id
                    )
                    deal.take_profit_order_id = None
                    results["take_profit_canceled"] = True
                    logger.info(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Canceled take-profit order {deal.take_profit_order_id}")
                except Exception as e:
                    results["errors"].append(f"Take-profit cancellation failed: {e}")
            
            # Update deal
            deal.save()
            
            return results
            
        except Exception as e:
            logger.error(f"{settings.STOP_ORDER_MONITOR_LOG_PREFIX} Error canceling stop orders for deal {deal.client_deal_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
