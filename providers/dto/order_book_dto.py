from typing import List, Dict, Any
from datetime import datetime

from providers.dto.dto_factory import DataTypeEnum


class OrderBookDTO:
    """
    Data Transfer Object for Order Book data.
    """

    def __init__(
            self,
            symbol: str,
            asks: List[Dict[str, str]],
            bids: List[Dict[str, str]],
            data_type: DataTypeEnum,
            timestamp: datetime = None
    ):
        self.symbol = symbol
        self.asks = asks
        self.bids = bids
        self.data_type = data_type
        self.timestamp: datetime = timestamp or datetime.now().astimezone()

    def   to_dict(self) -> Dict[str, Any]:
        """Convert the DTO to a dictionary representation."""
        return {
            'symbol': self.symbol,
            'asks': self.asks,
            'bids': self.bids,
            'data_type': self.data_type,
            'timestamp': self.timestamp.isoformat(),
        }
