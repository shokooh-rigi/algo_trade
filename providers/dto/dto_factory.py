from algo.strategies.enums import StrategyEnum
from providers.dto.mid_price_dto import MidPriceDTO
from providers.dto.order_book_dto import OrderBookDTO


class DataTypeEnum:
    pass


class DTOFactory:
    """
    Factory class to generate the appropriate DTO based on the strategy name.
    """

    @staticmethod
    def create_dto(strategy_name: str, raw_data: dict, data_type: DataTypeEnum):
        if strategy_name == StrategyEnum.StrategyMacdEmaCross.name:
            if data_type == DataTypeEnum.LIVE_ORDER_BOOK.value:
                return OrderBookDTO(
                    symbol=raw_data.get('symbol'),
                    asks=raw_data.get('asks'),
                    bids=raw_data.get('bids'),
                    data_type=DataTypeEnum.LIVE_ORDER_BOOK,
                )
            elif data_type == DataTypeEnum.HISTORICAL_MID_PRICE.value:
                return MidPriceDTO(
                    symbol=raw_data.get('symbol'),
                    mid_price=raw_data.get('mid_price'),
                    timestamp=raw_data.get('timestamp'),
                    data_type=DataTypeEnum.HISTORICAL_MID_PRICE,

                )
        # Add other strategy DTOs here as needed
        else:
            raise ValueError(f"No DTO found for strategy: {strategy_name}")
