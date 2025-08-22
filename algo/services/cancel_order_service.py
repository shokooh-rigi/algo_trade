import logging

from algo.enums import OrderStatus
from algo.models import StoreClient, Order
from algo_trade import settings
from algo_trade.utils import validate_response_schema
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class CancelOrderService:
    """
    Service responsible for handling order cancellation logic with the provider.

    This service interacts with a provider to cancel an order and validate the
    cancellation response. If successful, it stores the cancellation result in
    the database.
    """

    def __init__(
        self,
        store_client: StoreClient,
        client_order_id: str = None,
        provider_config=None,
    ):
        """
        Initializes the CancelOrderService with the client and order details.

        Args:
            store_client (StoreClient): The client that owns the order.
            client_order_id (str): The unique ID of the order to be canceled.
            provider_config (dict, optional): Configuration for the provider (defaults to None).

        Raises:
            ValueError: If an invalid provider configuration is provided.
        """
        self.store_client = store_client
        self.provider_name = store_client.provider
        self.client_order_id = client_order_id
        provider_config = provider_config or {}

        try:
            self.provider = ProviderFactory.create_provider(
                provider_name=self.provider_name,
                provider_config=provider_config,
            )
        except ValueError as e:
            logger.error(f"{settings.ORDER_LOG_PREFIX} Provider creation failed: {e}")
            raise ValueError("Failed to create provider.") from e

    def cancel_order(self):
        """
        Cancels the specified order via the provider and processes the response.

        This method interacts with the provider to cancel an order and validates
        the response schema. If the cancellation is successful and the order is
        marked as canceled, the result is saved to the database.

        Raises:
            ValueError: If the cancellation fails or the response is invalid.
        """
        try:
            logger.info(f"{settings.ORDER_LOG_PREFIX} Attempting to cancel order {self.client_order_id}.")
            response = self.provider.cancel_order(
                api_key=self.store_client.api_key,
                order_id=self.client_order_id,
            )

            response_schema = validate_response_schema(response)

            if response_schema.success:
                if response_schema.result.status == OrderStatus.CANCELED or response_schema.result.status == OrderStatus.FILLED:
                    Order.objects.filter(
                        client_order_id =self.client_order_id
                    ).update(**dict(response_schema.result))
                    logger.info(
                        f"{settings.ORDER_LOG_PREFIX}"
                        f" Order:{self.client_order_id} by status {response_schema.result.status} and recorded successfully.")
                    return True
            else:
                logger.warning(
                    f"{settings.ORDER_LOG_PREFIX} Cancellation failed for order {self.client_order_id}: "
                    f"{response_schema.message},"
                    f" result: {response_schema.result}"
                )
                return False

        except ValueError as e:
            logger.error(
                f"{settings.ORDER_LOG_PREFIX} Cancellation failed for"
                f" order {self.client_order_id}: {e}"
            )
            raise ValueError(f"Failed to cancel order {self.client_order_id}.") from e

    def cancel_active_orders(self):
        try:
            logger.info(f"{settings.ORDER_LOG_PREFIX} Fetching active orders for store client: {self.store_client}.")

            # Fetch active orders from the provider
            active_orders = self.provider.get_active_orders(api_key=self.store_client.api_key)

            # Validate the API response structure
            if not active_orders.get("success", False):
                logger.error(
                    f"{settings.ORDER_LOG_PREFIX} Failed to fetch active orders. Provider response: {active_orders}"
                )
                return False

            results = active_orders.get("result")
            if not results or "orders" not in results:
                logger.error(
                    f"{settings.ORDER_LOG_PREFIX} Invalid response structure. Missing 'result' or 'orders': {active_orders}"
                )
                return False

            # Retrieve the list of active orders
            list_active_orders = results["orders"]
            if not list_active_orders:
                logger.info(
                    f"{settings.ORDER_LOG_PREFIX} No active orders found for store client: {self.store_client}.")
                return True

            # Iterate through active orders and cancel them
            for active_order in list_active_orders:
                client_order_id = active_order.get("clientOrderId")
                if not client_order_id:
                    logger.warning(
                        f"{settings.ORDER_LOG_PREFIX} Skipping order without a valid 'clientOrderId'. Order data: {active_order}"
                    )
                    continue

                logger.info(f"{settings.ORDER_LOG_PREFIX} Attempting to cancel order: {client_order_id}.")

                try:
                    # Cancel the order via the provider
                    response = self.provider.cancel_order(
                        api_key=self.store_client.api_key,
                        order_id=client_order_id,
                    )

                    # Validate the cancellation response
                    response_schema = validate_response_schema(response)

                    if response_schema.success and response_schema.result.status == OrderStatus.CANCELED:
                        # Update the database with the cancellation details
                        Order.objects.filter(client_order_id=client_order_id).update(**dict(response_schema.result))
                        logger.info(
                            f"{settings.ORDER_LOG_PREFIX} Order {client_order_id} canceled successfully and updated in the database."
                        )
                    else:
                        logger.error(
                            f"{settings.ORDER_LOG_PREFIX} Failed to cancel order {client_order_id}. "
                            f"Response message: {response_schema.message}, result: {response_schema.result}"
                        )

                except Exception as e:
                    logger.error(
                        f"{settings.ORDER_LOG_PREFIX} Error occurred while canceling order {client_order_id}: {e}"
                    )

            logger.info(f"{settings.ORDER_LOG_PREFIX} Completed processing all active orders for store client.")
            return True

        except Exception as e:
            logger.exception(
                f"{settings.ORDER_LOG_PREFIX} An unexpected error occurred while canceling active orders for "
                f"store client {self.store_client}: {e}"
            )
            return False
