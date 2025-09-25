"""
Backtesting service for evaluating strategy performance using historical data.
"""

import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from algo.strategies.sterategy_macd_ema_cross import StrategyMacdEmaCross
from algo.strategies.schemas import StrategyMacdEmaCrossSchema
from providers.nobitex_provider import NobitexProvider
from algo.strategies.enums import ProcessedSideEnum

logger = logging.getLogger(__name__)


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self):
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = Decimal('0')
        self.total_loss = Decimal('0')
        self.max_profit = Decimal('0')
        self.max_loss = Decimal('0')
        self.trades = []
        self.signals = []
        self.start_balance = Decimal('10000')  # Starting with $10,000
        self.current_balance = Decimal('10000')
        self.position_size = Decimal('0.1')  # 10% of balance per trade
        
    def add_trade(self, side: ProcessedSideEnum, price: Decimal, timestamp: int, reason: str):
        """Add a trade to the results."""
        trade = {
            'side': side.value,
            'price': float(price),
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'reason': reason,
            'balance_before': float(self.current_balance)
        }
        
        # Calculate trade value
        trade_value = self.current_balance * self.position_size
        
        if side == ProcessedSideEnum.BUY:
            # Simulate buying (reduce balance, increase position)
            self.current_balance -= trade_value
            trade['trade_value'] = float(trade_value)
            trade['balance_after'] = float(self.current_balance)
        else:  # SELL
            # Simulate selling (increase balance, close position)
            self.current_balance += trade_value
            trade['trade_value'] = float(trade_value)
            trade['balance_after'] = float(self.current_balance)
            
            # Calculate profit/loss from the trade
            if len(self.trades) > 0 and self.trades[-1]['side'] == ProcessedSideEnum.BUY.value:
                buy_price = Decimal(str(self.trades[-1]['price']))
                sell_price = price
                profit_loss = (sell_price - buy_price) / buy_price * trade_value
                
                trade['profit_loss'] = float(profit_loss)
                self.total_profit += profit_loss if profit_loss > 0 else Decimal('0')
                self.total_loss += abs(profit_loss) if profit_loss < 0 else Decimal('0')
                
                if profit_loss > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                    
                self.max_profit = max(self.max_profit, profit_loss)
                self.max_loss = min(self.max_loss, profit_loss)
        
        self.trades.append(trade)
        self.total_trades += 1
        
    def add_signal(self, signal_type: str, price: Decimal, timestamp: int, reason: str):
        """Add a signal to the results."""
        signal = {
            'type': signal_type,
            'price': float(price),
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'reason': reason
        }
        self.signals.append(signal)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the backtest results."""
        total_return = (self.current_balance - self.start_balance) / self.start_balance * 100
        win_rate = (self.winning_trades / max(1, self.winning_trades + self.losing_trades)) * 100
        
        return {
            'start_balance': float(self.start_balance),
            'end_balance': float(self.current_balance),
            'total_return_percent': float(total_return),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_percent': win_rate,
            'total_profit': float(self.total_profit),
            'total_loss': float(self.total_loss),
            'max_profit': float(self.max_profit),
            'max_loss': float(self.max_loss),
            'net_profit': float(self.total_profit - self.total_loss),
            'signals_generated': len(self.signals)
        }


class BacktestService:
    """Service for backtesting trading strategies."""
    
    def __init__(self):
        self.nobitex_provider = NobitexProvider({})
    
    def backtest_strategy(
        self,
        symbol: str,
        strategy_config: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        resolution: str = "D"
    ) -> BacktestResult:
        """
        Backtest a strategy for a given symbol and time period.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            strategy_config: Strategy configuration parameters
            start_date: Start date for backtesting
            end_date: End date for backtesting
            resolution: Data resolution ('D' for daily, '4h' for 4-hour, etc.)
            
        Returns:
            BacktestResult object with detailed results
        """
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        # Fetch historical data
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        raw_data = self.nobitex_provider.fetch_ohlcv_data(
            symbol=symbol,
            resolution=resolution,
            from_timestamp=start_ts,
            to_timestamp=end_ts
        )
        
        if not raw_data:
            logger.error(f"No historical data available for {symbol}")
            return BacktestResult()
        
        logger.info(f"Fetched {len(raw_data)} candles for {symbol}")
        
        # Create strategy instance
        strategy = StrategyMacdEmaCross(
            strategy_config_id=1,
            provider_name="NOBITEX",
            market_symbol=symbol
        )
        
        # Set strategy configuration
        strategy.strategy_configs = strategy_config
        strategy._load_strategy_parameters()
        
        # Initialize strategy with historical data
        strategy.price_history = pd.DataFrame(raw_data)
        strategy.price_history['time'] = pd.to_datetime(strategy.price_history['time'], unit='s')
        strategy.price_history = strategy.price_history.set_index('time')
        
        # Ensure we have enough data for indicators
        max_period = max(strategy.long_ema_period, strategy.slow_ema_period + strategy.signal_ema_period)
        keep_data_points = max(max_period + 50, 250)
        if len(strategy.price_history) > keep_data_points:
            strategy.price_history = strategy.price_history.iloc[-keep_data_points:]
        
        # Calculate initial indicators
        strategy._calculate_all_indicators()
        
        # Initialize backtest result
        result = BacktestResult()
        
        # Run backtest simulation
        for i in range(max_period, len(strategy.price_history)):
            current_data = strategy.price_history.iloc[i]
            current_price = Decimal(str(current_data['close']))
            current_timestamp = int(current_data.name.timestamp())
            
            # Get current indicators
            current_macd = strategy.price_history['macd'].iloc[i]
            current_signal = strategy.price_history['signal'].iloc[i]
            current_short_ema = strategy.price_history['short_ema'].iloc[i]
            current_long_ema = strategy.price_history['long_ema'].iloc[i]
            
            # Check for MACD crossover signals
            prev_macd = strategy.price_history['macd'].iloc[i-1]
            prev_signal = strategy.price_history['signal'].iloc[i-1]
            
            macd_cross_buy = prev_macd <= prev_signal and current_macd > current_signal
            macd_cross_sell = prev_macd >= prev_signal and current_macd < current_signal
            
            # Check for EMA crossover signals
            prev_short_ema = strategy.price_history['short_ema'].iloc[i-1]
            prev_long_ema = strategy.price_history['long_ema'].iloc[i-1]
            
            ema_cross_buy = prev_short_ema <= prev_long_ema and current_short_ema > current_long_ema
            ema_cross_sell = prev_short_ema >= prev_long_ema and current_short_ema < current_long_ema
            
            # Generate signals
            if macd_cross_buy or ema_cross_buy:
                result.add_signal("BUY", current_price, current_timestamp, 
                                f"MACD cross: {macd_cross_buy}, EMA cross: {ema_cross_buy}")
                result.add_trade(ProcessedSideEnum.BUY, current_price, current_timestamp, "Buy signal")
                
            elif macd_cross_sell or ema_cross_sell:
                result.add_signal("SELL", current_price, current_timestamp,
                                f"MACD cross: {macd_cross_sell}, EMA cross: {ema_cross_sell}")
                result.add_trade(ProcessedSideEnum.SELL, current_price, current_timestamp, "Sell signal")
        
        logger.info(f"Backtest completed for {symbol}. Total trades: {result.total_trades}")
        return result
    
    def backtest_multiple_periods(
        self,
        symbol: str,
        strategy_config: Dict[str, Any],
        resolution: str = "D"
    ) -> Dict[str, BacktestResult]:
        """
        Backtest strategy for multiple time periods.
        
        Args:
            symbol: Trading symbol
            strategy_config: Strategy configuration
            resolution: Data resolution
            
        Returns:
            Dictionary with results for different periods
        """
        now = datetime.now()
        
        periods = {
            'last_week': (now - timedelta(days=7), now),
            'last_month': (now - timedelta(days=30), now),
            'last_3_months': (now - timedelta(days=90), now),
            'last_6_months': (now - timedelta(days=180), now),
            'last_year': (now - timedelta(days=365), now)
        }
        
        results = {}
        
        for period_name, (start_date, end_date) in periods.items():
            logger.info(f"Backtesting {symbol} for {period_name}")
            try:
                result = self.backtest_strategy(
                    symbol=symbol,
                    strategy_config=strategy_config,
                    start_date=start_date,
                    end_date=end_date,
                    resolution=resolution
                )
                results[period_name] = result
            except Exception as e:
                logger.error(f"Error backtesting {symbol} for {period_name}: {e}")
                results[period_name] = BacktestResult()
        
        return results
    
    def generate_report(self, results: Dict[str, BacktestResult], symbol: str) -> str:
        """Generate a comprehensive backtest report."""
        report = f"""
# BACKTEST REPORT FOR {symbol.upper()}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## STRATEGY CONFIGURATION
- Strategy: MACD EMA Cross Strategy
- Resolution: Daily
- Starting Balance: $10,000
- Position Size: 10% per trade

## PERFORMANCE SUMMARY
"""
        
        for period_name, result in results.items():
            summary = result.get_summary()
            report += f"""
### {period_name.upper().replace('_', ' ')}
- **Total Return**: {summary['total_return_percent']:.2f}%
- **End Balance**: ${summary['end_balance']:,.2f}
- **Total Trades**: {summary['total_trades']}
- **Win Rate**: {summary['win_rate_percent']:.1f}%
- **Winning Trades**: {summary['winning_trades']}
- **Losing Trades**: {summary['losing_trades']}
- **Total Profit**: ${summary['total_profit']:,.2f}
- **Total Loss**: ${summary['total_loss']:,.2f}
- **Net Profit**: ${summary['net_profit']:,.2f}
- **Max Profit**: ${summary['max_profit']:,.2f}
- **Max Loss**: ${summary['max_loss']:,.2f}
- **Signals Generated**: {summary['signals_generated']}

"""
        
        return report
