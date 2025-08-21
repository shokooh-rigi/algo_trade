import requests
import logging
from typing import Dict, Any

from algo_trade import settings
from providers.provider_interface import IProvider

logger = logging.getLogger(__name__)


class NobitexProvider(IProvider):
    """
    Provider implementation for the Nobitex exchange. This class handles fetching data and managing orders
    for the Nobitex exchange.
    """

    BASE_URL = settings.NOBITEX_BASE_URL

    def __init__(self, provider_config: Dict[str, Any]):
        """
        Initialize the NobitexProvider with the given configuration.

        Args:
            provider_config (Dict[str, Any]): Configuration details, such as API keys and connection parameters.
        """
        self.config = provider_config

    def fetch_all_order_books(self) -> Dict[str, Any]:
        """
        Fetch the latest order books for all markets on Nobitex.

        Returns:
            Dict[str, Any]: A dictionary containing order books for all markets.
        """
        try:
            endpoint = settings.NOBITEX_ORDER_BOOK_PATH
            response = requests.get(f"{self.BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex order books: {e}")
            return {}

    def fetch_order_book_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch the latest order book for a specific market symbol on Nobitex.

        Args:
            symbol (str): The market symbol.

        Returns:
            Dict[str, Any]: A dictionary containing the order book for the given symbol.
        """
        try:
            endpoint = settings.NOBITEX_ORDER_BOOK_PATH_BY_SYMBOL
            response = requests.get(f"{self.BASE_URL}{endpoint}{symbol}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex order book for symbol {symbol}: {e}")
            return {}

    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available market information on Nobitex.

        Returns:
            Dict[str, Any]: A dictionary containing market information.
        """
        try:
            endpoint = settings.NOBITEX_MARKET_PATH
            response = requests.get(f"{self.BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex markets: {e}")
            return {}

    def fetch_assets(self) -> Dict[str, Any]:
        """
        Fetch all available assets on Nobitex.

        Returns:
            Dict[str, Any]: A dictionary containing asset information.
        """
        try:
            endpoint = settings.NOBITEX_ASSET_PATH
            response = requests.get(f"{self.BASE_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching Nobitex assets: {e}")
            return {}

    def create_order(
            self,
            api_key: str,
            order_request_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new order on Nobitex using the provided schema.

        Args:
            api_key (str): The API key to authenticate the request.
            order_request_schema (Dict[str, Any]): Schema containing order details such as type, amount, and price.

        Returns:
            Dict[str, Any]: A dictionary containing the order creation response.
        """
        try:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            }
            endpoint = settings.NOBITEX_ORDER_CREATE_PATH
            response = requests.post(
                url=f"{self.BASE_URL}{endpoint}",
                json=order_request_schema,
                headers=headers,
            )
            logger.info(f"Response of create order Nobitex: {response}")
            response =response.json()
            if response.get("success"):
                return response
            else:
                logger.warning(f"Error creating order Nobitex: {response}")
                return {}

        except requests.RequestException as e:
            logger.error(f"Error creating Nobitex order: {e}")
            return {}

    def get_active_orders(
            self,
            api_key: str,
            symbol: str = None,
    ) -> Dict[str, Any]:
        """
        Fetch all active orders, optionally filtered by a specific market symbol.

        Args:
            api_key (str): The API key to authenticate the request.
            symbol (str, optional): Market symbol to filter active orders. Defaults to None.

        Returns:
            Dict[str, Any]: A dictionary containing active order details.
        """
        try:
            endpoint = settings.NOBITEX_ACTIVE_ORDERS_PATH
            url = f"{self.BASE_URL}{endpoint}"
            headers = {
                "X-API-Key": api_key
            }
            if symbol:
                url += f"?symbol={symbol}"
            response = requests.get(url=url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching active orders: {e}")
            return {}

    def order_info(
            self,
            api_key: str,
            client_order_id: str = None,
    ) -> Dict[str, Any]:
        """
        Fetch information for a specific order by its ID.

        Args:
            api_key (str): The API key to authenticate the request.
            client_order_id (str): The unique identifier of the order.

        Returns:
            Dict[str, Any]: A dictionary containing order details.
        """
        try:
            endpoint = settings.NOBITEX_ORDER_INFO_PATH
            headers = {
                "X-API-Key": api_key
            }
            response = requests.get(
                url=f"{self.BASE_URL}{endpoint}{client_order_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching order info for client_order_id {client_order_id}: {e}")
            return {}

    def cancel_order(
            self,
            api_key: str,
            order_id: str,
    ) -> Dict[str, Any]:
        """
        Cancel an existing order by its ID.

        Args:
            api_key (str): The API key to authenticate the request.
            order_id (str): The unique identifier of the order to cancel.

        Returns:
            Dict[str, Any]: A dictionary containing the response to the cancellation request.
        """
        try:
            endpoint = settings.NOBITEX_CANCEL_ORDER_PATH
            headers = {
                "X-API-Key": api_key
            }
            response = requests.delete(
                url=f"{self.BASE_URL}{endpoint}?clientOrderId={order_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Error canceling Nobitex order for order_id {order_id}: {e}")
            return {}

    def get_balances(self, api_key: str) -> Dict[str, Any]:
        """
        Fetch the balance details for a Nobitex user account.

        Args:
            api_key (str): The API key to authenticate the request.

        Returns:
            Dict[str, Any]: A dictionary containing the balance details.
        """
        try:
            endpoint = settings.NOBITEX_GET_BALANCES_PATH
            headers = {
                "X-API-Key": api_key
            }
            response = requests.get(
                url=f"{self.BASE_URL}{endpoint}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching balances for a Nobitex account: {e}")
            return {}
