from typing import Dict, Any
from datetime import datetime

from providers.dto.dto_factory import DataTypeEnum


class MidPriceDTO:
    """
    Data Transfer Object for Mid Price data.
    """

    def __init__(
            self,
            symbol: str,
            mid_price: float,
            timestamp: datetime,
            data_type : DataTypeEnum,
    ):
        """
        Initialize MidPriceDTO.

        Args:
            symbol (str): The trading pair symbol (e.g., BTC/USDT).
            mid_price (float): The calculated mid-price.
            timestamp (datetime, optional): The timestamp of the mid-price calculation in local timezone.
                                            Defaults to the current local time.
            data_type (DataTypeEnum, optional): The data type of the mid-price.
        """
        self.symbol = symbol
        self.mid_price = mid_price
        self.timestamp = timestamp or datetime.now().astimezone()
        self.data_type = data_type
    def to_dict(self) -> Dict[str, Any]:
        """Convert the DTO to a dictionary representation."""
        return {
            'symbol': self.symbol,
            'mid_price': self.mid_price,
            'timestamp': self.timestamp.isoformat(),  # زمان به فرمت استاندارد ISO 8601
            'data_type': self.data_type,
        }
