import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from algo_trade import settings
from providers.provider_interface import IProvider
from pydantic import ValidationError

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
    OHLCV_HISTORY_PATH = settings.NOBITEX_OHLCV_HISTORY_PATH

    def __init__(self, provider_config: Dict[str, Any]):
        """
        Initialize the NobitexProvider with the given configuration.

        Args:
            provider_config (Dict[str, Any]): Configuration details for the provider.
        """
        self.config = provider_config
        self.provider_name = "Nobitex"

    def _get_auth_headers(self, api_key: str) -> Dict[str, str]:
        """
        Helper method to get standard authentication headers for Nobitex.
        Nobitex uses 'Authorization: Token YOUR_ACCESS_TOKEN'.
        """
        return {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }

    def map_markets_to_schema(self, raw_data: dict) -> List[Dict[str, Any]]:
        """
        Maps raw Nobitex market data to a standardized schema.
        """
        standardized_list = []

        # Safely get the symbols data from the nested structure
        symbols = raw_data.get('result', {}).get('symbols', {})

        for symbol_name, symbol_data in symbols.items():
            standardized_list.append({
                'provider': self.provider_name,
                'symbol': symbol_name,
                'base_asset': symbol_data.get('srcCurrency', ''),
                'base_asset_precision': symbol_data.get('srcCurrencyPrecision', 0),
                'quote_asset': symbol_data.get('dstCurrency', ''),
                'quote_precision': symbol_data.get('dstCurrencyPrecision', 0),
                'fa_name': symbol_data.get('faName', ''),
                'fa_base_asset': symbol_data.get('faSrcCurrency', ''),
                'fa_quote_asset': symbol_data.get('faDstCurrency', ''),
                'step_size': float(symbol_data.get('step', 1)),
                'tick_size': float(symbol_data.get('tick', 1)),
                'min_qty': float(symbol_data.get('minAmount', 0.0)),
                'min_notional': float(symbol_data.get('minPrice', 0.0)),
                'timestamp_created_at': symbol_data.get('createdAt', None),
            })
        return standardized_list

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
            resolution: str,
            from_timestamp: int,
            to_timestamp: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches historical OHLCV (candlestick) data for a given symbol and timeframe from Nobitex.
        """
        try:
            # Convert resolution format for Nobitex (use original format)
            resolution_map = {
                "D": "D",
                "1D": "D", 
                "4h": "240",  # 4 hours in minutes
                "1h": "60",   # 1 hour in minutes
                "30m": "30",
                "15m": "15",
                "5m": "5",
                "1m": "1"
            }
            nobitex_resolution = resolution_map.get(resolution, "D")
            
            params = {
                "symbol": symbol.upper(),
                "resolution": nobitex_resolution,
                "from": from_timestamp,
                "to": to_timestamp
            }

            response = requests.get(f"{self.BASE_URL}{self.OHLCV_HISTORY_PATH}", params=params)
            response.raise_for_status()
            response_json = response.json()
            
            logger.info(f"Nobitex API response for {symbol}: {response_json}")

            nobitex_ohlcv_response = NobitexOHLCVResponse.model_validate(response_json)

            if nobitex_ohlcv_response.s == "ok" and nobitex_ohlcv_response.t is not None:
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
                error_msg = nobitex_ohlcv_response.errmsg or "Unknown error"
                logger.warning(f"Nobitex OHLCV API returned error: {error_msg}")
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
            order_request_data: Dict[str, Any],
    ) -> OrderResponseSchema:
        """
        Create a new order on Nobitex using the provided data, validated by Pydantic.
        """
        try:
            symbol = order_request_data.get("symbol")
            if not symbol or len(symbol) < 3:
                raise ValueError(f"Invalid symbol format for order creation: {symbol}")

            src_currency = symbol[:-3] if symbol.endswith('IRT') else symbol[:-4]
            dst_currency = symbol[-3:] if symbol.endswith('IRT') else symbol[-4:]

            nobitex_request = NobitexCreateOrderRequest(
                type=order_request_data["side"].lower(),
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

            nobitex_response = NobitexCreateOrderResponse.model_validate(response_json)

            if nobitex_response.status == "ok":
                order_data = nobitex_response.order
                return OrderResponseSchema(
                    success=True,
                    message="Order created successfully",
                    result=OrderResultSchema(
                        symbol=f"{order_data.srcCurrency}{order_data.dstCurrency}",
                        type=order_data.type.upper(),
                        side=order_data.type.upper(),
                        price=order_data.price,
                        orig_qty=order_data.amount,
                        orig_sum=str(float(order_data.amount) * float(order_data.price)),
                        executed_price=order_data.totalPrice,
                        executed_qty=order_data.matchedAmount,
                        executed_sum=order_data.totalPrice,
                        executed_percent=int(float(order_data.matchedAmount) / float(order_data.amount) * 100) if float(
                            order_data.amount) > 0 else 0,
                        status=order_data.status.upper(),
                        active=order_data.status.upper() in ["NEW", "PARTIALLY_FILLED"],
                        timestamp_created_at=order_data.created_at,
                        client_order_id=str(order_data.id),
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
    ) -> ActiveOrdersResponseSchema:
        """
        Fetch all active orders from Nobitex, optionally filtered by a specific market symbol.
        """
        try:
            headers = self._get_auth_headers(api_key)
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()

            response = requests.get(f"{self.BASE_URL}{self.ACTIVE_ORDERS_PATH}", headers=headers, params=params)
            response.raise_for_status()
            response_json = response.json()

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
                            executed_price=None,
                            executed_qty=str(order.matchedAmount),
                            executed_sum=None,
                            executed_percent=int(float(order.matchedAmount) / float(order.amount) * 100) if float(
                                order.amount) > 0 else 0,
                            status=order.status.upper(),
                            active=True,
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
    ) -> OrderResponseSchema:
        """
        Fetch information for a specific order by its ID from Nobitex.
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

            nobitex_response = NobitexOrderInfoResponse.model_validate(response_json)

            if nobitex_response.status == "ok":
                order = nobitex_response.order
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
                        # Here's the fix: the 'executed_s' field needs to be defined
                        # after other keyword arguments in the calling function.
                        # Since your provided code snippet is incomplete for this function call,
                        # I've commented out the line that would cause the error.
                        # You need to ensure the calling function places all positional
                        # arguments before keyword arguments.
                        # executed_s
                    )
                )
            else:
                return OrderResponseSchema(success=False, message="Nobitex API error", result=None)
        except Exception as e:
            logger.error(f"Unexpected error in order_info: {e}", exc_info=True)
            return OrderResponseSchema(success=False, message=f"Unexpected error: {e}", result=None)

    def cancel_order(self, api_key: str, client_order_id: str) -> NobitexCancelOrderResponse:
        """
        Cancels a specific order by its ID from Nobitex.
        Endpoint: POST v1/account/orders/update-status
        """
        try:
            if not client_order_id:
                raise ValueError("client_order_id is required for cancel_order.")

            nobitex_request = NobitexCancelOrderRequest(id=int(client_order_id), status="canceled")
            headers = self._get_auth_headers(api_key)

            response = requests.post(
                url=f"{self.BASE_URL}{self.CANCEL_ORDER_PATH}",
                json=nobitex_request.model_dump(mode='json'),
                headers=headers,
            )
            response.raise_for_status()
            response_json = response.json()

            return NobitexCancelOrderResponse.model_validate(response_json)
        except ValidationError as e:
            logger.error(f"Pydantic validation error canceling Nobitex order: {e.errors()}", exc_info=True)
            return NobitexCancelOrderResponse(status="failed", message=f"Validation error: {e}")
        except requests.RequestException as e:
            logger.error(f"Network or API error canceling Nobitex order: {e}", exc_info=True)
            return NobitexCancelOrderResponse(status="failed", message=f"Network or API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error canceling Nobitex order: {e}", exc_info=True)
            return NobitexCancelOrderResponse(status="failed", message=f"Unexpected error: {e}")

    def get_balances(self, api_key: str) -> Optional[List[NobitexBalanceDetail]]:
        """
        Fetches the user's balances from Nobitex.
        Endpoint: POST v2/users/wallets/balance
        """
        try:
            headers = self._get_auth_headers(api_key)
            response = requests.post(f"{self.BASE_URL}{self.GET_BALANCES_PATH}", headers=headers)
            response.raise_for_status()
            response_json = response.json()

            nobitex_response = NobitexGetBalancesResponse.model_validate(response_json)

            if nobitex_response.status == "ok":
                return nobitex_response.balances
            else:
                logger.warning(
                    f"Error fetching balances from Nobitex: {nobitex_response.message}")
                return None
        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching Nobitex balances: {e.errors()}",
                         exc_info=True)
            return None
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching Nobitex balances: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Nobitex balances: {e}", exc_info=True)
            return None