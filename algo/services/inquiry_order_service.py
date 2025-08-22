import logging

from django.db import transaction
from decimal import Decimal

from algo.enums import OrderStatus, OrderSide
from algo.models import Order
from algo.strategies.enums import ProcessedSideEnum
from algo_trade import settings
from algo_trade.utils import validate_response_schema
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

class InquiryOrderService:
    def  __init__(
            self,
            provider_config=None,
    ):
        self.provider_config = provider_config or {}

    def inquiry_all_orders(self):
        try:
            logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Starting inquiry all orders")
            orders = Order.objects.filter(
                status__in=[
                    OrderStatus.NEW,
                    OrderStatus.PARTIALLY_FILLED,
                ]
            ).all()
            logger.info(f'{settings.INQUIRY_ORDER_LOG_PREFIX} Inquiry order count {len(orders)}')
            if len(orders) == 0:
                logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} No active orders found for inquiry")
                return 'no active order found'
            for order in orders:
                self._inquiry_order(order=order)

        except Exception as e:
            logger.error(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Failed to inquiry order {e}")
            raise e

    def _inquiry_order(self, order: Order):
        logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Start inquiry order {order} from provider")

        self.provider_name = order.store_client.provider
        try:
            self.provider = ProviderFactory.create_provider(
                provider_name=self.provider_name,
                provider_config=self.provider_config,
            )
            response = self.provider.order_info(
                api_key=order.store_client.api_key,
                client_order_id=order.client_order_id,
            )
            logger.info(f'{settings.INQUIRY_ORDER_LOG_PREFIX} Inquiry order response {response} from provider{self.provider_name}')
            response_schema = validate_response_schema(response)
            if response_schema.success:
                with transaction.atomic():
                    if response_schema.result.status == OrderStatus.PARTIALLY_FILLED:
                        if order.status == OrderStatus.PARTIALLY_FILLED:
                            if order.executed_qty == Decimal(response_schema.result.executed_qty):
                                pass
                        else:
                            order.executed_qty = order.executed_qty + Decimal(response_schema.result.executed_qty)
                            order.executed_percent = order.executed_percent + int(
                                response_schema.result.executed_percent)
                    else:
                        order.executed_qty = response_schema.result.executed_qty
                        order.executed_percent = response_schema.result.executed_percent

                    order.status = response_schema.result.status
                    order.active = response_schema.result.active
                    order.executed_sum = response_schema.result.executed_sum
                    if  not order.deal:
                        logger.warning(f"{settings.INQUIRY_ORDER_LOG_PREFIX} order {order.id} has no deal"
                                       f" but inquiry to it's instance successfully done")
                        order.save(update_fields=['status','active','executed_sum'])
                        return True

                    if response_schema.result.status == OrderStatus.FILLED and order.side == OrderSide.BUY:

                         if order.deal.processed_side ==  ProcessedSideEnum.SELL.value:
                             order.deal.processed_side = ProcessedSideEnum.BUY_AND_SELL.value
                             order.deal.is_processed = True
                         elif order.deal.processed_side == ProcessedSideEnum.NONE.value:
                             order.deal.processed_side = ProcessedSideEnum.BUY.value

                    elif response_schema.result.status == OrderStatus.FILLED and order.side == OrderSide.SELL:

                        if order.deal.processed_side == ProcessedSideEnum.BUY.value:
                            order.deal.processed_side = ProcessedSideEnum.BUY_AND_SELL.value
                            order.deal.is_processed = True
                        elif order.deal.processed_side == ProcessedSideEnum.NONE.value:
                            order.deal.processed_side = ProcessedSideEnum.SELL.value
                    else:
                        pass

                    order.deal.save()
                    order.save()
                    logger.info(f'{settings.INQUIRY_ORDER_LOG_PREFIX} Inquiry order status {order.status} successfully updated')
                    return True
            else:
                logger.info(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Response from provider{self.provider_name} failed")
                return False
        except ValueError as e:
            logger.error(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Provider creation failed: {e}")
            raise ValueError(f"{settings.INQUIRY_ORDER_LOG_PREFIX} Failed to create provider.") from e
