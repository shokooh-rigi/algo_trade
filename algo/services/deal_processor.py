import logging
from django.db import transaction
from algo.models import Deal, Order, StoreClient
from providers.provider_factory import ProviderFactory
from algo.enums import OrderType
from algo_trade.utils import validate_response_schema
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DealProcessor:

    def process_unprocessed_deals(self):
        """Reads unprocessed deals and places orders on the exchange."""
        unprocessed_deals = Deal.objects.filter(processed=False, is_active=True)
        if not unprocessed_deals.exists():
            logger.info("No new deals to process.")
            return

        for deal in unprocessed_deals:
            try:
                self._place_order_for_deal(deal)
            except Exception as e:
                logger.error(f"Error processing deal {deal.id}: {e}")

    def _place_order_for_deal(self, deal: Deal):
        """Places an order for a single deal."""
        store_client = StoreClient.objects.filter(provider=deal.provider).first()
        if not store_client:
            logger.error(f"No StoreClient found for provider {deal.provider}")
            return

        provider_instance = ProviderFactory.create_provider(
            provider_name=deal.provider,
            provider_config={} # Add your provider config here if needed
        )

        order_request_data = {
            "symbol": deal.market,
            "type": OrderType.LIMIT,
            "side": deal.side,
            "price": float(deal.price),
            "quantity": float(deal.quantity),
        }

        # Call Wallex API
        response = provider_instance.create_order(
            api_key=store_client.api_key,
            order_request_schema=order_request_data
        )

        # Validate and process the response
        response_schema = validate_response_schema(response)

        if response_schema.success:
            with transaction.atomic():
                # Create an Order record
                order_result = response_schema.result
                order = Order.objects.create(
                    deal=deal,
                    store_client=store_client,
                    symbol=order_result.symbol,
                    type=order_result.type,
                    side=order_result.side,
                    price=order_result.price,
                    quantity=order_result.orig_qty,
                    status=order_result.status,
                    client_order_id=order_result.client_order_id,
                )
                logger.info(f"Order created successfully for deal {deal.id}. Order ID: {order.id}")

                # Update the deal to mark it as processed
                deal.processed = True
                deal.save()
        else:
            logger.error(f"Failed to create order for deal {deal.id}. Message: {response_schema.message}")