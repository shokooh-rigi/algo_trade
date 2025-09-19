from abc import ABC, abstractmethod
from typing import Any, Dict, List

from providers.schemas.wallex_schemas import OrderResponseSchema


class IProvider(ABC):
    """
    Abstract base class representing a provider interface for market data and order management.

    Subclasses should implement methods to handle fetching market data, managing orders, and other provider-specific actions.
    """

    @abstractmethod
    def fetch_all_order_books(self) -> Dict[str, Any]:
        """
        Fetch the latest order books for all markets.

        Returns:
            Dict[str, Any]: A dictionary containing data for all order books.
        """
        pass

    @abstractmethod
    def fetch_order_book_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch the latest order book for a specific market symbol.

        Args:
            symbol (str): The market symbol for which to fetch the order book.

        Returns:
            Dict[str, Any]: A dictionary containing the order book data for the given symbol.
        """
        pass

    @abstractmethod
    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available market information.

        Returns:
            Dict[str, Any]: A dictionary containing market data.
        """
        pass

    @abstractmethod
    def fetch_assets(self) -> Dict[str, Any]:
        """
        Fetch all available assets.

        Returns:
            Dict[str, Any]: A dictionary containing asset data.
        """
        pass

    @abstractmethod
    def create_order(
            self,
            api_key: str,
            order_request_schema: Dict[str, Any],
    ) -> OrderResponseSchema :
        """
        Create a new order based on the provided request schema.

        Args:
            api_key (str): The API key associated with the client account, used for authentication.
            order_request_schema (Dict[str, Any]): Schema containing order details, such as type, amount, and price.

        Returns:
            Dict[str, Any]: A dictionary containing the response from the order creation request.
        """
        pass

    @abstractmethod
    def get_active_orders(
            self,
            api_key: str,
            symbol: str = None,
    ) -> Dict[str, Any]:
        """
        Fetch all active orders, optionally filtered by a specific symbol.

        Args:
            api_key (str): The API key associated with the client account, used for authentication.
            symbol (str, optional): Market symbol to filter active orders. Defaults to None.

        Returns:
            Dict[str, Any]: A dictionary containing active order details.
        """
        pass

    @abstractmethod
    def order_info(
            self,
            api_key: str,
            client_order_id: str,
    ) -> OrderResponseSchema :
        """
        Fetch details for a specific order by its ID.

        Args:
            api_key (str): The API key associated with the client account, used for authentication.
            client_order_id (str): Unique identifier of the order.

        Returns:
            Dict[str, Any]: A dictionary containing order information.
        """
        pass

    @abstractmethod
    def get_balances(self, api_key: str) -> Dict[str, Any]:
        """
        Fetch the balance details for a user account.

        Args:
            api_key (str): The API key associated with the client account, used for authentication.

        Returns:
            Dict[str, Any]: A dictionary containing balance details.
        """
        pass

    @abstractmethod
    def cancel_order(
            self,
            api_key: str,
            order_id: str,
    ) -> Dict[str, Any]:
        """
        Cancel an order by its ID.

        Args:
            api_key (str): The API key associated with the client account, used for authentication.
            order_id (str): Unique identifier of the order to be canceled.

        Returns:
            Dict[str, Any]: A dictionary containing the response from the cancellation request.
        """
        pass

    @abstractmethod
    def map_markets_to_schema(
            self,
            raw_data: dict
    ) -> List[Dict[str, Any]]:
        pass