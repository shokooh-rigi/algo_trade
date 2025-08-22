import pandas as pd
from typing import Dict, Any
import logging
from decimal import Decimal

from algo.strategies.strategy_interface import StrategyInterface
from algo.strategies.enums import ProcessedSideEnum
from providers.providers_enum import ProviderEnum
from algo.models import Deal, Market, AdminSystemConfig

logger = logging.getLogger(__name__)


class StrategyMacdEmaCross(StrategyInterface):
    def __init__(self, config: Dict[str, Any], provider: ProviderEnum, market: str):
        self.config = config
        self.provider = provider
        self.market_symbol = market
        self.deal = None  # This will hold the current deal instance

    def initialize(self, price_history: pd.DataFrame):
        """Initialize the strategy with historical price data."""
        # You can calculate initial indicators here if needed.
        pass

    def execute(self, data: Dict[str, Any]):
        """Execute the strategy logic with real-time data."""
        latest_price = Decimal(data['close'])

        # 1. Analyze MACD & EMA Cross
        # This part requires fetching historical data first
        # For simplicity, let's assume `data` also contains `macd` and `signal`
        macd_line = data.get('macd')
        signal_line = data.get('signal')

        if macd_line and signal_line:
            # Check for a bullish cross (MACD crosses above Signal)
            if macd_line > signal_line and self.deal is None:  # Only buy if not already in a deal
                deal_side = ProcessedSideEnum.BUY
                self._generate_deal(deal_side, latest_price)
                return "Buy signal generated"

        # 2. Analyze Order Book Depth
        order_book = data.get('order_book')
        if order_book:
            buy_volume = sum(Decimal(order[1]) for order in order_book['bids'])
            sell_volume = sum(Decimal(order[1]) for order in order_book['asks'])

            # Avoid division by zero
            if sell_volume > 0:
                buy_sell_ratio = buy_volume / sell_volume
                logger.info(f"Buy/Sell Ratio for {self.market_symbol}: {buy_sell_ratio:.2f}")

                # You can add logic here to use the ratio to confirm a signal
                # For example, only buy if macd cross and ratio > 1.2
                if self.deal and buy_sell_ratio < 0.8:
                    deal_side = ProcessedSideEnum.SELL
                    self._generate_deal(deal_side, latest_price)
                    return "Sell signal generated"

    def _generate_deal(self, side: ProcessedSideEnum, price: Decimal):
        """Create a new Deal record in the database."""
        # This method is crucial. It links the strategy signal to a database record.
        system_configs = AdminSystemConfig.get_instance()
        trade_amount_usdt = system_configs.wallex_tether_order_amount
        market_instance = Market.objects.get(symbol=self.market_symbol)

        # Assuming you want to buy/sell a fixed USDT amount
        quantity_to_trade = Decimal(trade_amount_usdt) / price

        # Adjust quantity based on market rules
        quantity_to_trade = market_instance.adjust_quantity(quantity_to_trade)

        self.deal = Deal.objects.create(
            strategy=StrategyMacdEmaCross.name,
            provider=self.provider.value,
            market=self.market_symbol,
            side=side.value,
            quantity=quantity_to_trade,
            price=price,
            is_active=True,
            processed=False,  # It will be processed by DealProcessor
        )
        logger.info(f"New deal created for {self.market_symbol} with side {side.value}")

    def get_results(self):
        """Return the results of the strategy execution."""
        # You can return the latest deal object or a summary here.
        return self.deal
