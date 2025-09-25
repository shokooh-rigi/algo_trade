"""
Django management command for backtesting trading strategies.
"""

from django.core.management.base import BaseCommand
from algo.services.backtest_service import BacktestService
from algo.strategies.schemas import StrategyMacdEmaCrossSchema
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backtest trading strategies using historical data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            default='BTCUSDT',
            help='Trading symbol to backtest (default: BTCUSDT)'
        )
        parser.add_argument(
            '--periods',
            nargs='+',
            default=['last_week', 'last_month', 'last_year'],
            help='Time periods to backtest (default: last_week, last_month, last_year)'
        )
        parser.add_argument(
            '--resolution',
            type=str,
            default='D',
            help='Data resolution (D for daily, 4h for 4-hour, etc.)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file to save the report'
        )

    def handle(self, *args, **options):
        symbol = options['symbol']
        periods = options['periods']
        resolution = options['resolution']
        output_file = options['output_file']

        self.stdout.write(f"Starting backtest for {symbol}...")

        # Default strategy configuration
        strategy_config = {
            "fast_ema_period": 12,
            "slow_ema_period": 26,
            "signal_ema_period": 9,
            "short_ema_period": 50,
            "long_ema_period": 200,
            "order_book_depth_threshold": 0.8,
            "htf_resolution": "4h",
            "htf_ema_length": 50,
            "min_adx": 18.0,
            "min_atr_percent": 0.15,
            "volume_percentile_window": 50,
            "volume_percentile_threshold": 70,
            "trade_cooldown_minutes": 45
        }

        # Validate configuration
        try:
            validated_config = StrategyMacdEmaCrossSchema(**strategy_config)
            self.stdout.write("Strategy configuration validated successfully.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Invalid strategy configuration: {e}"))
            return

        # Initialize backtest service
        backtest_service = BacktestService()

        # Run backtests for specified periods
        results = {}
        for period in periods:
            self.stdout.write(f"Backtesting {symbol} for {period}...")
            try:
                if period == 'last_week':
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                elif period == 'last_month':
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                elif period == 'last_3_months':
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=90)
                elif period == 'last_6_months':
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=180)
                elif period == 'last_year':
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=365)
                else:
                    self.stdout.write(self.style.ERROR(f"Unknown period: {period}"))
                    continue

                result = backtest_service.backtest_strategy(
                    symbol=symbol,
                    strategy_config=strategy_config,
                    start_date=start_date,
                    end_date=end_date,
                    resolution=resolution
                )
                results[period] = result
                
                # Display quick summary
                summary = result.get_summary()
                self.stdout.write(
                    f"  {period}: {summary['total_return_percent']:.2f}% return, "
                    f"{summary['total_trades']} trades, {summary['win_rate_percent']:.1f}% win rate"
                )
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error backtesting {period}: {e}"))
                continue

        # Generate comprehensive report
        report = backtest_service.generate_report(results, symbol)
        
        # Display report
        self.stdout.write("\n" + "="*80)
        self.stdout.write(report)
        self.stdout.write("="*80)

        # Save to file if specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                self.stdout.write(f"\nReport saved to: {output_file}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving report: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Backtest completed for {symbol}"))
