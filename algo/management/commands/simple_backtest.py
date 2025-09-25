"""
Simple backtest command for testing strategy performance.
"""

from django.core.management.base import BaseCommand
from providers.nobitex_provider import NobitexProvider
from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Simple backtest for MACD EMA Cross strategy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            default='BTCUSDT',
            help='Trading symbol to backtest (default: BTCUSDT)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to backtest (default: 30)'
        )

    def handle(self, *args, **options):
        symbol = options['symbol']
        days = options['days']
        
        self.stdout.write(f"Starting simple backtest for {symbol} over {days} days...")
        
        # Fetch historical data
        nobitex_provider = NobitexProvider({})
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        raw_data = nobitex_provider.fetch_ohlcv_data(
            symbol=symbol,
            resolution="D",
            from_timestamp=start_ts,
            to_timestamp=end_ts
        )
        
        if not raw_data:
            self.stdout.write(self.style.ERROR(f"No historical data available for {symbol}"))
            return
        
        self.stdout.write(f"Fetched {len(raw_data)} candles for {symbol}")
        
        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')
        
        # Ensure numeric data types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna()
        
        if len(df) < 50:  # Need at least 50 data points for indicators
            self.stdout.write(self.style.ERROR(f"Not enough data points: {len(df)} (need at least 50)"))
            return
        
        # Calculate MACD
        import pandas_ta as ta
        
        # MACD parameters
        fast_ema = 12
        slow_ema = 26
        signal_ema = 9
        
        # Calculate MACD
        macd_df = ta.macd(df['close'], fast=fast_ema, slow=slow_ema, signal=signal_ema, append=False)
        
        if macd_df is not None and isinstance(macd_df, pd.DataFrame):
            # Find MACD columns
            macd_col = None
            signal_col = None
            
            for col in macd_df.columns:
                if 'MACD_' in col and 'MACDs_' not in col:
                    macd_col = col
                elif 'MACDs_' in col:
                    signal_col = col
            
            if macd_col and signal_col:
                df['macd'] = macd_df[macd_col]
                df['signal'] = macd_df[signal_col]
                
                # Calculate EMAs
                df['short_ema'] = ta.ema(df['close'], length=50)
                df['long_ema'] = ta.ema(df['close'], length=200)
                
                # Remove rows with NaN values in indicators
                df = df.dropna()
                
                # Find signals
                signals = []
                trades = []
                balance = 10000  # Starting balance
                position = 0
                position_size = 0.1  # 10% of balance per trade
                
                for i in range(1, len(df)):
                    current_macd = df['macd'].iloc[i]
                    current_signal = df['signal'].iloc[i]
                    prev_macd = df['macd'].iloc[i-1]
                    prev_signal = df['signal'].iloc[i-1]
                    
                    current_short_ema = df['short_ema'].iloc[i]
                    current_long_ema = df['long_ema'].iloc[i]
                    prev_short_ema = df['short_ema'].iloc[i-1]
                    prev_long_ema = df['long_ema'].iloc[i-1]
                    
                    current_price = df['close'].iloc[i]
                    current_time = df.index[i]
                    
                    # MACD crossover signals
                    macd_cross_buy = prev_macd <= prev_signal and current_macd > current_signal
                    macd_cross_sell = prev_macd >= prev_signal and current_macd < current_signal
                    
                    # EMA crossover signals
                    ema_cross_buy = prev_short_ema <= prev_long_ema and current_short_ema > current_long_ema
                    ema_cross_sell = prev_short_ema >= prev_long_ema and current_short_ema < current_long_ema
                    
                    # Generate signals
                    if macd_cross_buy or ema_cross_buy:
                        signals.append({
                            'time': current_time,
                            'type': 'BUY',
                            'price': current_price,
                            'reason': f"MACD: {macd_cross_buy}, EMA: {ema_cross_buy}"
                        })
                        
                        # Execute buy trade
                        trade_value = balance * position_size
                        balance -= trade_value
                        position = trade_value / current_price
                        
                        trades.append({
                            'time': current_time,
                            'side': 'BUY',
                            'price': current_price,
                            'amount': position,
                            'value': trade_value,
                            'balance': balance
                        })
                        
                    elif macd_cross_sell or ema_cross_sell:
                        signals.append({
                            'time': current_time,
                            'type': 'SELL',
                            'price': current_price,
                            'reason': f"MACD: {macd_cross_sell}, EMA: {ema_cross_sell}"
                        })
                        
                        # Execute sell trade
                        if position > 0:
                            trade_value = position * current_price
                            balance += trade_value
                            
                            trades.append({
                                'time': current_time,
                                'side': 'SELL',
                                'price': current_price,
                                'amount': position,
                                'value': trade_value,
                                'balance': balance
                            })
                            
                            position = 0
                
                # Calculate final results
                final_price = df['close'].iloc[-1]
                final_balance = balance + (position * final_price if position > 0 else 0)
                total_return = (final_balance - 10000) / 10000 * 100
                
                # Count winning/losing trades
                winning_trades = 0
                losing_trades = 0
                total_profit = 0
                total_loss = 0
                
                for i in range(1, len(trades)):
                    if trades[i]['side'] == 'SELL' and trades[i-1]['side'] == 'BUY':
                        profit_loss = trades[i]['value'] - trades[i-1]['value']
                        if profit_loss > 0:
                            winning_trades += 1
                            total_profit += profit_loss
                        else:
                            losing_trades += 1
                            total_loss += abs(profit_loss)
                
                # Display results
                self.stdout.write("\n" + "="*60)
                self.stdout.write(f"BACKTEST RESULTS FOR {symbol.upper()}")
                self.stdout.write("="*60)
                self.stdout.write(f"Period: {days} days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
                self.stdout.write(f"Starting Balance: $10,000")
                self.stdout.write(f"Final Balance: ${final_balance:,.2f}")
                self.stdout.write(f"Total Return: {total_return:.2f}%")
                self.stdout.write(f"Total Signals: {len(signals)}")
                self.stdout.write(f"Total Trades: {len(trades)}")
                self.stdout.write(f"Winning Trades: {winning_trades}")
                self.stdout.write(f"Losing Trades: {losing_trades}")
                if winning_trades + losing_trades > 0:
                    win_rate = winning_trades / (winning_trades + losing_trades) * 100
                    self.stdout.write(f"Win Rate: {win_rate:.1f}%")
                self.stdout.write(f"Total Profit: ${total_profit:,.2f}")
                self.stdout.write(f"Total Loss: ${total_loss:,.2f}")
                self.stdout.write(f"Net Profit: ${total_profit - total_loss:,.2f}")
                
                # Show recent signals
                if signals:
                    self.stdout.write("\nRecent Signals:")
                    for signal in signals[-5:]:  # Show last 5 signals
                        self.stdout.write(f"  {signal['time'].strftime('%Y-%m-%d')}: {signal['type']} at ${signal['price']:,.2f} - {signal['reason']}")
                
                self.stdout.write("="*60)
                
            else:
                self.stdout.write(self.style.ERROR("Could not find MACD columns in calculation result"))
        else:
            self.stdout.write(self.style.ERROR("MACD calculation failed"))
        
        self.stdout.write(self.style.SUCCESS(f"Backtest completed for {symbol}"))
