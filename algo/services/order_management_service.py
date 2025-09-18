import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional

from algo.models import Order, Deal, StoreClient, Market, AdminSystemConfig
from algo.strategies.enums import ProcessedSideEnum
from providers.provider_factory import ProviderFactory
from providers.services.provider_handler import ProviderHandler
from providers.schemas.wallex_schemas import CreateOrderRequestSchema, OrderResponseSchema
from algo_trade import settings

logger = logging.getLogger(__name__)


class OrderManagementService:
    """
    Service responsible for managing order placement, tracking, and execution.
    Handles the lifecycle of orders from creation to completion.
    """

    def __init__(self):
        self.system_configs = AdminSystemConfig.get_instance()

    def place_order_for_deal(self, deal: Deal) -> Dict[str, Any]:
        """
        Place an order for a given deal.
        
        Args:
            deal: The deal to place an order for
            
        Returns:
            Dict containing order placement result
        """
        logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Placing order for deal {deal.client_deal_id}")

        try:
            # Get store client
            store_client = self._get_store_client(deal)
            if not store_client:
                return {"status": "error", "message": "Store client not found"}

            # Get market info
            market = self._get_market_info(deal)
            if not market:
                return {"status": "error", "message": "Market not found"}

            # Create provider and handler
            provider = ProviderFactory.create_provider(
                provider_name=deal.provider_name,
                provider_config={}
            )
            handler = ProviderHandler(provider)

            # Prepare order request
            order_request = self._prepare_order_request(deal, market)
            if not order_request:
                return {"status": "error", "message": "Failed to prepare order request"}

            # Place order
            order_response = handler.create_order(
                api_key=store_client.api_key,
                request=order_request
            )

            # Create order record
            order = self._create_order_record(deal, order_response, store_client)
            
            # Update deal status
            deal.is_processed = True
            deal.processed_side = ProcessedSideEnum.BUY if deal.side == 'BUY' else ProcessedSideEnum.SELL
            deal.save()

            logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Order {order.client_order_id} placed successfully for deal {deal.client_deal_id}")

            return {
                "status": "success",
                "order_id": order.id,
                "client_order_id": order.client_order_id,
                "deal_id": deal.id
            }

        except Exception as e:
            logger.error(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Error placing order for deal {deal.client_deal_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _get_store_client(self, deal: Deal) -> Optional[StoreClient]:
        """Get store client for the deal."""
        try:
            return StoreClient.objects.get(provider=deal.provider_name)
        except StoreClient.DoesNotExist:
            logger.error(f"Store client not found for provider {deal.provider_name}")
            return None

    def _get_market_info(self, deal: Deal) -> Optional[Market]:
        """Get market information for the deal."""
        try:
            return Market.objects.get(symbol=deal.market_symbol, provider=deal.provider_name)
        except Market.DoesNotExist:
            logger.error(f"Market {deal.market_symbol} not found for provider {deal.provider_name}")
            return None

    def _prepare_order_request(self, deal: Deal, market: Market) -> Optional[CreateOrderRequestSchema]:
        """Prepare order request schema."""
        try:
            # Adjust price and quantity according to market rules
            adjusted_price = market.adjust_price(float(deal.price))
            adjusted_quantity = market.adjust_quantity(float(deal.quantity))
            adjusted_quantity = market.adjust_min_qty(adjusted_quantity)

            if adjusted_quantity <= 0:
                logger.error(f"Invalid adjusted quantity: {adjusted_quantity}")
                return None

            return CreateOrderRequestSchema(
                symbol=deal.market_symbol,
                side=deal.side,
                type="LIMIT",  # Use limit orders for better control
                quantity=str(adjusted_quantity),
                price=str(adjusted_price)
            )

        except Exception as e:
            logger.error(f"Error preparing order request: {e}")
            return None

    def _create_order_record(self, deal: Deal, order_response: OrderResponseSchema, store_client: StoreClient) -> Order:
        """Create order record in database."""
        return Order.objects.create(
            store_client=store_client,
            deal=deal,
            symbol=deal.market_symbol,
            type="LIMIT",
            side=deal.side,
            price=deal.price,
            quantity=deal.quantity,
            orig_qty=deal.quantity,
            orig_sum=deal.price * deal.quantity,
            status="NEW",
            active=True,
            client_order_id=order_response.order_id,
            timestamp_created_at=str(order_response.timestamp)
        )

    def get_active_orders(self, provider_name: str = None) -> List[Order]:
        """
        Get all active orders, optionally filtered by provider.
        
        Args:
            provider_name: Optional provider name to filter by
            
        Returns:
            List of active orders
        """
        queryset = Order.objects.filter(active=True, status__in=["NEW", "PARTIALLY_FILLED"])
        
        if provider_name:
            queryset = queryset.filter(store_client__provider=provider_name)
            
        return list(queryset)

    def cancel_order(self, order_id: str, api_key: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: The order ID to cancel
            api_key: API key for authentication
            
        Returns:
            Dict containing cancellation result
        """
        try:
            order = Order.objects.get(client_order_id=order_id, active=True)
            
            # Create provider and cancel order
            provider = ProviderFactory.create_provider(
                provider_name=order.store_client.provider,
                provider_config={}
            )
            
            cancel_response = provider.cancel_order(
                api_key=api_key,
                order_id=order_id
            )
            
            # Update order status
            order.status = "CANCELED"
            order.active = False
            order.save()
            
            logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Order {order_id} canceled successfully")
            
            return {"status": "success", "message": "Order canceled"}
            
        except Order.DoesNotExist:
            return {"status": "error", "message": "Order not found"}
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return {"status": "error", "message": str(e)}
