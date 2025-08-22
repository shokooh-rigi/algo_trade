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
from algo.models import Deal, Market, AdminSystemConfig, StoreClient, StrategyConfig
from providers.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)

# Set decimal precision for financial calculations
getcontext().prec = 10  # Adjust precision as needed for your markets

class StrategyMacdEmaCross(StrategyInterface):
    """
    Implements a trading strategy based on MACD cross, EMA cross,
    volume analysis, and order book depth, utilizing pandas_ta for indicators.
    Configuration is loaded from a StrategyConfig model.
    """

    def __init__(self, strategy_config_id: int, provider_name: ProviderEnum, market_symbol: str):
        """
        Initializes the strategy with a StrategyConfig ID.
        Args:
            strategy_config_id (int): The ID of the StrategyConfig instance for this strategy.
            provider_name (ProviderEnum): The enum representing the trading provider.
            market_symbol (str): The trading pair symbol.
        """
        self.strategy_config_id = strategy_config_id
        self.provider_name = provider_name
        self.market_symbol = market_symbol
        self.current_deal: Optional[Deal] = None
        self.price_history: pd.DataFrame = pd.DataFrame()
        self.provider_instance = None
        self.strategy_config: Optional[StrategyConfig] = None  # Store the StrategyConfig instance
        self.strategy_params = None  # Store validated strategy_configs from Pydantic schema

        # Parameters will be loaded in initialize()
        self.fast_ema_period = None
        self.slow_ema_period = None
        self.signal_ema_period = None
        self.short_ema_period = None
        self.long_ema_period = None
        self.order_book_depth_threshold = None
        self.initial_history_period_days = None
        self.resolution = None

        logger.info(
            f"Strategy {self.__class__.__name__} initialized for {market_symbol} on {provider_name.value} with config ID {strategy_config_id}.")

    def initialize(self):
        """
        Initializes the strategy by loading configuration from the database,
        fetching historical data, and calculating initial indicators.
        """
        logger.info(f"Loading configuration for StrategyConfig ID: {self.strategy_config_id}")
        try:
            self.strategy_config = StrategyConfig.objects.get(id=self.strategy_config_id)
            # Validate and load strategy-specific parameters using Pydantic schema
            self.strategy_params = self.strategy_config.get_config()

            self.fast_ema_period = self.strategy_params.fast_ema_period
            self.slow_ema_period = self.strategy_params.slow_ema_period
            self.signal_ema_period = self.strategy_params.signal_ema_period
            self.short_ema_period = self.strategy_params.short_ema_period
            self.long_ema_period = self.strategy_params.long_ema_period
            self.order_book_depth_threshold = Decimal(str(self.strategy_params.order_book_depth_threshold))
            self.initial_history_period_days = self.strategy_config.initial_history_period_days
            self.resolution = self.strategy_config.resolution

            logger.info(f"Strategy parameters loaded: {self.strategy_params.model_dump_json()}")

        except StrategyConfig.DoesNotExist:
            logger.error(f"StrategyConfig with ID {self.strategy_config_id} not found. Cannot initialize strategy.")
            raise
        except ValueError as e:
            logger.error(f"Error validating strategy configuration for ID {self.strategy_config_id}: {e}",
                         exc_info=True)
            raise

        # Get provider instance
        try:
            self.provider_instance = ProviderFactory.create_provider(
                provider_name=self.provider_name.value,
                provider_config={}
            )
        except ValueError as e:
            logger.error(f"Failed to create provider instance for {self.provider_name.value}: {e}", exc_info=True)
            raise

        # Fetch historical data if needed
        if self.strategy_config.need_historical_data:
            logger.info(
                f"Fetching {self.initial_history_period_days} days of history for {self.market_symbol} with resolution {self.resolution}.")
            end_timestamp = int(time.time())
            start_timestamp = int((datetime.now() - timedelta(days=self.initial_history_period_days)).timestamp())

            raw_ohlcv = self._fetch_historical_data(start_timestamp, end_timestamp, resolution=self.resolution)

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
            is_processed=False
        ).order_by('-created_at').first()

        if self.current_deal:
            logger.info(f"Found existing active deal {self.current_deal.client_deal_id} for {self.market_symbol}.")

        # Update strategy state to RUNNING after successful initialization
        StrategyConfig.update_state(self.strategy_config_id, StrategyState.RUNNING)

    def execute(self, latest_data: Dict[str, Any]):
        """
        Executes the strategy logic with real-time data.
        This method is called periodically with the latest market data.
        """
        if not self.strategy_config or not self.strategy_config.is_active or self.strategy_config.state == StrategyState.STOPPED.value:
            logger.debug(f"Strategy {self.strategy_config_id} is inactive or stopped. Skipping execution.")
            return "Strategy inactive or stopped"

        if self.strategy_config.state == StrategyState.NOT_ORDERING.value:
            logger.debug(f"Strategy {self.strategy_config_id} is in NOT_ORDERING state. Skipping deal generation.")
            return "Strategy not ordering"

        if not self.provider_instance:
            logger.error(f"Provider instance not initialized for {self.market_symbol}. Skipping execution.")
            return "Provider not initialized"

        # 1. Update historical data with latest candle if needed
        if self.strategy_config.need_historical_data:
            new_candle_time = pd.to_datetime(latest_data['time'], unit='s')
            new_candle_data = {k: latest_data[k] for k in ['open', 'high', 'low', 'close', 'volume']}
            new_candle_df = pd.DataFrame([new_candle_data], index=[new_candle_time])

            if not self.price_history.empty and new_candle_time in self.price_history.index:
                self.price_history.loc[new_candle_time] = new_candle_df.loc[new_candle_time]
            else:
                self.price_history = pd.concat([self.price_history, new_candle_df])

            max_period = max(self.long_ema_period, self.slow_ema_period + self.signal_ema_period)
            self.price_history = self.price_history.iloc[-(max_period + 5):]

            self._calculate_all_indicators()

            if len(self.price_history) < max_period:
                logger.warning(
                    f"Not enough historical data for {self.market_symbol} to calculate all indicators. Skipping signal generation.")
                return "Not enough historical data"

            latest_close_price = Decimal(str(self.price_history['close'].iloc[-1]))
            latest_macd = self.price_history['macd'].iloc[-1]
            latest_signal = self.price_history['signal'].iloc[-1]
            latest_short_ema = self.price_history['short_ema'].iloc[-1]
            latest_long_ema = self.price_history['long_ema'].iloc[-1]
            latest_volume = Decimal(str(self.price_history['volume'].iloc[-1]))

            prev_macd = self.price_history['macd'].iloc[-2]
            prev_signal = self.price_history['signal'].iloc[-2]
            prev_short_ema = self.price_history['short_ema'].iloc[-2]
            prev_long_ema = self.price_history['long_ema'].iloc[-2]
        else:
            # If not using historical data, rely on latest_data directly (e.g., for simple price action)
            latest_close_price = Decimal(str(latest_data['close']))
            latest_volume = Decimal(str(latest_data['volume']))
            # If historical data is not needed, MACD/EMA crosses won't be calculated.
            # The strategy logic would need to adapt to this. For now, assume these are required.
            logger.warning(
                f"Strategy {self.strategy_config_id} is configured not to use historical data. MACD/EMA signals will not be generated.")
            return "Historical data not enabled for indicators"

        # 2. Analyze Order Book Depth
        order_book_ratio = Decimal('1.0')
        order_book_data = latest_data.get('order_book')
        if order_book_data and 'bids' in order_book_data and 'asks' in order_book_data:
            buy_volume = sum(Decimal(str(order[1])) for order in order_book_data['bids'])
            sell_volume = sum(Decimal(str(order[1])) for order in order_book_data['asks'])

            if sell_volume > 0:
                order_book_ratio = buy_volume / sell_volume
            else:
                order_book_ratio = Decimal('1000000')

            logger.debug(f"Order Book Buy/Sell Ratio for {self.market_symbol}: {order_book_ratio:.2f}")

        # 3. Decision Logic (only if historical data is enabled for indicators)
        if self.strategy_config.need_historical_data:
            macd_cross_buy_signal = (latest_macd > latest_signal) and (prev_macd <= prev_signal)
            macd_cross_sell_signal = (latest_macd < latest_signal) and (prev_macd >= prev_signal)

            ema_cross_buy_signal = (latest_short_ema > latest_long_ema) and (prev_short_ema <= prev_long_ema)
            ema_cross_sell_signal = (latest_short_ema < latest_long_ema) and (prev_short_ema >= prev_long_ema)

            if len(self.price_history) >= self.fast_ema_period:
                avg_volume = self.price_history['volume'].iloc[-self.fast_ema_period:].mean()
                volume_confirmation = latest_volume > Decimal(str(avg_volume * Decimal('1.2')))
            else:
                volume_confirmation = False

            buy_pressure_confirmation = order_book_ratio > Decimal('1.0')
            sell_pressure_confirmation = order_book_ratio < self.order_book_depth_threshold

            # Generate BUY signal
            if (macd_cross_buy_signal or ema_cross_buy_signal) and volume_confirmation and buy_pressure_confirmation:
                if not self.current_deal or self.current_deal.side == ProcessedSideEnum.SELL.value:
                    logger.info(f"Strong BUY signal for {self.market_symbol} at {latest_close_price}.")
                    self._generate_deal(ProcessedSideEnum.BUY, latest_close_price)
                    return "Buy signal generated"

            # Generate SELL signal
            elif (
                    macd_cross_sell_signal or ema_cross_sell_signal) and volume_confirmation and sell_pressure_confirmation:
                if self.current_deal and self.current_deal.side == ProcessedSideEnum.BUY.value:
                    logger.info(f"Strong SELL signal for {self.market_symbol} at {latest_close_price}.")
                    self._generate_deal(ProcessedSideEnum.SELL, latest_close_price)
                    return "Sell signal generated"

        logger.debug(f"No strong signal for {self.market_symbol}.")
        return "No signal"

    def _fetch_historical_data(self, start_ts: int, end_ts: int, resolution: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches historical OHLCV data from the provider.
        """
        try:
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

        self.price_history['close_float'] = self.price_history['close'].astype(float)
        self.price_history['volume_float'] = self.price_history['volume'].astype(float)

        macd_output = ta.macd(
            self.price_history['close_float'],
            fast=self.fast_ema_period,
            slow=self.slow_ema_period,
            signal=self.signal_ema_period,
            append=True
        )

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

        self.price_history['short_ema'] = ta.ema(
            self.price_history['close_float'],
            length=self.short_ema_period,
            append=False
        ).apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))

        self.price_history['long_ema'] = ta.ema(
            self.price_history['close_float'],
            length=self.long_ema_period,
            append=False
        ).apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))

        self.price_history.drop(columns=['close_float', 'volume_float'], errors='ignore', inplace=True)

    def _generate_deal(self, side: ProcessedSideEnum, price: Decimal):
        """
        Creates a new Deal record in the database or updates an existing one.
        """
        if self.current_deal and self.current_deal.is_active and self.current_deal.side == side.value:
            logger.info(
                f"An active {side.value} deal already exists ({self.current_deal.client_deal_id}). Not creating a new one.")
            return

        system_configs = AdminSystemConfig.get_instance()
        trade_amount_quote_currency = Decimal(str(system_configs.wallex_tether_order_amount))

        try:
            market_instance = Market.objects.get(symbol=self.market_symbol, provider=self.provider_name.value)
        except Market.DoesNotExist:
            logger.error(
                f"Market {self.market_symbol} not found for provider {self.provider_name.value}. Cannot generate deal.")
            return

        if price > 0:
            calculated_quantity = trade_amount_quote_currency / price
        else:
            logger.error(f"Invalid price ({price}) for deal generation. Cannot calculate quantity.")
            return

        adjusted_quantity = Decimal(str(market_instance.adjust_quantity(float(calculated_quantity))))
        adjusted_price = Decimal(str(market_instance.adjust_price(float(price))))

        adjusted_quantity = Decimal(str(market_instance.adjust_min_qty(float(adjusted_quantity))))

        if adjusted_quantity <= 0:
            logger.error(f"Adjusted quantity is zero or negative ({adjusted_quantity}). Cannot create deal.")
            return

        self.current_deal = Deal.objects.create(
            strategy_name=self.__class__.__name__,
            provider_name=self.provider_name.value,
            market_symbol=self.market_symbol,
            side=side.value,
            quantity=adjusted_quantity,
            price=adjusted_price,
            is_active=True,
            is_processed=False,
            status=StrategyState.STARTED.value
        )
        logger.info(
            f"New deal {self.current_deal.client_deal_id} created for {self.market_symbol} with side {side.value} at {adjusted_price} for {adjusted_quantity}.")

    def get_results(self):
        """
        Returns the current active deal object if any.
        """
        return self.current_deal
