import requests
import logging
from typing import Dict, Any, Optional, List

from algo_trade import settings
from providers.provider_interface import IProvider
from pydantic import ValidationError

from providers.schemas.wallex_schemas import WallexOHLCVResponse, WallexCreateOrderRequest, WallexCreateOrderResponse, \
    WallexActiveOrdersResponse, WallexOrderInfoResponse, WallexCancelOrderResponse, WallexGetBalancesResponse

logger = logging.getLogger(__name__)


class WallexProvider(IProvider):
    """
    Provider implementation for the Wallex exchange. This class handles fetching data and managing orders
    for the Wallex exchange, now with robust Pydantic data validation.
    """

    BASE_URL = settings.WALLEX_BASE_URL
    ORDER_BOOK_ALL_PATH = settings.WALLEX_ORDER_BOOK_PATH
    ORDER_BOOK_SYMBOL_PATH = settings.WALLEX_ORDER_BOOK_PATH_BY_SYMBOL
    MARKET_PATH = settings.WALLEX_MARKET_PATH
    ASSET_PATH = settings.WALLEX_ASSET_PATH
    ORDER_CREATE_PATH = settings.WALLEX_ORDER_CREATE_PATH
    ACTIVE_ORDERS_PATH = settings.WALLEX_ACTIVE_ORDERS_PATH
    ORDER_INFO_PATH = settings.WALLEX_ORDER_INFO_PATH
    CANCEL_ORDER_PATH = settings.WALLEX_CANCEL_ORDER_PATH
    GET_BALANCES_PATH = settings.WALLEX_GET_BALANCES_PATH
    OHLCV_HISTORY_PATH =settings.WALLEX_OHLCV_HISTORY_PATH

    def __init__(self, provider_config: Dict[str, Any]):
        """
        Initialize the WallexProvider with the given configuration.

        Args:
            provider_config (Dict[str, Any]): Configuration details for the provider.
        """
        self.config = provider_config

    def _get_auth_headers(self, api_key: str) -> Dict[str, str]:
        """
        Helper method to get standard authentication headers for Wallex.
        """
        return {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def map_markets_to_schema(self, raw_data: dict) -> List[Dict[str, Any]]:
        """
        Maps raw Wallex market data to a standardized schema.
        """
        standardized_list = []

        # Safely get the markets data from the nested structure
        markets = raw_data.get('payload', {}).get('markets', {})

        # Iterate over the items in the markets dictionary
        for market_key, market_data in markets.items():
            standardized_list.append({
                'provider': self.provider_name,
                'symbol': market_key,
                'base_asset': market_data.get('baseAssetSymbol', ''),
                'base_asset_precision': market_data.get('baseAssetPrecision', 0),
                'quote_asset': market_data.get('quoteAssetSymbol', ''),
                'quote_precision': market_data.get('quotePrecision', 0),
                'fa_name': market_data.get('persian_title', ''),
                'fa_base_asset': market_data.get('baseAssetSymbol', ''),  # Assuming fa_base_asset is same as base asset
                'fa_quote_asset': market_data.get('quoteAssetSymbol', ''),
                # Assuming fa_quote_asset is same as quote asset
                'step_size': float(market_data.get('stepSize', 1)),
                'tick_size': float(market_data.get('tickSize', 1)),
                'min_qty': float(market_data.get('minQty', 0.0)),
                'min_notional': float(market_data.get('minNotional', 0.0)),
                'timestamp_created_at': market_data.get('createdAt', None),
            })
        return standardized_list

    def fetch_all_order_books(self) -> Dict[str, Any]:
        """
        Fetch the latest order books for all markets on Wallex.
        Endpoint: settings.WALLEX_ORDER_BOOK_PATH
        """
        try:
            response = requests.get(f"{self.BASE_URL}{self.ORDER_BOOK_ALL_PATH}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Wallex all order books: {e}")
            return {}

    def fetch_order_book_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch the latest order book for a specific market symbol on Wallex.

        Args:
            symbol (str): The market symbol.

        Returns:
            Dict[str, Any]: A dictionary containing the order book for the given symbol.
        """
        try:
            # Wallex's specific symbol endpoint might not use query params, but direct path
            response = requests.get(f"{self.BASE_URL}{self.ORDER_BOOK_SYMBOL_PATH}{symbol}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Wallex order book for symbol {symbol}: {e}")
            return {}

    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available market information on Wallex.

        Returns:
            Dict[str, Any]: A dictionary containing market information.
        """
        try:
            response = requests.get(f"{self.BASE_URL}{self.MARKET_PATH}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Wallex markets: {e}")
            return {}

    def fetch_assets(self) -> Dict[str, Any]:
        """
        Fetch all available assets on Wallex.

        Returns:
            Dict[str, Any]: A dictionary containing asset information.
        """
        try:
            endpoint = self.ASSET_PATH
            response = requests.get(f"{self.BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Wallex assets: {e}")
            return {}

    def fetch_ohlcv_data(
            self,
            symbol: str,
            resolution: str,  # e.g., '60' for 1 hour, 'D' for 1 day, or integer seconds
            from_timestamp: int,  # Unix timestamp (seconds)
            to_timestamp: int  # Unix timestamp (seconds)
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches historical OHLCV (candlestick) data for a given symbol and timeframe from Wallex.
        NOTE: A direct public OHLCV endpoint for Wallex.ir is NOT clearly documented.
        This implementation is conceptual and uses a common API pattern.
        You MUST verify the actual endpoint, parameters, and response structure with Wallex's
        API documentation if one becomes available, or use a third-party data provider.

        Conceptual Endpoint: GET /v1/market/ohlcv?symbol={symbol}&resolution={resolution}&from={from_ts}&to={to_ts}
        Returns: List of dictionaries, each representing a candlestick (time, open, high, low, close, volume).
        """
        try:
            params = {
                "symbol": symbol.upper(),
                "resolution": resolution,
                "from": from_timestamp,
                "to": to_timestamp
            }

            # This is a placeholder URL for Wallex's OHLCV endpoint.
            # Replace with the actual URL if it exists in your settings.
            response = requests.get(f"{self.BASE_URL}{self.OHLCV_HISTORY_PATH}", params=params)
            response.raise_for_status()
            response_json = response.json()

            # Validate the conceptual response with Pydantic
            wallex_ohlcv_response = WallexOHLCVResponse.model_validate(response_json)

            if wallex_ohlcv_response.success and wallex_ohlcv_response.result:
                # Return the list of candles as dictionaries
                return [candle.model_dump() for candle in wallex_ohlcv_response.result.candles]
            else:
                logger.warning(f"Error fetching OHLCV data for {symbol} from Wallex: {wallex_ohlcv_response.message}")
                return None
        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching Wallex OHLCV data for {symbol}: {e.errors()}",
                         exc_info=True)
            return None
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching Wallex OHLCV data for {symbol}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Wallex OHLCV data for {symbol}: {e}", exc_info=True)
            return None

    def create_order(
            self,
            api_key: str,
            order_request_data: Dict[str, Any],  # Still accepting Dict for flexibility from caller
    ) -> Dict[str, Any]:
        """
        Create a new order on Wallex using the provided data, validated by Pydantic.

        Args:
            api_key (str): The API key to authenticate the request.
            order_request_data (Dict[str, Any]): Dictionary containing order details.

        Returns:
            Dict[str, Any]: A dictionary containing the order creation response,
                           parsed and validated.
        """
        try:
            # Validate the incoming order_request_data using Pydantic schema
            wallex_request = WallexCreateOrderRequest(**order_request_data)
            headers = self._get_auth_headers(api_key)

            response = requests.post(
                url=f"{self.BASE_URL}{self.ORDER_CREATE_PATH}",
                json=wallex_request.model_dump(mode='json', exclude_none=True),  # Convert Pydantic model to JSON dict
                headers=headers,
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            response_json = response.json()

            # Validate Wallex's response using the appropriate Pydantic schema
            wallex_response = WallexCreateOrderResponse.model_validate(response_json)

            if wallex_response.success and wallex_response.result:
                # Return the result as a dictionary, as per the original method signature expectation
                return {
                    "success": True,
                    "message": wallex_response.message,
                    "result": wallex_response.result.model_dump()  # Convert Pydantic result data to dict
                }
            else:
                logger.warning(f"Error creating order Wallex: {wallex_response.message}")
                return {"success": False, "message": wallex_response.message, "result": None}

        except ValidationError as e:
            logger.error(f"Pydantic validation error (request/response) creating Wallex order: {e.errors()}",
                         exc_info=True)
            return {"success": False, "message": f"Validation error: {e}", "result": None}
        except requests.RequestException as e:
            logger.error(f"Network or API error creating Wallex order: {e}", exc_info=True)
            return {"success": False, "message": f"Network or API error: {e}", "result": None}
        except Exception as e:
            logger.error(f"Unexpected error creating Wallex order: {e}", exc_info=True)
            return {"success": False, "message": f"Unexpected error: {e}", "result": None}

    def get_active_orders(
            self,
            api_key: str,
            symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch all active orders from Wallex, optionally filtered by a specific market symbol.
        Endpoint: settings.WALLEX_ACTIVE_ORDERS_PATH
        """
        try:
            endpoint = self.ACTIVE_ORDERS_PATH
            url = f"{self.BASE_URL}{endpoint}"
            headers = self._get_auth_headers(api_key)
            if symbol:
                url += f"?symbol={symbol}"  # Assuming Wallex supports symbol filter in query params

            response = requests.get(url=url, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            # Validate Wallex's response using Pydantic schema
            wallex_response = WallexActiveOrdersResponse.model_validate(response_json)

            if wallex_response.success and wallex_response.result:
                # Return the result as a dictionary, including the list of order dicts
                return {
                    "success": True,
                    "message": wallex_response.message,
                    "result": {
                        "orders": [order.model_dump() for order in wallex_response.result.orders]
                    }
                }
            else:
                logger.warning(f"Error fetching active orders Wallex: {wallex_response.message}")
                return {"success": False, "message": wallex_response.message, "result": None}
        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching active orders: {e.errors()}", exc_info=True)
            return {"success": False, "message": f"Validation error: {e}", "result": None}
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching active orders: {e}", exc_info=True)
            return {"success": False, "message": f"Network or API error: {e}", "result": None}
        except Exception as e:
            logger.error(f"Unexpected error fetching active orders: {e}", exc_info=True)
            return {"success": False, "message": f"Unexpected error: {e}", "result": None}

    def order_info(
            self,
            api_key: str,
            client_order_id: str = None,
    ) -> Dict[str, Any]:
        """
        Fetch information for a specific order by its ID from Wallex.
        Endpoint: settings.WALLEX_ORDER_INFO_PATH + client_order_id
        """
        try:
            if not client_order_id:
                raise ValueError("client_order_id is required for order_info.")

            headers = self._get_auth_headers(api_key)
            response = requests.get(
                url=f"{self.BASE_URL}{self.ORDER_INFO_PATH}{client_order_id}",
                headers=headers
            )
            response.raise_for_status()
            response_json = response.json()

            # Validate Wallex's response
            wallex_response = WallexOrderInfoResponse.model_validate(response_json)

            if wallex_response.success and wallex_response.result:
                # Return the result as a dictionary
                return {
                    "success": True,
                    "message": wallex_response.message,
                    "result": wallex_response.result.model_dump()
                }
            else:
                logger.warning(
                    f"Error fetching order info for client_order_id {client_order_id}: {wallex_response.message}")
                return {"success": False, "message": wallex_response.message, "result": None}
        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching order info: {e.errors()}", exc_info=True)
            return {"success": False, "message": f"Validation error: {e}", "result": None}
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching order info for client_order_id {client_order_id}: {e}",
                         exc_info=True)
            return {"success": False, "message": f"Network or API error: {e}", "result": None}
        except Exception as e:
            logger.error(f"Unexpected error fetching order info for client_order_id {client_order_id}: {e}",
                         exc_info=True)
            return {"success": False, "message": f"Unexpected error: {e}", "result": None}

    def cancel_order(
            self,
            api_key: str,
            order_id: str,
    ) -> Dict[str, Any]:
        """
        Cancel an existing order by its ID on Wallex.
        Endpoint: DELETE settings.WALLEX_CANCEL_ORDER_PATH + ?clientOrderId={order_id}
        """
        try:
            headers = self._get_auth_headers(api_key)
            response = requests.delete(
                url=f"{self.BASE_URL}{self.CANCEL_ORDER_PATH}?clientOrderId={order_id}",
                headers=headers,
            )
            response.raise_for_status()
            response_json = response.json()

            wallex_response = WallexCancelOrderResponse.model_validate(response_json)

            if wallex_response.success:
                return {"success": True, "message": wallex_response.message, "result": None}
            else:
                logger.warning(f"Error canceling Wallex order for order_id {order_id}: {wallex_response.message}")
                return {"success": False, "message": wallex_response.message, "result": None}
        except ValidationError as e:
            logger.error(f"Pydantic validation error canceling order: {e.errors()}", exc_info=True)
            return {"success": False, "message": f"Validation error: {e}", "result": None}
        except requests.RequestException as e:
            logger.warning(f"Network or API error canceling Wallex order for order_id {order_id}: {e}", exc_info=True)
            return {"success": False, "message": f"Network or API error: {e}", "result": None}
        except Exception as e:
            logger.error(f"Unexpected error canceling Wallex order for order_id {order_id}: {e}", exc_info=True)
            return {"success": False, "message": f"Unexpected error: {e}", "result": None}

    def get_balances(self, api_key: str) -> Dict[str, Any]:
        """
        Fetch the balance details for a Wallex user account.
        Endpoint: settings.WALLEX_GET_BALANCES_PATH
        """
        try:
            headers = self._get_auth_headers(api_key)
            response = requests.get(
                url=f"{self.BASE_URL}{self.GET_BALANCES_PATH}",
                headers=headers,
            )
            response.raise_for_status()
            response_json = response.json()

            wallex_response = WallexGetBalancesResponse.model_validate(response_json)

            if wallex_response.success and wallex_response.result:
                # Return the balances list as a list of dictionaries
                return {"success": True, "message": wallex_response.message,
                        "result": [bal.model_dump() for bal in wallex_response.result.balances]}
            else:
                logger.error(f"Error fetching balances for a Wallex account: {wallex_response.message}")
                return {"success": False, "message": wallex_response.message, "result": None}
        except ValidationError as e:
            logger.error(f"Pydantic validation error fetching balances: {e.errors()}", exc_info=True)
            return {"success": False, "message": f"Validation error: {e}", "result": None}
        except requests.RequestException as e:
            logger.error(f"Network or API error fetching balances for a Wallex account: {e}", exc_info=True)
            return {"success": False, "message": f"Network or API error: {e}", "result": None}
        except Exception as e:
            logger.error(f"Unexpected error fetching balances for a Wallex account: {e}", exc_info=True)
            return {"success": False, "message": f"Unexpected error: {e}", "result": None}
