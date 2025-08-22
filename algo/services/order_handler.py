import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from django.contrib.sites import requests
from django.db import transaction

from algo.models import Order, Deal, StoreClient
from algo.enums import OrderStatus
from providers.provider_factory import ProviderFactory
from providers.schemas.wallex_schemas import OrderResponseSchema, OrderResultSchema # Assuming common schemas
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class OrderHandler:
    """
    Handles the lifecycle and management of individual orders after they have been placed.
    This includes inquiring about order status, canceling orders, and updating related deals.
    """

    def __init__(self, provider_config: Optional[Dict[str, Any]] = None):
        """
        Initializes the OrderHandler.
        Args:
            provider_config (Optional[Dict[str, Any]]): Configuration for providers.
        """
        self.provider_config = provider_config or {}

    def get_and_update_order_status(self, order_id: str) -> bool:
        """
        Fetches the latest status of a specific order from its provider and updates
        the database record.

        Args:
            order_id (str): The client_order_id of the order to inquire about.

        Returns:
            bool: True if the order status was successfully fetched and updated, False otherwise.
        """
        logger.info(f"Inquiring about order with client_order_id: {order_id}")
        try:
            order = Order.objects.select_related('deal', 'store_client').get(client_order_id=order_id)
        except Order.DoesNotExist:
            logger.warning(f"Order with client_order_id {order_id} not found in the database.")
            return False
        except Exception as e:
            logger.error(f"Error retrieving order {order_id} from database: {e}", exc_info=True)
            return False

        store_client = order.store_client
        if not store_client:
            logger.error(f"StoreClient not found for order {order.id}. Cannot inquire status.")
            return False

        try:
            provider_instance = ProviderFactory.create_provider(
                provider_name=store_client.provider,
                provider_config=self.provider_config
            )
        except ValueError as e:
            logger.error(f"Failed to create provider instance for {store_client.provider}: {e}")
            return False

        try:
            # The order_info method in providers should return OrderResponseSchema
            api_response: OrderResponseSchema = provider_instance.order_info(
                api_key=store_client.api_key,
                client_order_id=order.client_order_id,
            )

            if api_response.success and api_response.result:
                order_result: OrderResultSchema = api_response.result

                with transaction.atomic():
                    # Update order fields based on API response
                    order.executed_price = Decimal(order_result.executed_price) if order_result.executed_price else None
                    order.executed_qty = Decimal(order_result.executed_qty) if order_result.executed_qty else None
                    order.executed_sum = Decimal(order_result.executed_sum) if order_result.executed_sum else None
                    order.executed_percent = order_result.executed_percent
                    order.status = order_result.status
                    order.active = order_result.active
                    order.save(update_fields=[
                        'executed_price', 'executed_qty', 'executed_sum',
                        'executed_percent', 'status', 'active', 'updated_at'
                    ])
                    logger.info(f"Order {order.client_order_id} status updated to {order.status}.")

                    # Logic to update the parent Deal based on order status
                    if order.deal and order.status == OrderStatus.FILLED:
                        # You might want to define more granular deal statuses
                        # For example, if a BUY order is filled, the deal might move to a 'BOUGHT' state,
                        # waiting for a SELL signal.
                        # deal.status = StrategyState.BOUGHT # Example: Requires new StrategyState
                        # deal.save(update_fields=['status'])
                        logger.info(f"Deal {order.deal.client_deal_id} potentially affected by order {order.client_order_id} being FILLED.")

                return True
            else:
                logger.warning(f"Failed to get order info for {order.client_order_id}: {api_response.message}")
                return False

        except ValidationError as e:
            logger.error(f"Pydantic validation error for order info API response for order {order.client_order_id}: {e.errors()}", exc_info=True)
            return False
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching order info for {order.client_order_id}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error in get_and_update_order_status for order {order.client_order_id}: {e}", exc_info=True)
            return False


    def cancel_single_order(self, order_id: str) -> bool:
        """
        Cancels a specific order on its respective exchange and updates its status in the database.

        Args:
            order_id (str): The client_order_id of the order to cancel.

        Returns:
            bool: True if the order was successfully canceled and updated, False otherwise.
        """
        logger.info(f"Attempting to cancel order with client_order_id: {order_id}")
        try:
            order = Order.objects.select_related('store_client').get(client_order_id=order_id)
        except Order.DoesNotExist:
            logger.warning(f"Order with client_order_id {order_id} not found in the database for cancellation.")
            return False
        except Exception as e:
            logger.error(f"Error retrieving order {order_id} from database for cancellation: {e}", exc_info=True)
            return False

        if order.status == OrderStatus.CANCELED or order.status == OrderStatus.FILLED:
            logger.info(f"Order {order.client_order_id} is already {order.status}. No need to cancel.")
            return True # Already in a final state, consider it "handled"

        store_client = order.store_client
        if not store_client:
            logger.error(f"StoreClient not found for order {order.id}. Cannot cancel order.")
            return False

        try:
            provider_instance = ProviderFactory.create_provider(
                provider_name=store_client.provider,
                provider_config=self.provider_config
            )
        except ValueError as e:
            logger.error(f"Failed to create provider instance for {store_client.provider}: {e}")
            return False

        try:
            # The cancel_order method in providers should return OrderResponseSchema
            api_response: OrderResponseSchema = provider_instance.cancel_order(
                api_key=store_client.api_key,
                order_id=order.client_order_id,
            )

            if api_response.success:
                with transaction.atomic():
                    order.status = OrderStatus.CANCELED
                    order.active = False
                    order.save(update_fields=['status', 'active', 'updated_at'])
                    logger.info(f"Order {order.client_order_id} successfully canceled and updated in DB.")

                    # Optionally, update the parent Deal's status if its associated order is canceled
                    if order.deal:
                        # deal.status = StrategyState.ORDER_CANCELED # Example: Requires new StrategyState
                        # deal.save(update_fields=['status'])
                        logger.info(f"Deal {order.deal.client_deal_id} potentially affected by order {order.client_order_id} cancellation.")
                return True
            else:
                logger.warning(f"Failed to cancel order {order.client_order_id} on exchange: {api_response.message}")
                return False

        except ValidationError as e:
            logger.error(f"Pydantic validation error for cancel order API response for order {order.client_order_id}: {e.errors()}", exc_info=True)
            return False
        except requests.RequestException as e:
            logger.error(f"Network or API error canceling order {order.client_order_id}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error in cancel_single_order for order {order.client_order_id}: {e}", exc_info=True)
            return False

