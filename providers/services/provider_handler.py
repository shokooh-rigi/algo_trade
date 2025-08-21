import logging
from pydantic import ValidationError

from algo.schemas import CreateOrderRequestSchema, OrderResponseSchema
from algo_trade import settings
from algo_trade.utils import validate_response_schema
from providers.provider_interface import IProvider

logger = logging.getLogger(__name__)


class ProviderHandler:
    """
    Handles interactions with the provider to create orders and validate the response.

    This class communicates with a provider to place orders and validates the response against
    a predefined schema to ensure correctness.
    """

    def __init__(self, provider: IProvider):
        """
        Initializes the ProviderHandler with the provided provider.

        Args:
            provider (IProvider): The provider instance responsible for creating orders.
        """
        self.provider = provider
        logger.info(f"{settings.ORDER_LOG_PREFIX} Initialized ProviderHandler with provider: {provider.__class__.__name__}")

    def create_order(
            self,
            api_key: str,
            request: CreateOrderRequestSchema,
    ) -> OrderResponseSchema:
        """
        Creates an order through the provider and validates the response.

        Args:
            api_key (str): The API key associated with the client account, used for authentication.
            request (CreateOrderRequestSchema): The request schema for creating an order.

        Returns:
            OrderResponseSchema: The response schema with order details, validated.

        Raises:
            ValueError: If the response schema is invalid or the provider fails.
        """
        try:
            logger.info(f"{settings.ORDER_LOG_PREFIX} Creating order with request: {request}")
            print(f"{settings.ORDER_LOG_PREFIX} DEBUG: Request payload to provider: {request}")

            # Convert Pydantic schema to dict and send to provider
            response = self.provider.create_order(
                order_request_schema=dict(request),
                api_key=api_key,
            )
            logger.info(f"{settings.ORDER_LOG_PREFIX} Received response from provider: {response}")
            print(f"{settings.ORDER_LOG_PREFIX} DEBUG: Raw response from provider: {response}")

            return validate_response_schema(response)

        except ValidationError as e:
            logger.error(f"{settings.ORDER_LOG_PREFIX} Response validation failed: {e}")
            print(f"{settings.ORDER_LOG_PREFIX} ERROR: ValidationError occurred: {e}")
            raise ValueError("Invalid response schema.") from e

        except Exception as e:
            logger.error(f"{settings.ORDER_LOG_PREFIX} Failed to create order: {e}")
            print(f"{settings.ORDER_LOG_PREFIX} ERROR: Unexpected error occurred during order creation: {e}")
            raise ValueError(f"Order creation failed due to an unexpected error: {str(e)}") from e
