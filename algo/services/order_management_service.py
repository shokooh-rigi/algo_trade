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

            # Place main order
            order_response = handler.create_order(
                api_key=store_client.api_key,
                request=order_request
            )

            # Create order record
            order = self._create_order_record(deal, order_response, store_client)
            
            # Place stop-loss and take-profit orders if specified
            stop_loss_result = None
            take_profit_result = None
            
            if deal.stop_loss_price:
                stop_loss_result = self._place_stop_loss_order(deal, market, store_client, handler)
            
            if deal.take_profit_price:
                take_profit_result = self._place_take_profit_order(deal, market, store_client, handler)
            
            # Update deal status
            deal.is_processed = True
            deal.processed_side = ProcessedSideEnum.BUY if deal.side == 'BUY' else ProcessedSideEnum.SELL
            deal.save()

            logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Order {order.client_order_id} placed successfully for deal {deal.client_deal_id}")
            if stop_loss_result:
                logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Stop-loss order placed: {stop_loss_result.get('client_order_id')}")
            if take_profit_result:
                logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Take-profit order placed: {take_profit_result.get('client_order_id')}")

            return {
                "status": "success",
                "order_id": order.id,
                "client_order_id": order.client_order_id,
                "deal_id": deal.id,
                "stop_loss_order": stop_loss_result,
                "take_profit_order": take_profit_result
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

    def _place_stop_loss_order(self, deal: Deal, market: Market, store_client: StoreClient, handler) -> Optional[Dict[str, Any]]:
        """Place stop-loss order."""
        try:
            # Determine stop-loss side (opposite of main order)
            stop_loss_side = "SELL" if deal.side == "BUY" else "BUY"
            
            # Adjust stop-loss price according to market rules
            adjusted_stop_price = market.adjust_price(float(deal.stop_loss_price))
            adjusted_quantity = market.adjust_quantity(float(deal.quantity))
            adjusted_quantity = market.adjust_min_qty(adjusted_quantity)
            
            if adjusted_quantity <= 0:
                logger.error(f"Invalid adjusted quantity for stop-loss: {adjusted_quantity}")
                return None
            
            # Create stop-loss order request
            stop_loss_request = CreateOrderRequestSchema(
                symbol=deal.market_symbol,
                side=stop_loss_side,
                type="STOP_MARKET",  # Stop market order for immediate execution
                quantity=str(adjusted_quantity),
                stopPrice=str(adjusted_stop_price)  # Trigger price
            )
            
            # Place stop-loss order
            stop_loss_response = handler.create_order(
                api_key=store_client.api_key,
                request=stop_loss_request
            )
            
            # Create stop-loss order record
            stop_loss_order = Order.objects.create(
                store_client=store_client,
                deal=deal,
                symbol=deal.market_symbol,
                type="STOP_MARKET",
                side=stop_loss_side,
                price=deal.stop_loss_price,
                quantity=deal.quantity,
                orig_qty=deal.quantity,
                orig_sum=deal.stop_loss_price * deal.quantity,
                status="NEW",
                active=True,
                client_order_id=stop_loss_response.order_id,
                timestamp_created_at=str(stop_loss_response.timestamp)
            )
            
            # Update deal with stop-loss order ID
            deal.stop_loss_order_id = stop_loss_response.order_id
            deal.save()
            
            logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Stop-loss order placed for deal {deal.client_deal_id} at {adjusted_stop_price}")
            
            return {
                "status": "success",
                "order_id": stop_loss_order.id,
                "client_order_id": stop_loss_response.order_id,
                "price": adjusted_stop_price,
                "side": stop_loss_side
            }
            
        except Exception as e:
            logger.error(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Error placing stop-loss order for deal {deal.client_deal_id}: {e}", exc_info=True)
            return None

    def _place_take_profit_order(self, deal: Deal, market: Market, store_client: StoreClient, handler) -> Optional[Dict[str, Any]]:
        """Place take-profit order."""
        try:
            # Determine take-profit side (opposite of main order)
            take_profit_side = "SELL" if deal.side == "BUY" else "BUY"
            
            # Adjust take-profit price according to market rules
            adjusted_take_profit_price = market.adjust_price(float(deal.take_profit_price))
            adjusted_quantity = market.adjust_quantity(float(deal.quantity))
            adjusted_quantity = market.adjust_min_qty(adjusted_quantity)
            
            if adjusted_quantity <= 0:
                logger.error(f"Invalid adjusted quantity for take-profit: {adjusted_quantity}")
                return None
            
            # Create take-profit order request (limit order for better price control)
            take_profit_request = CreateOrderRequestSchema(
                symbol=deal.market_symbol,
                side=take_profit_side,
                type="LIMIT",  # Limit order for take-profit
                quantity=str(adjusted_quantity),
                price=str(adjusted_take_profit_price)
            )
            
            # Place take-profit order
            take_profit_response = handler.create_order(
                api_key=store_client.api_key,
                request=take_profit_request
            )
            
            # Create take-profit order record
            take_profit_order = Order.objects.create(
                store_client=store_client,
                deal=deal,
                symbol=deal.market_symbol,
                type="LIMIT",
                side=take_profit_side,
                price=deal.take_profit_price,
                quantity=deal.quantity,
                orig_qty=deal.quantity,
                orig_sum=deal.take_profit_price * deal.quantity,
                status="NEW",
                active=True,
                client_order_id=take_profit_response.order_id,
                timestamp_created_at=str(take_profit_response.timestamp)
            )
            
            # Update deal with take-profit order ID
            deal.take_profit_order_id = take_profit_response.order_id
            deal.save()
            
            logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Take-profit order placed for deal {deal.client_deal_id} at {adjusted_take_profit_price}")
            
            return {
                "status": "success",
                "order_id": take_profit_order.id,
                "client_order_id": take_profit_response.order_id,
                "price": adjusted_take_profit_price,
                "side": take_profit_side
            }
            
        except Exception as e:
            logger.error(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Error placing take-profit order for deal {deal.client_deal_id}: {e}", exc_info=True)
            return None

    def update_trailing_stop(self, deal: Deal, current_price: float) -> Optional[Dict[str, Any]]:
        """
        Update trailing stop order based on current price.
        
        Args:
            deal: The deal with trailing stop enabled
            current_price: Current market price
            
        Returns:
            Dict with update result
        """
        try:
            if not deal.trailing_stop_enabled or not deal.trailing_stop_distance:
                return None
            
            # Calculate new stop-loss price based on trailing distance
            if deal.side == "BUY":
                # For long positions, trail upward
                new_stop_price = current_price * (1 - deal.trailing_stop_distance / 100)
                # Only update if new stop is higher than current
                if new_stop_price > deal.stop_loss_price:
                    return self._update_stop_loss_price(deal, new_stop_price)
            else:
                # For short positions, trail downward
                new_stop_price = current_price * (1 + deal.trailing_stop_distance / 100)
                # Only update if new stop is lower than current
                if new_stop_price < deal.stop_loss_price:
                    return self._update_stop_loss_price(deal, new_stop_price)
            
            return None
            
        except Exception as e:
            logger.error(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Error updating trailing stop for deal {deal.client_deal_id}: {e}", exc_info=True)
            return None

    def _update_stop_loss_price(self, deal: Deal, new_stop_price: float) -> Optional[Dict[str, Any]]:
        """Update stop-loss price by canceling old order and placing new one."""
        try:
            # Get store client and market info
            store_client = self._get_store_client(deal)
            market = self._get_market_info(deal)
            
            if not store_client or not market:
                return None
            
            # Create provider and handler
            provider = ProviderFactory.create_provider(
                provider_name=deal.provider_name,
                provider_config={}
            )
            handler = ProviderHandler(provider)
            
            # Cancel existing stop-loss order if it exists
            if deal.stop_loss_order_id:
                try:
                    handler.cancel_order(
                        api_key=store_client.api_key,
                        order_id=deal.stop_loss_order_id
                    )
                    logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Canceled old stop-loss order {deal.stop_loss_order_id}")
                except Exception as e:
                    logger.warning(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Could not cancel old stop-loss order: {e}")
            
            # Update deal with new stop-loss price
            deal.stop_loss_price = new_stop_price
            deal.stop_loss_order_id = None  # Will be set by new order
            deal.save()
            
            # Place new stop-loss order
            stop_loss_result = self._place_stop_loss_order(deal, market, store_client, handler)
            
            if stop_loss_result:
                logger.info(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Updated trailing stop for deal {deal.client_deal_id} to {new_stop_price}")
                return {
                    "status": "success",
                    "old_price": deal.stop_loss_price,
                    "new_price": new_stop_price,
                    "stop_loss_order": stop_loss_result
                }
            
            return None
            
        except Exception as e:
            logger.error(f"{settings.ORDER_MANAGEMENT_LOG_PREFIX} Error updating stop-loss price for deal {deal.client_deal_id}: {e}", exc_info=True)
            return None

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
