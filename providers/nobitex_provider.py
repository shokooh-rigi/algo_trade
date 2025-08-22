import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from algo_trade import settings
from providers.provider_interface import IProvider
from pydantic import ValidationError  # Crucial for catching validation issues

from providers.schemas.nobitex_schemas import (
    NobitexCreateOrderRequest, NobitexOrderInfoRequest, NobitexCancelOrderRequest, NobitexGetBalanceRequest,
    NobitexCreateOrderResponse, NobitexActiveOrdersResponse, NobitexOrderInfoResponse,
    NobitexCancelOrderResponse, NobitexGetBalancesResponse, NobitexOHLCVResponse,
    NobitexOrderData, NobitexBalanceDetail,
    OrderResultSchema, OrderResponseSchema, ActiveOrdersResultSchema, ActiveOrdersResponseSchema
)

logger = logging.getLogger(__name__)


class NobitexProvider(IProvider):
    """
    Provider implementation for the Nobitex exchange. This class handles fetching data and managing orders
    for the Nobitex exchange, now with robust Pydantic data validation.
    """

    # Centralizing API endpoint paths from settings for easy configuration
    BASE_URL = settings.NOBITEX_BASE_URL
    ORDER_BOOK_ALL_PATH = settings.NOBITEX_ORDER_BOOK_PATH
    ORDER_BOOK_SYMBOL_PATH = settings.NOBITEX_ORDER_BOOK_PATH_BY_SYMBOL
    MARKET_PATH = settings.NOBITEX_MARKET_PATH
    ASSET_PATH = settings.NOBITEX_ASSET_PATH
    ORDER_CREATE_PATH = settings.NOBITEX_ORDER_CREATE_PATH
    ACTIVE_ORDERS_PATH = settings.NOBITEX_ACTIVE_ORDERS_PATH
    ORDER_INFO_PATH = settings.NOBITEX_ORDER_INFO_PATH
    CANCEL_ORDER_PATH = settings.NOBITEX_CANCEL_ORDER_PATH
    GET_BALANCES_PATH = settings.NOBITEX_GET_BALANCES_PATH
    OHLCV_HISTORY_PATH =settings.NOBITEX_OHLCV_HISTORY_PATH

    def __init__(self, provider_config: Dict[str, Any]):
        """
        Initialize the NobitexProvider with the given configuration.

        Args:
            provider_config (Dict[str, Any]): Configuration details for the provider.
        """
        self.config = provider_config

    def _get_auth_headers(self, api_key: str) -> Dict[str, str]:
        """
        Helper method to get standard authentication headers for Nobitex.
        Nobitex uses 'Authorization: Token YOUR_ACCESS_TOKEN'.
        """
        return {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }

    def fetch_all_order_books(self) -> Dict[str, Any]:
        """
        Fetch the latest order books for all markets on Nobitex.
        Endpoint: settings.NOBITEX_ORDER_BOOK_PATH (e.g., v2/depth/all)
        """
        try:
            response = requests.get(f"{self.BASE_URL}{self.ORDER_BOOK_ALL_PATH}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex all order books: {e}")
            return {}

    def fetch_order_book_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch the latest order book for a specific market symbol on Nobitex.
        Endpoint: settings.NOBITEX_ORDER_BOOK_PATH_BY_SYMBOL + ?symbol={symbol} (e.g., v1/depth)
        """
        try:
            params = {"symbol": symbol.upper()}
            response = requests.get(f"{self.BASE_URL}{self.ORDER_BOOK_SYMBOL_PATH}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex order book for symbol {symbol}: {e}")
            return {}

    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available market information on Nobitex.
        Endpoint: settings.NOBITEX_MARKET_PATH (e.g., v1/markets)
        """
        try:
            response = requests.get(f"{self.BASE_URL}{self.MARKET_PATH}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex markets: {e}")
            return {}

    def fetch_assets(self) -> Dict[str, Any]:
        """
        Fetch all available assets on Nobitex.
        Endpoint: settings.NOBITEX_ASSET_PATH (e.g., v1/currencies)
        """
        try:
            endpoint = self.ASSET_PATH
            response = requests.get(f"{self.BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex assets: {e}")
            return {}

    def fetch_ohlcv_data(
            self,
            symbol: str,
            resolution: str,  # e.g., '60' for 1 hour, 'D' for 1 day, or integer seconds
            from_timestamp: int,  # Unix timestamp (seconds)
            to_timestamp: int  # Unix timestamp (seconds)
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches historical OHLCV (candlestick) data for a given symbol and timeframe from Nobitex.
        Endpoint: GET market/udf/history?symbol={symbol}&resolution={resolution}&from={from_ts}&to={to_ts}
        Returns: List of dictionaries, each representing a candlestick (time, open, high, low, close, volume).
        """
        try:
            params = {
                "symbol": symbol.upper(),
                "resolution": resolution,
                "from": from_timestamp,
                "to": to_timestamp
            }

            response = requests.get(f"{self.BASE_URL}{self.OHLCV_HISTORY_PATH}", params=params)
            response.raise_for_status()
            response_json = response.json()

            # Validate the response with Pydantic
            nobitex_ohlcv_response = NobitexOHLCVResponse.model_validate(response_json)

            if nobitex_ohlcv_response.status == "ok":
                # Reconstruct list of dictionaries for easier consumption
                ohlcv_data = []
                num_candles = len(nobitex_ohlcv_response.t)
                for i in range(num_candles):
                    ohlcv_data.append({
                        "time": nobitex_ohlcv_response.t[i],
                        "open": nobitex_ohlcv_response.o[i],
                        "high": nobitex_ohlcv_response.h[i],
                        "low": nobitex_ohlcv_response.l[i],
                        "close": nobitex_ohlcv_response.c[i],
                        "volume": nobitex_ohlcv_response.v[i],
                    })
                return ohlcv_data
            else:
                logger.warning(
                    f"Error fetching OHLCV data for {symbol} from Nobitex: {response_json.get('message', 'Unknown error')}")
                return None
        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching Nobitex OHLCV data for {symbol}: {e.errors()}",
                         exc_info=True)
            return None
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching Nobitex OHLCV data for {symbol}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Nobitex OHLCV data for {symbol}: {e}", exc_info=True)
            return None

    def create_order(
            self,
            api_key: str,
            order_request_data: Dict[str, Any],  # Still accepting Dict for flexibility from caller
    ) -> OrderResponseSchema:  # Returning your internal OrderResponseSchema
        """
        Create a new order on Nobitex using the provided data, validated by Pydantic.

        Args:
            api_key (str): The API key to authenticate the request.
            order_request_data (Dict[str, Any]): Dictionary containing order details.

        Returns:
            OrderResponseSchema: Your internal schema for the order creation response.
        """
        try:
            # You'll need to parse symbol (e.g., 'BTCUSDT') into srcCurrency ('BTC') and dstCurrency ('USDT')
            symbol = order_request_data.get("symbol")
            if not symbol or len(symbol) < 3:
                raise ValueError(f"Invalid symbol format for order creation: {symbol}")

            # This part needs careful mapping to Nobitex's specific currency naming (e.g., IRT vs RLS)
            # Assuming symbol is like BTCUSDT, for IRT markets, it might be BTCIRT.
            src_currency = symbol[:-3] if symbol.endswith('IRT') else symbol[:-4]
            dst_currency = symbol[-3:] if symbol.endswith('IRT') else symbol[-4:]

            # Validate the incoming order_request_data and construct Nobitex's specific request payload
            nobitex_request = NobitexCreateOrderRequest(
                type=order_request_data["side"].lower(),  # Nobitex expects 'buy' or 'sell' lowercase
                srcCurrency=src_currency.upper(),
                dstCurrency=dst_currency.upper(),
                amount=order_request_data["quantity"],
                price=order_request_data["price"]
            )
            headers = self._get_auth_headers(api_key)

            response = requests.post(
                url=f"{self.BASE_URL}{self.ORDER_CREATE_PATH}",
                json=nobitex_request.model_dump(mode='json', exclude_none=True),
                headers=headers,
            )
            response.raise_for_status()
            response_json = response.json()

            # Validate Nobitex's response using the appropriate Pydantic schema
            nobitex_response = NobitexCreateOrderResponse.model_validate(response_json)

            if nobitex_response.status == "ok":
                order_data = nobitex_response.order  # Access order data directly as per Nobitex schema
                # Map Nobitex's response to your internal OrderResultSchema
                return OrderResponseSchema(
                    success=True,
                    message="Order created successfully",
                    result=OrderResultSchema(
                        symbol=f"{order_data.srcCurrency}{order_data.dstCurrency}",
                        type=order_data.type.upper(),
                        side=order_data.type.upper(),  # Assuming buy/sell is consistent
                        price=order_data.price,
                        orig_qty=order_data.amount,
                        orig_sum=str(float(order_data.amount) * float(order_data.price)),  # Calculate if not provided
                        executed_price=order_data.totalPrice,
                        executed_qty=order_data.matchedAmount,
                        executed_sum=order_data.totalPrice,
                        executed_percent=int(float(order_data.matchedAmount) / float(order_data.amount) * 100) if float(
                            order_data.amount) > 0 else 0,
                        status=order_data.status.upper(),
                        active=order_data.status.upper() in ["NEW", "PARTIALLY_FILLED"],
                        timestamp_created_at=order_data.created_at,
                        client_order_id=str(order_data.id),  # Nobitex returns integer ID
                    )
                )
            else:
                return OrderResponseSchema(success=False, message="Nobitex API error", result=None)

        except ValidationError as e:
            logger.error(f"Pydantic validation error (request/response) creating Nobitex order: {e.errors()}",
                         exc_info=True)
            return OrderResponseSchema(success=False, message=f"Validation error: {e}", result=None)
        except requests.RequestException as e:
            logger.error(f"Network or API error creating Nobitex order: {e}", exc_info=True)
            return OrderResponseSchema(success=False, message=f"Network or API error: {e}", result=None)
        except Exception as e:
            logger.error(f"Unexpected error creating Nobitex order: {e}", exc_info=True)
            return OrderResponseSchema(success=False, message=f"Unexpected error: {e}", result=None)

    def get_active_orders(
            self,
            api_key: str,
            symbol: Optional[str] = None,
    ) -> ActiveOrdersResponseSchema:  # Returning your internal ActiveOrdersResponseSchema
        """
        Fetch all active orders from Nobitex, optionally filtered by a specific market symbol.
        Endpoint: GET v1/account/openOrders
        """
        try:
            headers = self._get_auth_headers(api_key)
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()  # Nobitex might use 'srcCurrency' and 'dstCurrency' for filtering

            response = requests.get(f"{self.BASE_URL}{self.ACTIVE_ORDERS_PATH}", headers=headers, params=params)
            response.raise_for_status()
            response_json = response.json()

            # Validate Nobitex's response
            nobitex_response = NobitexActiveOrdersResponse.model_validate(response_json)

            if nobitex_response.status == "ok":
                parsed_orders = []
                for order in nobitex_response.result.orders:
                    parsed_orders.append(
                        OrderResultSchema(
                            symbol=f"{order.srcCurrency}{order.dstCurrency}",
                            type=order.type.upper(),
                            side=order.type.upper(),
                            price=str(order.price),
                            orig_qty=str(order.amount),
                            orig_sum=str(float(order.amount) * float(order.price)),
                            executed_price=None,  # Not always available here
                            executed_qty=str(order.matchedAmount),
                            executed_sum=None,  # Not always available here
                            executed_percent=int(float(order.matchedAmount) / float(order.amount) * 100) if float(
                                order.amount) > 0 else 0,
                            status=order.status.upper(),  # e.g., 'NEW', 'PARTIALLY_FILLED'
                            active=True,  # Open orders are active
                            timestamp_created_at=order.created_at,
                            client_order_id=str(order.id),
                        )
                    )
                return ActiveOrdersResponseSchema(
                    success=True,
                    message="Active orders fetched successfully",
                    result=ActiveOrdersResultSchema(orders=parsed_orders)
                )
            else:
                return ActiveOrdersResponseSchema(success=False, message="Nobitex API error", result=None)

        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching active orders: {e.errors()}", exc_info=True)
            return ActiveOrdersResponseSchema(success=False, message=f"Response validation error: {e}", result=None)
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching active orders: {e}", exc_info=True)
            return ActiveOrdersResponseSchema(success=False, message=f"Network or API error: {e}", result=None)
        except Exception as e:
            logger.error(f"Unexpected error fetching active orders: {e}", exc_info=True)
            return ActiveOrdersResponseSchema(success=False, message=f"Unexpected error: {e}", result=None)

    def order_info(
            self,
            api_key: str,
            client_order_id: str = None,
    ) -> OrderResponseSchema:  # Returning your internal OrderResponseSchema
        """
        Fetch information for a specific order by its ID from Nobitex.
        Endpoint: POST v1/market/orders/status
        """
        try:
            if not client_order_id:
                raise ValueError("client_order_id is required for order_info.")

            nobitex_request = NobitexOrderInfoRequest(id=int(client_order_id))
            headers = self._get_auth_headers(api_key)

            response = requests.post(
                url=f"{self.BASE_URL}{self.ORDER_INFO_PATH}",
                json=nobitex_request.model_dump(mode='json'),
                headers=headers
            )
            response.raise_for_status()
            response_json = response.json()

            # Validate Nobitex's response
            nobitex_response = NobitexOrderInfoResponse.model_validate(response_json)

            if nobitex_response.status == "ok":
                order = nobitex_response.order  # Access order data directly as per Nobitex schema
                return OrderResponseSchema(
                    success=True,
                    message="Order info fetched successfully",
                    result=OrderResultSchema(
                        symbol=f"{order.srcCurrency}{order.dstCurrency}",
                        type=order.type.upper(),
                        side=order.type.upper(),
                        price=str(order.price),
                        orig_qty=str(order.amount),
                        orig_sum=str(float(order.amount) * float(order.price)),
                        executed_price=str(order.totalPrice) if order.totalPrice else None,
                        executed_qty=str(order.matchedAmount),
                        executed_s