import logging

from django.conf import settings

from providers.dto.dto_factory import DataTypeEnum
from providers.dto.order_book_dto import OrderBookDTO
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


def get_order_book_data(store_client_provider, symbol: str):
    try:
        provider = ProviderFactory.create_provider(store_client_provider, {})
        result_order_book = provider.fetch_all_order_books()

        order_books = result_order_book.get("result", {})
        if not order_books:
            logger.error(f"{settings.ORDER_LOG_PREFIX} Provider API is not accessible or returned no data.")
            return None
        else:
            for market, data in order_books.items():
                if market == symbol:
                    order_book_dto = OrderBookDTO(
                        symbol=symbol,
                        asks=data["ask"],
                        bids=data["bid"],
                        data_type=DataTypeEnum.LIVE_ORDER_BOOK.value
                    )
                    return order_book_dto
            return None
    except Exception as e:
        logger.error(f"{settings.ORDER_LOG_PREFIX} Error in getting order book from provider API: {e}")
        return None