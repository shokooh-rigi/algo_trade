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

class BreakoutStrategy(StrategyInterface):
    """
    Implements a breakout trading strategy based on:
    - High/Low breakouts with volume confirmation
    - EMA cross signals for trend direction
    - RSI for momentum confirmation
    - ATR for volatility analysis
    - Risk management with stop-loss and take-profit
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
        self.last_trade_time = None  # For cooldown management
        self.state = StrategyState.INITIALIZING

    def initialize(self) -> bool:
        """
        Initializes the strategy by loading configuration and fetching initial historical data.
        Returns:
            bool: True if initialization successful, False otherwise.
        """
        try:
            # Load strategy configuration
            self.strategy_config = StrategyConfig.objects.get(id=self.strategy_config_id)
            logger.info(f"Loading configuration for StrategyConfig ID: {self.strategy_config_id}")
            
            # Validate configuration using Pydantic schema
            from algo.strategies.schemas import get_strategy_schema
            schema_class = get_strategy_schema(self.strategy_config.strategy)
            self.strategy_params = schema_class(**self.strategy_config.strategy_configs)
            
            logger.info(f"Strategy {self.strategy_config_id} initialized for {self.market_symbol} on {self.provider_name}")
            
            # Initialize provider
            self.provider_instance = ProviderFactory.create_provider(self.provider_name, {})
            
            # Fetch historical data for indicators
            if self.strategy_config.need_historical_data:
                success = self._fetch_historical_data()
                if not success:
                    logger.warning(f"Could not fetch historical data for {self.market_symbol}. Strategy will use simple signals.")
            else:
                logger.info(f"Strategy {self.strategy_config_id} doesn't require historical data. Using simple signals.")
            
            self.state = StrategyState.ACTIVE
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize strategy {self.strategy_config_id}: {e}", exc_info=True)
            self.state = StrategyState.ERROR
            return False

    def _fetch_historical_data(self) -> bool:
        """
        Fetches historical OHLCV data for indicator calculations.
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Ensure we have enough data for indicators (at least 250 days for EMA 200)
            min_days = max(self.strategy_config.initial_history_period_days, 250)
            htf_days = min_days
            
            end_timestamp = int(time.time())
            start_timestamp = end_timestamp - (htf_days * 24 * 60 * 60)
            
            logger.info(f"Fetching {htf_days} days of history for {self.market_symbol} with resolution D")
            
            # Use NobitexProvider for historical data
            from providers.nobitex_provider import NobitexProvider
            nobitex_provider = NobitexProvider({})
            
            ohlcv_data = nobitex_provider.fetch_ohlcv_data(
                symbol=self.market_symbol,
                resolution="D",  # Daily resolution
                from_timestamp=start_timestamp,
                to_timestamp=end_timestamp
            )
            
            if not ohlcv_data or len(ohlcv_data) < 50:
                logger.warning(f"Insufficient historical data for {self.market_symbol}: {len(ohlcv_data) if ohlcv_data else 0} candles")
                return False
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time')
            
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            if len(df) < 50:
                logger.warning(f"Not enough data points after cleaning: {len(df)} (need at least 50)")
                return False
            
            # Calculate breakout indicators
            self._calculate_breakout_indicators(df)
            
            # Keep only recent data (last 250 points for efficiency)
            self.price_history = df.tail(250).copy()
            
            logger.info(f"Successfully fetched {len(self.price_history)} historical candles from Nobitex for {self.market_symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {self.market_symbol}: {e}", exc_info=True)
            return False

    def _calculate_breakout_indicators(self, df: pd.DataFrame):
        """Calculate indicators for breakout trading."""
        try:
            # Fast EMAs for quick signals
            df['ema_5'] = ta.ema(df['close'], length=5)
            df['ema_13'] = ta.ema(df['close'], length=13)
            
            # RSI
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # Volume
            df['volume_sma'] = ta.sma(df['volume'], length=5)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price change
            df['price_change'] = df['close'].pct_change()
            
            # High/Low breakouts
            df['high_20'] = df['high'].rolling(window=20).max()
            df['low_20'] = df['low'].rolling(window=20).min()
            
            # Volatility
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # Momentum
            df['momentum'] = df['close'] - df['close'].shift(3)
            
            logger.info(f"Breakout indicators calculated successfully for {self.market_symbol}")
            
        except Exception as e:
            logger.error(f"Error calculating breakout indicators for {self.market_symbol}: {e}", exc_info=True)

    def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes the breakout strategy based on current market data.
        Args:
            market_data (Dict[str, Any]): Current market data including OHLCV and order book.
        Returns:
            Optional[Dict[str, Any]]: Deal information if a trade is executed, None otherwise.
        """
        try:
            if self.state != StrategyState.ACTIVE:
                logger.warning(f"Strategy {self.strategy_config_id} is not active. Current state: {self.state}")
                return None
            
            # Check if we have an active deal
            if self.current_deal:
                return self._check_exit_conditions(market_data)
            
            # Check cooldown period
            if self._is_in_cooldown():
                return None
            
            # Generate breakout signals
            signal = self._generate_breakout_signal(market_data)
            
            if signal:
                return self._execute_trade(signal, market_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing strategy {self.strategy_config_id}: {e}", exc_info=True)
            return None

    def _generate_breakout_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate breakout trading signals based on current market data.
        Args:
            market_data (Dict[str, Any]): Current market data.
        Returns:
            Optional[Dict[str, Any]]: Signal information if a signal is generated, None otherwise.
        """
        try:
            if not self.strategy_config.need_historical_data or len(self.price_history) < 20:
                return self._generate_simple_signal(market_data)
            
            # Get current price
            current_price = market_data.get('mid_price', 0)
            if not current_price:
                return None
            
            # Get latest data from price history
            latest_data = self.price_history.iloc[-1]
            previous_data = self.price_history.iloc[-2] if len(self.price_history) > 1 else latest_data
            
            # BUY signal: Price breaks above high + EMA cross + RSI not overbought
            if (current_price > latest_data['high_20'] and 
                latest_data['ema_5'] > latest_data['ema_13'] and 
                latest_data['rsi'] < 75 and 
                latest_data['volume_ratio'] > 1.2):
                
                return {
                    'side': ProcessedSideEnum.BUY,
                    'reason': 'High breakout + EMA cross',
                    'confidence': 0.8
                }
            
            # SELL signal: Price breaks below low + EMA cross + RSI not oversold
            elif (current_price < latest_data['low_20'] and 
                  latest_data['ema_5'] < latest_data['ema_13'] and 
                  latest_data['rsi'] > 25 and 
                  latest_data['volume_ratio'] > 1.2):
                
                return {
                    'side': ProcessedSideEnum.SELL,
                    'reason': 'Low breakout + EMA cross',
                    'confidence': 0.8
                }
            
            # Additional momentum signals
            # BUY signal: Strong momentum + EMA cross up
            elif (latest_data['momentum'] > 0 and 
                  latest_data['ema_5'] > latest_data['ema_13'] and 
                  previous_data['ema_5'] <= previous_data['ema_13'] and
                  latest_data['rsi'] < 70):
                
                return {
                    'side': ProcessedSideEnum.BUY,
                    'reason': 'Momentum + EMA cross up',
                    'confidence': 0.7
                }
            
            # SELL signal: Strong negative momentum + EMA cross down
            elif (latest_data['momentum'] < 0 and 
                  latest_data['ema_5'] < latest_data['ema_13'] and 
                  previous_data['ema_5'] >= previous_data['ema_13'] and
                  latest_data['rsi'] > 30):
                
                return {
                    'side': ProcessedSideEnum.SELL,
                    'reason': 'Momentum + EMA cross down',
                    'confidence': 0.7
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating breakout signal for {self.market_symbol}: {e}", exc_info=True)
            return None

    def _generate_simple_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate simple signals when historical data is not available.
        Args:
            market_data (Dict[str, Any]): Current market data.
        Returns:
            Optional[Dict[str, Any]]: Signal information if a signal is generated, None otherwise.
        """
        try:
            # Simple order book imbalance signal
            order_book = market_data.get('order_book', {})
            if not order_book:
                return None
            
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return None
            
            # Calculate order book imbalance
            bid_volume = sum(float(bid[1]) for bid in bids[:5])  # Top 5 bids
            ask_volume = sum(float(ask[1]) for ask in asks[:5])  # Top 5 asks
            
            if bid_volume > ask_volume * 1.5:  # Strong buy pressure
                return {
                    'side': ProcessedSideEnum.BUY,
                    'reason': 'Order book imbalance (buy pressure)',
                    'confidence': 0.6
                }
            elif ask_volume > bid_volume * 1.5:  # Strong sell pressure
                return {
                    'side': ProcessedSideEnum.SELL,
                    'reason': 'Order book imbalance (sell pressure)',
                    'confidence': 0.6
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating simple signal for {self.market_symbol}: {e}", exc_info=True)
            return None

    def _execute_trade(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a trade based on the generated signal.
        Args:
            signal (Dict[str, Any]): Trading signal.
            market_data (Dict[str, Any]): Current market data.
        Returns:
            Optional[Dict[str, Any]]: Deal information if trade is executed.
        """
        try:
            side = signal['side']
            reason = signal['reason']
            confidence = signal.get('confidence', 0.5)
            
            # Get current price
            current_price = market_data.get('mid_price', 0)
            if not current_price:
                return None
            
            # Calculate position size based on confidence and risk management
            position_size_percent = min(confidence * 50, 50)  # Max 50% position size
            
            # Create deal
            deal_data = {
                'side': side.value,
                'price': current_price,
                'quantity': position_size_percent / 100,  # As percentage of balance
                'reason': reason,
                'confidence': confidence
            }
            
            # Update last trade time for cooldown
            self.last_trade_time = datetime.now()
            
            logger.info(f"Breakout trade executed: {side.value} {self.market_symbol} at {current_price} - {reason}")
            
            return deal_data
            
        except Exception as e:
            logger.error(f"Error executing trade for {self.market_symbol}: {e}", exc_info=True)
            return None

    def _check_exit_conditions(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if current position should be exited based on stop-loss or take-profit.
        Args:
            market_data (Dict[str, Any]): Current market data.
        Returns:
            Optional[Dict[str, Any]]: Exit deal information if position should be closed.
        """
        try:
            if not self.current_deal:
                return None
            
            current_price = market_data.get('mid_price', 0)
            if not current_price:
                return None
            
            # Get strategy parameters
            stop_loss_percent = getattr(self.strategy_params, 'stop_loss_percent', 0.3)
            take_profit_percent = getattr(self.strategy_params, 'take_profit_percent', 0.6)
            
            entry_price = self.current_deal.price
            side = self.current_deal.side
            
            if side == ProcessedSideEnum.BUY.value:
                stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                take_profit_price = entry_price * (1 + take_profit_percent / 100)
                
                if current_price <= stop_loss_price:
                    return {
                        'side': ProcessedSideEnum.SELL.value,
                        'price': current_price,
                        'reason': 'Stop-loss',
                        'exit_deal': True
                    }
                elif current_price >= take_profit_price:
                    return {
                        'side': ProcessedSideEnum.SELL.value,
                        'price': current_price,
                        'reason': 'Take-profit',
                        'exit_deal': True
                    }
            
            elif side == ProcessedSideEnum.SELL.value:
                stop_loss_price = entry_price * (1 + stop_loss_percent / 100)
                take_profit_price = entry_price * (1 - take_profit_percent / 100)
                
                if current_price >= stop_loss_price:
                    return {
                        'side': ProcessedSideEnum.BUY.value,
                        'price': current_price,
                        'reason': 'Stop-loss',
                        'exit_deal': True
                    }
                elif current_price <= take_profit_price:
                    return {
                        'side': ProcessedSideEnum.BUY.value,
                        'price': current_price,
                        'reason': 'Take-profit',
                        'exit_deal': True
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking exit conditions for {self.market_symbol}: {e}", exc_info=True)
            return None

    def _is_in_cooldown(self) -> bool:
        """
        Check if strategy is in cooldown period between trades.
        Returns:
            bool: True if in cooldown, False otherwise.
        """
        if not self.last_trade_time:
            return False
        
        cooldown_minutes = getattr(self.strategy_params, 'trade_cooldown_minutes', 30)
        time_since_last_trade = datetime.now() - self.last_trade_time
        
        return time_since_last_trade.total_seconds() < (cooldown_minutes * 60)

    def get_state(self) -> StrategyState:
        """Returns the current state of the strategy."""
        return self.state

    def get_config(self) -> Optional[StrategyConfig]:
        """Returns the strategy configuration."""
        return self.strategy_config

    def update_price_history(self, new_candle: Dict[str, Any]):
        """
        Update price history with new candle data.
        Args:
            new_candle (Dict[str, Any]): New OHLCV candle data.
        """
        try:
            if not self.strategy_config.need_historical_data:
                return
            
            # Convert new candle to DataFrame row
            new_row = pd.DataFrame([{
                'time': pd.to_datetime(new_candle['time'], unit='s'),
                'open': float(new_candle['open']),
                'high': float(new_candle['high']),
                'low': float(new_candle['low']),
                'close': float(new_candle['close']),
                'volume': float(new_candle['volume'])
            }])
            new_row = new_row.set_index('time')
            
            # Append to price history
            self.price_history = pd.concat([self.price_history, new_row])
            
            # Keep only recent data (last 250 points)
            self.price_history = self.price_history.tail(250)
            
            # Recalculate indicators for the updated data
            self._calculate_breakout_indicators(self.price_history)
            
        except Exception as e:
            logger.error(f"Error updating price history for {self.market_symbol}: {e}", exc_info=True)
