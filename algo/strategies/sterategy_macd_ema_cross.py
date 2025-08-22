from datetime import datetime, timedelta

import pandas as pd
from typing import Dict, Any, Optional, List
import logging
from decimal import Decimal, getcontext
import time  # For Unix timestamps
import pandas_ta as ta  # Import the pandas_ta library

from algo.strategies.strategy_interface import StrategyInterface
from algo.strategies.enums import ProcessedSideEnum, StrategyState
from providers.providers_enum import ProviderEnum
from algo.models import Deal, Market, AdminSystemConfig, StoreClient
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

# Set decimal precision for financial calculations
getcontext().prec = 10  # Adjust precision as needed for your markets


class StrategyMacdEmaCross(StrategyInterface):
    """
    Implements a trading strategy based on MACD cross, EMA cross,
    volume analysis, and order book depth, utilizing pandas_ta for indicators.
    """

    # Default indicator periods (can be overridden by config)
    DEFAULT_FAST_EMA = 12
    DEFAULT_SLOW_EMA = 26
    DEFAULT_SIGNAL_EMA = 9
    DEFAULT_SHORT_EMA = 50
    DEFAULT_LONG_EMA = 200
    DEFAULT_ORDER_BOOK_DEPTH_THRESHOLD = 0.8  # Ratio below which to consider selling pressure (e.g., if bids/asks < 0.8, strong sell pressure)

    def __init__(self, config: Dict[str, Any], provider_name: ProviderEnum, market_symbol: str):
        self.config = config
        self.provider_name = provider_name
        self.market_symbol = market_symbol
        self.current_deal: Optional[Deal] = None  # Tracks the active deal for this strategy instance
        self.price_history: pd.DataFrame = pd.DataFrame()  # Stores OHLCV data for calculations
        self.provider_instance = None  # Will be initialized in initialize method

        # Load indicator periods from config or use defaults
        self.fast_ema_period = config.get('fast_ema_period', self.DEFAULT_FAST_EMA)
        self.slow_ema_period = config.get('slow_ema_period', self.DEFAULT_SLOW_EMA)
        self.signal_ema_period = config.get('signal_ema_period', self.DEFAULT_SIGNAL_EMA)
        self.short_ema_period = config.get('short_ema_period', self.DEFAULT_SHORT_EMA)
        self.long_ema_period = config.get('long_ema_period', self.DEFAULT_LONG_EMA)
        self.order_book_depth_threshold = Decimal(
            str(config.get('order_book_depth_threshold', self.DEFAULT_ORDER_BOOK_DEPTH_THRESHOLD)))

        logger.info(f"Strategy {self.__class__.__name__} initialized for {market_symbol} on {provider_name.value}.")

    def initialize(self, initial_history_period_days: int = 30, resolution: str = 'D'):
        """
        Initializes the strategy by fetching historical data and calculating initial indicators.
        Args:
            initial_history_period_days (int): Number of days of historical data to fetch initially.
            resolution (str): The resolution for historical data (e.g., '60' for 1 hour, 'D' for 1 day).
        """
        logger.info(
            f"Initializing strategy for {self.market_symbol} on {self.provider_name.value} with {initial_history_period_days} days history and resolution {resolution}.")

        # Get provider instance
        try:
            self.provider_instance = ProviderFactory.create_provider(
                provider_name=self.provider_name.value,  # Pass the string value of the enum
                provider_config={}  # Add provider-specific config if needed
            )
        except ValueError as e:
            logger.error(f"Failed to create provider instance for {self.provider_name.value}: {e}", exc_info=True)
            raise

        # Fetch historical data
        end_timestamp = int(time.time())
        start_timestamp = int((datetime.now() - timedelta(days=initial_history_period_days)).timestamp())

        raw_ohlcv = self._fetch_historical_data(start_timestamp, end_timestamp, resolution=resolution)

        if raw_ohlcv:
            self.price_history = pd.DataFrame(raw_ohlcv)
            self.price_history['time'] = pd.to_datetime(self.price_history['time'], unit='s')
            self.price_history = self.price_history.set_index('time')
            self._calculate_all_indicators()
            logger.info(f"Initial indicators calculated for {self.market_symbol}.")
        else:
            logger.warning(
                f"Could not fetch initial historical data for {self.market_symbol}. Strategy might not function correctly.")

        # Check for any active deals for this strategy/market
        self.current_deal = Deal.objects.filter(
            strategy_name=self.__class__.__name__,
            market_symbol=self.market_symbol,
            provider_name=self.provider_name.value,
            is_active=True,
            is_processed=False  # Still waiting for an order to be placed/filled
        ).order_by('-created_at').first()

        if self.current_deal:
            logger.info(f"Found existing active deal {self.current_deal.client_deal_id} for {self.market_symbol}.")

    def execute(self, latest_data: Dict[str, Any]):
        """
        Executes the strategy logic with real-time data.
        This method is called periodically with the latest market data.

        Args:
            latest_data (Dict[str, Any]): Contains the latest OHLCV data (e.g., current candle)
                                         and real-time order book data.
                                         Expected keys: 'time', 'open', 'high', 'low', 'close', 'volume', 'order_book'.
        """
        logger.debug(f"Executing strategy for {self.market_symbol} with latest data.")

        # Ensure provider_instance is initialized
        if not self.provider_instance:
            logger.error(f"Provider instance not initialized for {self.market_symbol}. Skipping execution.")
            return

        # 1. Update historical data with latest candle
        new_candle_time = pd.to_datetime(latest_data['time'], unit='s')
        new_candle_data = {k: latest_data[k] for k in ['open', 'high', 'low', 'close', 'volume']}
        new_candle_df = pd.DataFrame([new_candle_data], index=[new_candle_time])

        # Append new data, handling potential duplicates (e.g., if same candle is sent twice)
        if not self.price_history.empty and new_candle_time in self.price_history.index:
            self.price_history.loc[new_candle_time] = new_candle_df.loc[new_candle_time]
        else:
            self.price_history = pd.concat([self.price_history, new_candle_df])

        # Keep only necessary history for calculations to manage memory
        # Need enough data for the longest indicator period + a few extra for initial calculations
        max_period = max(self.long_ema_period, self.slow_ema_period + self.signal_ema_period)
        self.price_history = self.price_history.iloc[-(max_period + 5):]  # Keep a buffer

        # Recalculate all indicators
        self._calculate_all_indicators()

        # Ensure there's enough data for indicator lookback
        if len(self.price_history) < max_period:
            logger.warning(
                f"Not enough historical data for {self.market_symbol} to calculate all indicators. Current data points: {len(self.price_history)}. Required: {max_period}. Skipping signal generation.")
            return

        # Get latest indicator values
        latest_close_price = Decimal(str(self.price_history['close'].iloc[-1]))
        latest_macd = self.price_history['macd'].iloc[-1]
        latest_signal = self.price_history['signal'].iloc[-1]
        latest_short_ema = self.price_history['short_ema'].iloc[-1]
        latest_long_ema = self.price_history['long_ema'].iloc[-1]
        latest_volume = Decimal(str(self.price_history['volume'].iloc[-1]))

        # Get previous indicator values for crossover detection
        prev_macd = self.price_history['macd'].iloc[-2]
        prev_signal = self.price_history['signal'].iloc[-2]
        prev_short_ema = self.price_history['short_ema'].iloc[-2]
        prev_long_ema = self.price_history['long_ema'].iloc[-2]

        # 2. Analyze Order Book Depth
        order_book_ratio = Decimal('1.0')
        order_book_data = latest_data.get('order_book')
        if order_book_data and 'bids' in order_book_data and 'asks' in order_book_data:
            buy_volume = sum(Decimal(str(order[1])) for order in order_book_data['bids'])
            sell_volume = sum(Decimal(str(order[1])) for order in order_book_data['asks'])

            if sell_volume > 0:
                order_book_ratio = buy_volume / sell_volume
            else:  # All buy orders, strong buy pressure
                order_book_ratio = Decimal('1000000')  # Effectively infinite, indicating extreme buy pressure

            logger.debug(f"Order Book Buy/Sell Ratio for {self.market_symbol}: {order_book_ratio:.2f}")

        # 3. Decision Logic
        # Condition 1: MACD Crossover (Bullish/Bearish)
        macd_cross_buy_signal = (latest_macd > latest_signal) and (prev_macd <= prev_signal)
        macd_cross_sell_signal = (latest_macd < latest_signal) and (prev_macd >= prev_signal)

        # Condition 2: EMA Crossover (Golden Cross/Death Cross)
        ema_cross_buy_signal = (latest_short_ema > latest_long_ema) and (prev_short_ema <= prev_long_ema)
        ema_cross_sell_signal = (latest_short_ema < latest_long_ema) and (prev_short_ema >= prev_long_ema)

        # Condition 3: Volume Confirmation (example: higher than average volume)
        # Calculate average volume over a recent period (e.g., same as fast EMA period)
        if len(self.price_history) >= self.fast_ema_period:
            avg_volume = self.price_history['volume'].iloc[-self.fast_ema_period:].mean()
            volume_confirmation = latest_volume > Decimal(str(avg_volume * Decimal('1.2')))  # 20% higher than average
        else:
            volume_confirmation = False  # Not enough data for volume confirmation

        # Condition 4: Order Book Depth Confirmation
        buy_pressure_confirmation = order_book_ratio > Decimal('1.0')  # More buy volume than sell
        sell_pressure_confirmation = order_book_ratio < self.order_book_depth_threshold  # Significant selling pressure

        # Generate BUY signal
        # Combine MACD OR EMA cross with volume and buy pressure confirmation
        if (macd_cross_buy_signal or ema_cross_buy_signal) and volume_confirmation and buy_pressure_confirmation:
            # Only generate a new BUY deal if no active deal or the last deal was a SELL
            if not self.current_deal or self.current_deal.side == ProcessedSideEnum.SELL.value:
                logger.info(
                    f"Strong BUY signal for {self.market_symbol} at {latest_close_price}. MACD Cross: {macd_cross_buy_signal}, EMA Cross: {ema_cross_buy_signal}, Volume Conf: {volume_confirmation}, Buy Pressure: {buy_pressure_confirmation}.")
                self._generate_deal(ProcessedSideEnum.BUY, latest_close_price)
                return "Buy signal generated"

        # Generate SELL signal
        # Combine MACD OR EMA cross with volume and sell pressure confirmation
        elif (macd_cross_sell_signal or ema_cross_sell_signal) and volume_confirmation and sell_pressure_confirmation:
            # Only generate a SELL deal if there's an active BUY deal to close
            if self.current_deal and self.current_deal.side == ProcessedSideEnum.BUY.value:
                logger.info(
                    f"Strong SELL signal for {self.market_symbol} at {latest_close_price}. MACD Cross: {macd_cross_sell_signal}, EMA Cross: {ema_cross_sell_signal}, Volume Conf: {volume_confirmation}, Sell Pressure: {sell_pressure_confirmation}.")
                self._generate_deal(ProcessedSideEnum.SELL, latest_close_price)
                return "Sell signal generated"

        logger.debug(f"No strong signal for {self.market_symbol}.")
        return "No signal"

    def _fetch_historical_data(self, start_ts: int, end_ts: int, resolution: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches historical OHLCV data from the provider.
        """
        try:
            # The provider's fetch_ohlcv_data returns a list of dictionaries
            # where each dict is a candle (time, open, high, low, close, volume)
            ohlcv_data = self.provider_instance.fetch_ohlcv_data(
                symbol=self.market_symbol,
                resolution=resolution,
                from_timestamp=start_ts,
                to_timestamp=end_ts
            )
            return ohlcv_data
        except Exception as e:
            logger.error(f"Error fetching historical OHLCV data for {self.market_symbol}: {e}", exc_info=True)
            return None

    def _calculate_all_indicators(self) -> None:
        """
        Calculates all necessary indicators and updates price_history DataFrame using pandas_ta.
        Converts float results from pandas_ta back to Decimal for precision.
        """
        if self.price_history.empty:
            return

        # Ensure 'close' and 'volume' columns are numeric (float) for pandas_ta
        # Create temporary float columns for calculations
        self.price_history['close_float'] = self.price_history['close'].astype(float)
        self.price_history['volume_float'] = self.price_history['volume'].astype(float)

        # Calculate MACD
        # pandas_ta creates 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9' columns by default
        macd_output = ta.macd(
            self.price_history['close_float'],
            fast=self.fast_ema_period,
            slow=self.slow_ema_period,
            signal=self.signal_ema_period,
            append=True  # Appends directly to the DataFrame
        )

        # Map pandas_ta output columns back to your desired names and convert to Decimal
        macd_col_name = f'MACD_{self.fast_ema_period}_{self.slow_ema_period}_{self.signal_ema_period}'
        signal_col_name = f'MACDs_{self.fast_ema_period}_{self.slow_ema_period}_{self.signal_ema_period}'

        if macd_col_name in self.price_history.columns and signal_col_name in self.price_history.columns:
            self.price_history['macd'] = self.price_history[macd_col_name].apply(
                lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
            self.price_history['signal'] = self.price_history[signal_col_name].apply(
                lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
        else:
            logger.warning(
                f"MACD columns not found after calculation for {self.market_symbol}. Check pandas_ta version or parameters.")
            self.price_history['macd'] = Decimal('0')
            self.price_history['signal'] = Decimal('0')

        # Calculate EMAs
        self.price_history['short_ema'] = ta.ema(
            self.price_history['close_float'],
            length=self.short_ema_period,
            append=False  # Don't append directly, we'll assign
        ).apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))

        self.price_history['long_ema'] = ta.ema(
            self.price_history['close_float'],
            length=self.long_ema_period,
            append=False  # Don't append directly, we'll assign
        ).apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))

        # Clean up temporary float columns
        self.price_history.drop(columns=['close_float', 'volume_float'], errors='ignore', inplace=True)

    def _generate_deal(self, side: ProcessedSideEnum, price: Decimal):
        """
        Creates a new Deal record in the database or updates an existing one.
        """
        # Ensure only one active deal of the same side is being managed by this strategy instance
        # If there's an active deal and it's on the same side, don't create a new one.
        # This prevents opening multiple buy positions without closing the previous one.
        if self.current_deal and self.current_deal.is_active and self.current_deal.side == side.value:
            logger.info(
                f"An active {side.value} deal already exists ({self.current_deal.client_deal_id}). Not creating a new one.")
            return

        system_configs = AdminSystemConfig.get_instance()
        trade_amount_quote_currency = Decimal(
            str(system_configs.wallex_tether_order_amount))  # Assuming this is a base amount in quote currency (e.g., USDT)

        try:
            market_instance = Market.objects.get(symbol=self.market_symbol, provider=self.provider_name.value)
        except Market.DoesNotExist:
            logger.error(
                f"Market {self.market_symbol} not found for provider {self.provider_name.value}. Cannot generate deal.")
            return

        # Calculate quantity based on desired trade amount and current price
        if price > 0:
            # For a BUY deal, trade_amount_quote_currency is the budget in quote currency.
            # For a SELL deal, it might represent the amount of base currency to sell,
            # or the target quote currency amount to receive.
            # Here, assuming trade_amount_quote_currency is a budget/target in the quote currency.
            calculated_quantity = trade_amount_quote_currency / price
        else:
            logger.error(f"Invalid price ({price}) for deal generation. Cannot calculate quantity.")
            return

        # Adjust quantity based on market rules (step_size, min_qty)
        # Convert Decimal to float for market_instance.adjust_quantity, then back to Decimal
        adjusted_quantity = Decimal(str(market_instance.adjust_quantity(float(calculated_quantity))))
        adjusted_price = Decimal(str(market_instance.adjust_price(float(price))))

        # Ensure adjusted quantity meets minimums
        adjusted_quantity = Decimal(str(market_instance.adjust_min_qty(float(adjusted_quantity))))

        if adjusted_quantity <= 0:
            logger.error(f"Adjusted quantity is zero or negative ({adjusted_quantity}). Cannot create deal.")
            return

        # Create a new Deal record
        self.current_deal = Deal.objects.create(
            strategy_name=self.__class__.__name__,
            provider_name=self.provider_name.value,
            market_symbol=self.market_symbol,
            side=side.value,
            quantity=adjusted_quantity,
            price=adjusted_price,
            is_active=True,
            is_processed=False,  # It will be processed by DealProcessor
            status=StrategyState.STARTED.value  # Initial state for a new deal
        )
        logger.info(
            f"New deal {self.current_deal.client_deal_id} created for {self.market_symbol} with side {side.value} at {adjusted_price} for {adjusted_quantity}.")

    def get_results(self):
        """
        Returns the current active deal object if any.
        """
        return self.current_deal
