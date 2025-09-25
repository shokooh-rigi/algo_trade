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

    Upgrades:
    - Higher timeframe confirmation using EMA trend (default 4h)
    - ADX trend-strength filter and ATR volatility floor to avoid chop
    - Volume percentile confirmation (stronger than simple average)
    - Cooldown period between opposite trades to reduce churn
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
        self.htf_history: pd.DataFrame = pd.DataFrame()  # Higher timeframe history
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

        # New parameters (can be promoted to DB config later)
        self.htf_resolution = '4h'
        self.htf_ema_length = 50
        self.min_adx = Decimal('18')  # skip if trend is weak
        self.min_atr_percent = Decimal('0.15')  # ATR as % of price
        self.volume_percentile_window = 50
        self.volume_percentile_threshold = 70  # latest volume must be above this percentile
        self.trade_cooldown_minutes = 45
        self._last_trade_ts: Optional[int] = None

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
                    f"Could not fetch initial historical data for {self.market_symbol}. Strategy will run without historical data.")

            # Higher timeframe history for trend confirmation
            htf_days = max(14, self.initial_history_period_days)
            htf_start_ts = int((datetime.now() - timedelta(days=htf_days)).timestamp())
            htf_raw = self._fetch_historical_data(htf_start_ts, end_timestamp, resolution=self.htf_resolution)
            if htf_raw:
                self.htf_history = pd.DataFrame(htf_raw)
                self.htf_history['time'] = pd.to_datetime(self.htf_history['time'], unit='s')
                self.htf_history = self.htf_history.set_index('time')
                self._calculate_htf_indicators()
        else:
            logger.info(f"Historical data not required for {self.market_symbol}. Strategy will start without initial indicators.")

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
            self._last_trade_ts = int(self.current_deal.created_at.timestamp())

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

        # Check if we have historical data capability
        if not self.strategy_config.need_historical_data:
            logger.info(f"Strategy {self.strategy_config_id} running without historical data. Using real-time data only.")
            return self._execute_simple_strategy(latest_data)

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
            logger.warning(
                f"Strategy {self.strategy_config_id} is configured not to use historical data. MACD/EMA signals will not be generated.")
            return "Historical data not enabled for indicators"

        # 1.1 Update HTF periodically from provider (lightweight: only every N minutes)
        if self.htf_history.empty or (self.htf_history.index.max() < new_candle_time - pd.Timedelta(self.htf_resolution)):
            try:
                now_ts = int(time.time())
                htf_raw = self.provider_instance.fetch_ohlcv_data(
                    symbol=self.market_symbol,
                    resolution=self.htf_resolution,
                    from_timestamp=now_ts - (14 * 24 * 3600),
                    to_timestamp=now_ts
                )
                if htf_raw:
                    self.htf_history = pd.DataFrame(htf_raw)
                    self.htf_history['time'] = pd.to_datetime(self.htf_history['time'], unit='s')
                    self.htf_history = self.htf_history.set_index('time')
                    self._calculate_htf_indicators()
            except Exception as e:
                logger.warning(f"Failed to refresh HTF data: {e}")

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

            volume_confirmation = self._volume_percentile_confirmation()

            buy_pressure_confirmation = order_book_ratio > Decimal('1.0')
            sell_pressure_confirmation = order_book_ratio < self.order_book_depth_threshold

            # Higher timeframe trend filter
            htf_trend_up, htf_trend_down = self._htf_trend()

            # ADX and ATR filters to avoid chop/low volatility
            adx_ok = self._adx_filter_ok()
            atr_ok = self._atr_filter_ok()

            cooldown_ok = self._cooldown_ok()

            # Generate BUY signal
            if cooldown_ok and (macd_cross_buy_signal or ema_cross_buy_signal) and volume_confirmation and buy_pressure_confirmation and htf_trend_up and adx_ok and atr_ok:
                if not self.current_deal or self.current_deal.side == ProcessedSideEnum.SELL.value:
                    logger.info(f"Strong BUY signal for {self.market_symbol} at {latest_close_price}.")
                    self._generate_deal(ProcessedSideEnum.BUY, latest_close_price)
                    self._last_trade_ts = int(time.time())
                    return "Buy signal generated"

            # Generate SELL signal
            elif cooldown_ok and (macd_cross_sell_signal or ema_cross_sell_signal) and volume_confirmation and sell_pressure_confirmation and htf_trend_down and adx_ok and atr_ok:
                if self.current_deal and self.current_deal.side == ProcessedSideEnum.BUY.value:
                    logger.info(f"Strong SELL signal for {self.market_symbol} at {latest_close_price}.")
                    self._generate_deal(ProcessedSideEnum.SELL, latest_close_price)
                    self._last_trade_ts = int(time.time())
                    return "Sell signal generated"

        logger.debug(f"No strong signal for {self.market_symbol}.")
        return "No signal"

    def _execute_simple_strategy(self, latest_data: Dict[str, Any]) -> str:
        """
        Execute a simplified strategy using only real-time data from order book.
        This is used when historical data is not available.
        """
        try:
            # Extract order book data
            order_book = latest_data.get('order_book', {})
            current_price = latest_data.get('close', Decimal('0'))
            
            if current_price <= 0:
                logger.warning(f"Invalid price data for {self.market_symbol}: {current_price}")
                return "Invalid price data"
            
            # Extract bid/ask data
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                logger.warning(f"No order book data available for {self.market_symbol}")
                return "No order book data"
            
            best_bid = Decimal(str(bids[0][0]))
            best_ask = Decimal(str(asks[0][0]))
            bid_volume = Decimal(str(bids[0][1])) if len(bids[0]) > 1 else Decimal('0')
            ask_volume = Decimal(str(asks[0][1])) if len(asks[0]) > 1 else Decimal('0')
            
            # Calculate order book imbalance
            total_bid_volume = sum(Decimal(str(bid[1])) for bid in bids[:5])  # Top 5 bids
            total_ask_volume = sum(Decimal(str(ask[1])) for ask in asks[:5])  # Top 5 asks
            
            if total_bid_volume + total_ask_volume > 0:
                bid_ratio = total_bid_volume / (total_bid_volume + total_ask_volume)
            else:
                bid_ratio = Decimal('0.5')
            
            logger.info(f"Order book analysis for {self.market_symbol}: "
                       f"Price: {current_price}, Bid ratio: {bid_ratio:.3f}, "
                       f"Threshold: {self.order_book_depth_threshold}")
            
            # Simple trading logic based on order book imbalance
            if bid_ratio >= self.order_book_depth_threshold:
                # Strong buying pressure
                if not self.current_deal or self.current_deal.side == ProcessedSideEnum.SELL.value:
                    if self._cooldown_ok():
                        logger.info(f"BUY signal for {self.market_symbol} based on order book imbalance: {bid_ratio:.3f}")
                        self._generate_deal(ProcessedSideEnum.BUY, current_price)
                        self._last_trade_ts = int(time.time())
                        return "Buy signal generated (order book)"
            
            elif bid_ratio <= (1 - self.order_book_depth_threshold):
                # Strong selling pressure
                if self.current_deal and self.current_deal.side == ProcessedSideEnum.BUY.value:
                    if self._cooldown_ok():
                        logger.info(f"SELL signal for {self.market_symbol} based on order book imbalance: {bid_ratio:.3f}")
                        self._generate_deal(ProcessedSideEnum.SELL, current_price)
                        self._last_trade_ts = int(time.time())
                        return "Sell signal generated (order book)"
            
            logger.debug(f"No signal for {self.market_symbol}. Bid ratio: {bid_ratio:.3f}")
            return "No signal (order book analysis)"
            
        except Exception as e:
            logger.error(f"Error in simple strategy execution for {self.market_symbol}: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def _fetch_historical_data(self, start_ts: int, end_ts: int, resolution: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches historical OHLCV data from Nobitex (for indicators) while trading on Wallex.
        This hybrid approach allows us to use technical indicators while trading on the preferred exchange.
        """
        try:
            # Use Nobitex for historical data (better for indicators)
            from providers.nobitex_provider import NobitexProvider
            
            nobitex_provider = NobitexProvider({})
            ohlcv_data = nobitex_provider.fetch_ohlcv_data(
                symbol=self.market_symbol,
                resolution=resolution,
                from_timestamp=start_ts,
                to_timestamp=end_ts
            )
            
            if ohlcv_data:
                logger.info(f"Successfully fetched {len(ohlcv_data)} historical candles from Nobitex for {self.market_symbol}")
                return ohlcv_data
            else:
                logger.warning(f"No historical data available from Nobitex for {self.market_symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data from Nobitex for {self.market_symbol}: {e}", exc_info=True)
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
        self.price_history['high_float'] = self.price_history['high'].astype(float)
        self.price_history['low_float'] = self.price_history['low'].astype(float)

        # Calculate MACD with proper error handling
        macd_df = ta.macd(
            self.price_history['close_float'],
            fast=self.fast_ema_period,
            slow=self.slow_ema_period,
            signal=self.signal_ema_period,
            append=False
        )

        if macd_df is not None and isinstance(macd_df, pd.DataFrame):
            # Check for MACD columns in the returned DataFrame
            macd_col = None
            signal_col = None
            
            # Look for MACD column (usually named MACD_12_26_9 or similar)
            for col in macd_df.columns:
                if 'MACD_' in col and 'MACDs_' not in col:
                    macd_col = col
                elif 'MACDs_' in col:
                    signal_col = col
            
            if macd_col and signal_col:
                self.price_history['macd'] = macd_df[macd_col].apply(
                    lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
                self.price_history['signal'] = macd_df[signal_col].apply(
                    lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
                logger.info(f"MACD calculated successfully for {self.market_symbol}")
            else:
                logger.warning(f"MACD columns not found in DataFrame for {self.market_symbol}. Available columns: {list(macd_df.columns)}")
                self.price_history['macd'] = Decimal('0')
                self.price_history['signal'] = Decimal('0')
        else:
            logger.warning(f"MACD calculation failed for {self.market_symbol}. pandas_ta returned: {type(macd_df)}")
            self.price_history['macd'] = Decimal('0')
            self.price_history['signal'] = Decimal('0')

        # Calculate EMAs with proper error handling
        short_ema = ta.ema(self.price_history['close_float'], length=self.short_ema_period, append=False)
        if short_ema is not None:
            self.price_history['short_ema'] = short_ema.apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
        else:
            self.price_history['short_ema'] = Decimal('0')

        long_ema = ta.ema(self.price_history['close_float'], length=self.long_ema_period, append=False)
        if long_ema is not None:
            self.price_history['long_ema'] = long_ema.apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
        else:
            self.price_history['long_ema'] = Decimal('0')

        # ADX and ATR for chop/volatility filters
        adx_df = ta.adx(high=self.price_history['high_float'], low=self.price_history['low_float'], close=self.price_history['close_float'])
        if isinstance(adx_df, pd.DataFrame) and 'ADX_14' in adx_df.columns:
            self.price_history['adx'] = adx_df['ADX_14'].apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
        else:
            self.price_history['adx'] = Decimal('0')

        atr_series = ta.atr(high=self.price_history['high_float'], low=self.price_history['low_float'], close=self.price_history['close_float'])
        if atr_series is not None and len(atr_series) > 0:
            self.price_history['atr'] = atr_series.apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
        else:
            self.price_history['atr'] = Decimal('0')

        self.price_history.drop(columns=['close_float', 'volume_float', 'high_float', 'low_float'], errors='ignore', inplace=True)

    def _calculate_htf_indicators(self) -> None:
        if self.htf_history.empty:
            return
        self.htf_history['close_float'] = self.htf_history['close'].astype(float)
        self.htf_history['ema_htf'] = ta.ema(self.htf_history['close_float'], length=self.htf_ema_length)
        self.htf_history.drop(columns=['close_float'], errors='ignore', inplace=True)

    def _htf_trend(self) -> (bool, bool):
        if self.htf_history.empty or 'ema_htf' not in self.htf_history.columns:
            return True, True  # do not block signals if HTF not available
        last_close = Decimal(str(self.htf_history['close'].iloc[-1]))
        last_ema = Decimal(str(self.htf_history['ema_htf'].iloc[-1])) if pd.notna(self.htf_history['ema_htf'].iloc[-1]) else Decimal('0')
        return last_close > last_ema, last_close < last_ema

    def _adx_filter_ok(self) -> bool:
        if 'adx' not in self.price_history.columns:
            return True
        last_adx = self.price_history['adx'].iloc[-1]
        try:
            return Decimal(str(last_adx)) >= self.min_adx
        except Exception:
            return True

    def _atr_filter_ok(self) -> bool:
        if 'atr' not in self.price_history.columns or self.price_history['atr'].iloc[-1] <= 0:
            return True
        last_atr = Decimal(str(self.price_history['atr'].iloc[-1]))
        last_close = Decimal(str(self.price_history['close'].iloc[-1]))
        if last_close <= 0:
            return False
        atr_percent = (last_atr / last_close) * Decimal('100')
        return atr_percent >= self.min_atr_percent

    def _volume_percentile_confirmation(self) -> bool:
        try:
            vol_window = self.price_history['volume'].iloc[-self.volume_percentile_window:]
            latest_vol = Decimal(str(vol_window.iloc[-1]))
            rank = (vol_window.rank(pct=True).iloc[-1]) * 100
            return Decimal(str(rank)) >= Decimal(str(self.volume_percentile_threshold)) and latest_vol > 0
        except Exception:
            return False

    def _cooldown_ok(self) -> bool:
        if not self._last_trade_ts:
            return True
        elapsed = int(time.time()) - self._last_trade_ts
        return elapsed >= self.trade_cooldown_minutes * 60

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
