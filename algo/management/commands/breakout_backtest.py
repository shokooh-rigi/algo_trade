from django.core.management.base import BaseCommand
from decimal import Decimal
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import logging

from providers.nobitex_provider import NobitexProvider
from algo.strategies.enums import ProcessedSideEnum

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs a breakout backtest targeting 1% daily moves with aggressive parameters.'

    def add_arguments(self, parser):
        parser.add_argument('symbol', type=str, help='Market symbol (e.g., BTCUSDT)')
        parser.add_argument('--days', type=int, default=90, help='Number of days to backtest')
        parser.add_argument('--initial_balance', type=float, default=10000.0, help='Starting balance for backtest')
        parser.add_argument('--position_size_percent', type=float, default=50.0, help='Percentage of balance to use per trade')
        parser.add_argument('--stop_loss', type=float, default=0.3, help='Stop loss percentage')
        parser.add_argument('--take_profit', type=float, default=0.6, help='Take profit percentage')
        parser.add_argument('--max_daily_trades', type=int, default=10, help='Maximum trades per day')

    def handle(self, *args, **options):
        symbol = options['symbol']
        days = options['days']
        initial_balance = float(options['initial_balance'])
        position_size_percent = float(options['position_size_percent'])
        stop_loss_percent = float(options['stop_loss'])
        take_profit_percent = float(options['take_profit'])
        max_daily_trades = options['max_daily_trades']

        self.stdout.write(
            self.style.SUCCESS(f'Starting Breakout Backtest for {symbol}')
        )
        self.stdout.write(f'Period: {days} days')
        self.stdout.write(f'Initial Balance: ${initial_balance:,.2f}')
        self.stdout.write(f'Position Size: {position_size_percent}%')
        self.stdout.write(f'Stop Loss: {stop_loss_percent}%')
        self.stdout.write(f'Take Profit: {take_profit_percent}%')
        self.stdout.write(f'Max Daily Trades: {max_daily_trades}')
        self.stdout.write('-' * 60)

        # Fetch historical data
        provider = NobitexProvider({})
        end_timestamp = int(datetime.now().timestamp())
        start_timestamp = end_timestamp - (days * 24 * 60 * 60)

        try:
            # Use 4-hour resolution
            ohlcv_data = provider.fetch_ohlcv_data(
                symbol=symbol,
                resolution="240",  # 4 hours
                from_timestamp=start_timestamp,
                to_timestamp=end_timestamp
            )

            if not ohlcv_data or len(ohlcv_data) < 50:
                self.stdout.write(
                    self.style.ERROR(f'Insufficient data for {symbol}: {len(ohlcv_data) if ohlcv_data else 0} candles')
                )
                return

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('time')
            
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            if len(df) < 50:
                self.stdout.write(
                    self.style.ERROR(f'Not enough data points: {len(df)} (need at least 50)')
                )
                return

            self.stdout.write(f'Loaded {len(df)} candles for {symbol}')
            
            # Calculate breakout indicators
            self._calculate_breakout_indicators(df)
            
            # Run backtest
            results = self._run_breakout_backtest(df, initial_balance, position_size_percent, stop_loss_percent, take_profit_percent, max_daily_trades)
            
            # Display results
            self._display_results(results, symbol, days)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during backtest: {e}')
            )
            logger.error(f'Breakout backtest error for {symbol}: {e}', exc_info=True)

    def _calculate_breakout_indicators(self, df):
        """Calculate indicators for breakout trading."""
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

    def _run_breakout_backtest(self, df, initial_balance, position_size_percent, stop_loss_percent, take_profit_percent, max_daily_trades):
        """Run the breakout backtest."""
        balance = initial_balance
        position = None
        trades = []
        equity_curve = []
        daily_trades = {}
        daily_pnl = {}
        
        for i in range(20, len(df)):  # Start after 20 periods for indicators
            current = df.iloc[i]
            previous = df.iloc[i-1]
            current_date = current.name.date()
            
            # Initialize daily counters
            if current_date not in daily_trades:
                daily_trades[current_date] = 0
                daily_pnl[current_date] = 0
            
            # Check daily trade limit
            if daily_trades[current_date] >= max_daily_trades:
                continue
            
            # Check stop-loss and take-profit
            if position:
                entry_price = position['price']
                side = position['side']
                
                if side == ProcessedSideEnum.BUY.value:
                    stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                    take_profit_price = entry_price * (1 + take_profit_percent / 100)
                    
                    if current['close'] <= stop_loss_price:
                        # Stop-loss triggered
                        pnl = (current['close'] - entry_price) / entry_price * position['size']
                        balance += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'date': current.name,
                            'side': 'SELL',
                            'price': current['close'],
                            'pnl': pnl,
                            'balance': balance,
                            'reason': 'Stop-loss'
                        })
                        position = None
                        daily_trades[current_date] += 1
                    elif current['close'] >= take_profit_price:
                        # Take-profit triggered
                        pnl = (current['close'] - entry_price) / entry_price * position['size']
                        balance += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'date': current.name,
                            'side': 'SELL',
                            'price': current['close'],
                            'pnl': pnl,
                            'balance': balance,
                            'reason': 'Take-profit'
                        })
                        position = None
                        daily_trades[current_date] += 1
                
                elif side == ProcessedSideEnum.SELL.value:
                    stop_loss_price = entry_price * (1 + stop_loss_percent / 100)
                    take_profit_price = entry_price * (1 - take_profit_percent / 100)
                    
                    if current['close'] >= stop_loss_price:
                        # Stop-loss triggered
                        pnl = (entry_price - current['close']) / entry_price * position['size']
                        balance += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'date': current.name,
                            'side': 'BUY',
                            'price': current['close'],
                            'pnl': pnl,
                            'balance': balance,
                            'reason': 'Stop-loss'
                        })
                        position = None
                        daily_trades[current_date] += 1
                    elif current['close'] <= take_profit_price:
                        # Take-profit triggered
                        pnl = (entry_price - current['close']) / entry_price * position['size']
                        balance += pnl
                        daily_pnl[current_date] += pnl
                        trades.append({
                            'date': current.name,
                            'side': 'BUY',
                            'price': current['close'],
                            'pnl': pnl,
                            'balance': balance,
                            'reason': 'Take-profit'
                        })
                        position = None
                        daily_trades[current_date] += 1
            
            # Generate breakout signals
            # BUY signal: Price breaks above high + EMA cross + RSI not overbought
            if (current['close'] > current['high_20'] and 
                current['ema_5'] > current['ema_13'] and 
                current['rsi'] < 75 and 
                current['volume_ratio'] > 1.2):
                if not position or position['side'] == ProcessedSideEnum.SELL.value:
                    position_size = balance * position_size_percent / 100
                    position = {
                        'side': ProcessedSideEnum.BUY.value,
                        'price': current['close'],
                        'size': position_size,
                        'date': current.name
                    }
                    trades.append({
                        'date': current.name,
                        'side': 'BUY',
                        'price': current['close'],
                        'pnl': 0,
                        'balance': balance,
                        'reason': 'High breakout + EMA cross'
                    })
                    daily_trades[current_date] += 1
            
            # SELL signal: Price breaks below low + EMA cross + RSI not oversold
            elif (current['close'] < current['low_20'] and 
                  current['ema_5'] < current['ema_13'] and 
                  current['rsi'] > 25 and 
                  current['volume_ratio'] > 1.2):
                if position and position['side'] == ProcessedSideEnum.BUY.value:
                    pnl = (current['close'] - position['price']) / position['price'] * position['size']
                    balance += pnl
                    daily_pnl[current_date] += pnl
                    trades.append({
                        'date': current.name,
                        'side': 'SELL',
                        'price': current['close'],
                        'pnl': pnl,
                        'balance': balance,
                        'reason': 'Low breakout + EMA cross'
                    })
                    position = None
                    daily_trades[current_date] += 1
            
            # Additional momentum signals
            # BUY signal: Strong momentum + EMA cross up
            elif (current['momentum'] > 0 and 
                  current['ema_5'] > current['ema_13'] and 
                  previous['ema_5'] <= previous['ema_13'] and
                  current['rsi'] < 70):
                if not position or position['side'] == ProcessedSideEnum.SELL.value:
                    position_size = balance * position_size_percent / 100
                    position = {
                        'side': ProcessedSideEnum.BUY.value,
                        'price': current['close'],
                        'size': position_size,
                        'date': current.name
                    }
                    trades.append({
                        'date': current.name,
                        'side': 'BUY',
                        'price': current['close'],
                        'pnl': 0,
                        'balance': balance,
                        'reason': 'Momentum + EMA cross up'
                    })
                    daily_trades[current_date] += 1
            
            # SELL signal: Strong negative momentum + EMA cross down
            elif (current['momentum'] < 0 and 
                  current['ema_5'] < current['ema_13'] and 
                  previous['ema_5'] >= previous['ema_13'] and
                  current['rsi'] > 30):
                if position and position['side'] == ProcessedSideEnum.BUY.value:
                    pnl = (current['close'] - position['price']) / position['price'] * position['size']
                    balance += pnl
                    daily_pnl[current_date] += pnl
                    trades.append({
                        'date': current.name,
                        'side': 'SELL',
                        'price': current['close'],
                        'pnl': pnl,
                        'balance': balance,
                        'reason': 'Momentum + EMA cross down'
                    })
                    position = None
                    daily_trades[current_date] += 1
            
            # Record equity curve
            current_equity = balance
            if position:
                if position['side'] == ProcessedSideEnum.BUY.value:
                    unrealized_pnl = (current['close'] - position['price']) / position['price'] * position['size']
                    current_equity += unrealized_pnl
                else:
                    unrealized_pnl = (position['price'] - current['close']) / position['price'] * position['size']
                    current_equity += unrealized_pnl
            
            equity_curve.append({
                'date': current.name,
                'equity': current_equity,
                'balance': balance
            })
        
        return {
            'initial_balance': initial_balance,
            'final_balance': balance,
            'trades': trades,
            'equity_curve': equity_curve,
            'position': position,
            'daily_trades': daily_trades,
            'daily_pnl': daily_pnl
        }

    def _display_results(self, results, symbol, days):
        """Display breakout backtest results."""
        initial_balance = results['initial_balance']
        final_balance = results['final_balance']
        trades = results['trades']
        equity_curve = results['equity_curve']
        daily_trades = results['daily_trades']
        daily_pnl = results['daily_pnl']
        
        # Calculate statistics
        total_return = (final_balance - initial_balance) / initial_balance * 100
        daily_return = total_return / days
        
        profitable_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(profitable_trades) / len(trades) * 100 if trades else 0
        avg_profit = sum(t['pnl'] for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Calculate maximum drawdown
        max_equity = initial_balance
        max_drawdown = 0
        for point in equity_curve:
            if point['equity'] > max_equity:
                max_equity = point['equity']
            drawdown = (max_equity - point['equity']) / max_equity * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate daily statistics
        total_days = len(daily_trades)
        avg_daily_trades = sum(daily_trades.values()) / total_days if total_days > 0 else 0
        profitable_days = len([pnl for pnl in daily_pnl.values() if pnl > 0])
        daily_win_rate = profitable_days / total_days * 100 if total_days > 0 else 0
        
        # Display results
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'BREAKOUT BACKTEST RESULTS - {symbol}')
        self.stdout.write('=' * 60)
        
        self.stdout.write(f'Period: {days} days')
        self.stdout.write(f'Initial Balance: ${initial_balance:,.2f}')
        self.stdout.write(f'Final Balance: ${final_balance:,.2f}')
        self.stdout.write(f'Total Return: {total_return:+.2f}%')
        self.stdout.write(f'Daily Return: {daily_return:+.2f}%')
        
        if daily_return >= 0.1:  # 0.1% daily target
            self.stdout.write(self.style.SUCCESS(f'🎯 DAILY TARGET ACHIEVED! Daily return >= 0.1%'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Daily target not met. Need {0.1 - daily_return:.3f}% more daily return'))
        
        self.stdout.write(f'Max Drawdown: {max_drawdown:.2f}%')
        self.stdout.write(f'Total Trades: {len(trades)}')
        self.stdout.write(f'Win Rate: {win_rate:.1f}%')
        self.stdout.write(f'Average Profit: ${avg_profit:,.2f}')
        self.stdout.write(f'Average Loss: ${avg_loss:,.2f}')
        
        if avg_profit != 0 and avg_loss != 0:
            profit_loss_ratio = abs(avg_profit / avg_loss)
            self.stdout.write(f'Profit/Loss Ratio: {profit_loss_ratio:.2f}')
        
        # Daily statistics
        self.stdout.write(f'\nDaily Statistics:')
        self.stdout.write(f'Average Daily Trades: {avg_daily_trades:.1f}')
        self.stdout.write(f'Daily Win Rate: {daily_win_rate:.1f}%')
        self.stdout.write(f'Profitable Days: {profitable_days}/{total_days}')
        
        # Show recent trades
        if trades:
            self.stdout.write('\nRecent Trades:')
            self.stdout.write('-' * 60)
            for trade in trades[-20:]:  # Show last 20 trades
                pnl_str = f"+${trade['pnl']:,.2f}" if trade['pnl'] > 0 else f"-${abs(trade['pnl']):,.2f}"
                self.stdout.write(f"{trade['date'].strftime('%Y-%m-%d %H:%M')} | {trade['side']} @ ${trade['price']:,.2f} | {pnl_str} | {trade['reason']}")
        
        # Daily performance
        self.stdout.write('\nDaily Performance:')
        self.stdout.write('-' * 60)
        for date, pnl in sorted(daily_pnl.items()):
            trades_count = daily_trades[date]
            pnl_str = f"+${pnl:,.2f}" if pnl > 0 else f"-${abs(pnl):,.2f}"
            daily_return_pct = (pnl / initial_balance) * 100
            self.stdout.write(f"{date}: {pnl_str} ({daily_return_pct:+.2f}%) | {trades_count} trades")
        
        self.stdout.write('\n' + '=' * 60)
