import logging
from typing import Dict, Any, List

from algo.models import Deal, AdminSystemConfig
from algo.strategies.enums import StrategyState, ProcessedSideEnum
from algo.services.order_management_service import OrderManagementService
from algo_trade import settings

logger = logging.getLogger(__name__)


class DealProcessorService:
    """
    Service responsible for processing unprocessed deals.
    Manages the lifecycle of deals from creation to order placement.
    """

    def __init__(self):
        self.system_configs = AdminSystemConfig.get_instance()
        self.order_management = OrderManagementService()

    def process_unprocessed_deals(self) -> Dict[str, Any]:
        """
        Process all unprocessed deals.
        
        Returns:
            Dict containing processing results and statistics.
        """
        logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Starting deal processing.")

        # Check global kill switch
        if self.system_configs.kill_switch:
            logger.warning(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Global kill switch is ON. Skipping deal processing.")
            return {"status": "disabled", "reason": "Global kill switch is ON"}

        # Get unprocessed deals
        unprocessed_deals = self._get_unprocessed_deals()
        if not unprocessed_deals:
            logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} No unprocessed deals found.")
            return {"status": "no_deals", "count": 0}

        results = {
            "status": "success",
            "total_deals": len(unprocessed_deals),
            "processed": 0,
            "errors": 0,
            "orders_placed": 0,
            "details": []
        }

        # Process each deal
        for deal in unprocessed_deals:
            try:
                result = self._process_single_deal(deal)
                results["processed"] += 1
                results["details"].append(result)
                
                if result.get("order_placed"):
                    results["orders_placed"] += 1
                    
            except Exception as e:
                logger.error(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Error processing deal {deal.client_deal_id}: {e}", exc_info=True)
                results["errors"] += 1
                results["details"].append({
                    "deal_id": deal.id,
                    "client_deal_id": deal.client_deal_id,
                    "status": "error",
                    "error": str(e)
                })

        logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Deal processing completed. "
                   f"Processed: {results['processed']}, Errors: {results['errors']}, Orders: {results['orders_placed']}")
        
        return results

    def _get_unprocessed_deals(self) -> List[Deal]:
        """Get all unprocessed active deals."""
        return Deal.objects.filter(
            is_active=True,
            is_processed=False
        ).order_by('created_at')

    def _process_single_deal(self, deal: Deal) -> Dict[str, Any]:
        """
        Process a single deal.
        
        Args:
            deal: The deal to process
            
        Returns:
            Dict containing processing result
        """
        logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Processing deal {deal.client_deal_id} "
                   f"({deal.side} {deal.quantity} {deal.market_symbol} at {deal.price})")

        # Validate deal
        if not self._validate_deal(deal):
            return {
                "deal_id": deal.id,
                "client_deal_id": deal.client_deal_id,
                "status": "error",
                "error": "Deal validation failed"
            }

        # Check if we should process this deal
        if not self._should_process_deal(deal):
            return {
                "deal_id": deal.id,
                "client_deal_id": deal.client_deal_id,
                "status": "skipped",
                "reason": "Deal processing conditions not met"
            }

        # Place order for the deal
        order_result = self.order_management.place_order_for_deal(deal)
        
        if order_result.get("status") == "success":
            # Update deal status
            deal.status = StrategyState.RUNNING.value
            deal.save()
            
            logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Deal {deal.client_deal_id} processed successfully. "
                       f"Order {order_result.get('client_order_id')} placed.")
            
            return {
                "deal_id": deal.id,
                "client_deal_id": deal.client_deal_id,
                "status": "success",
                "order_placed": True,
                "order_id": order_result.get("order_id"),
                "client_order_id": order_result.get("client_order_id")
            }
        else:
            # Mark deal as failed
            deal.status = StrategyState.STOPPED.value
            deal.is_active = False
            deal.save()
            
            logger.error(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Failed to place order for deal {deal.client_deal_id}: "
                        f"{order_result.get('message')}")
            
            return {
                "deal_id": deal.id,
                "client_deal_id": deal.client_deal_id,
                "status": "error",
                "error": order_result.get("message")
            }

    def _validate_deal(self, deal: Deal) -> bool:
        """Validate deal before processing."""
        try:
            # Check if deal has required fields
            if not all([deal.market_symbol, deal.side, deal.price, deal.quantity]):
                logger.error(f"Deal {deal.client_deal_id} missing required fields")
                return False

            # Check if price and quantity are positive
            if deal.price <= 0 or deal.quantity <= 0:
                logger.error(f"Deal {deal.client_deal_id} has invalid price or quantity")
                return False

            # Check if side is valid
            if deal.side not in ['BUY', 'SELL']:
                logger.error(f"Deal {deal.client_deal_id} has invalid side: {deal.side}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating deal {deal.client_deal_id}: {e}")
            return False

    def _should_process_deal(self, deal: Deal) -> bool:
        """Check if deal should be processed based on business rules."""
        try:
            # For example: check market hours, account balance, risk limits, etc.
            
            # For now, process all valid deals
            return True

        except Exception as e:
            logger.error(f"Error checking deal processing conditions for {deal.client_deal_id}: {e}")
            return False

    def get_deal_statistics(self) -> Dict[str, Any]:
        """Get statistics about deals."""
        try:
            total_deals = Deal.objects.count()
            active_deals = Deal.objects.filter(is_active=True).count()
            processed_deals = Deal.objects.filter(is_processed=True).count()
            unprocessed_deals = Deal.objects.filter(is_active=True, is_processed=False).count()

            return {
                "total_deals": total_deals,
                "active_deals": active_deals,
                "processed_deals": processed_deals,
                "unprocessed_deals": unprocessed_deals
            }

        except Exception as e:
            logger.error(f"Error getting deal statistics: {e}")
            return {}

    def cancel_deal(self, deal_id: str) -> Dict[str, Any]:
        """
        Cancel a deal and any associated orders.
        
        Args:
            deal_id: The deal ID to cancel
            
        Returns:
            Dict containing cancellation result
        """
        try:
            deal = Deal.objects.get(client_deal_id=deal_id, is_active=True)
            
            # Mark deal as inactive
            deal.is_active = False
            deal.status = StrategyState.STOPPED.value
            deal.save()
            
            # Cancel any associated orders
            from algo.models import Order
            orders = Order.objects.filter(deal=deal, active=True)
            for order in orders:
                order.active = False
                order.status = "CANCELED"
                order.save()
            
            logger.info(f"{settings.DEAL_PROCESSING_LOG_PREFIX} Deal {deal_id} canceled successfully")
            
            return {"status": "success", "message": "Deal canceled"}
            
        except Deal.DoesNotExist:
            return {"status": "error", "message": "Deal not found"}
        except Exception as e:
            logger.error(f"Error canceling deal {deal_id}: {e}")
            return {"status": "error", "message": str(e)}
