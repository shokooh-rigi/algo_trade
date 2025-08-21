import logging
from django.conf import settings

from providers.dto.dto_factory import DataTypeEnum
from providers.dto.order_book_dto import OrderBookDTO
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


def get_recent_mid_price(
        store_client_provider,
        symbol: str = None,
        markets: list = None,
) -> list:
    mid_prices = []
    try:
        provider = ProviderFactory.create_provider(store_client_provider, {})
        result_order_book = provider.fetch_all_order_books()

        order_books = result_order_book.get("result", {})
        if not order_books:
            logger.error(f"{settings.ORDER_LOG_PREFIX} Provider API returned no data.")
            return mid_prices

        # Determine the markets to process
        target_markets = set(markets) if markets else {symbol}
        if not target_markets:
            logger.warning(f"{settings.ORDER_LOG_PREFIX} No symbol or markets provided.")
            return mid_prices

        for market, data in order_books.items():
            if market not in target_markets and market != "USDTTMN":
                continue

            asks = data.get("ask", [])
            bids = data.get("bid", [])

            if not asks or not bids:
                logger.warning(f"{settings.ORDER_LOG_PREFIX} Order book for {market} is missing asks or bids.")
                continue

            order_book_dto = OrderBookDTO(
                symbol=market,
                asks=asks,
                bids=bids,
                data_type=DataTypeEnum.LIVE_ORDER_BOOK.value
            )

            try:
                best_ask = float(order_book_dto.asks[0]["price"])
                best_bid = float(order_book_dto.bids[0]["price"])
                mid_price = (best_ask + best_bid) / 2
                mid_prices.append({
                    "symbol": order_book_dto.symbol,
                    "mid_price": mid_price,
                    "best_ask": best_ask,
                    "best_bid": best_bid,
                }
                )
            except (IndexError, ValueError, KeyError) as e:
                logger.error(f"{settings.ORDER_LOG_PREFIX} Error processing order book for {market}: {e}")

    except Exception as e:
        logger.error(f"{settings.ORDER_LOG_PREFIX} Error in fetching order book from provider API: {e}")

    return mid_prices
