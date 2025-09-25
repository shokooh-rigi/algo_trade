from django import forms
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from algo.models import StrategyConfig
from algo.strategies.enums import StrategyEnum
from algo.strategies.schemas import get_strategy_schema

class StrategyConfigAdminForm(forms.ModelForm):
    """
    Custom form for the StrategyConfig model to provide a better user experience
    for the JSONField and other fields.
    """
    strategy_configs = forms.JSONField(
        initial={
            "ema_fast_period": 5,
            "ema_slow_period": 13,
            "rsi_period": 14,
            "rsi_overbought": 75.0,
            "rsi_oversold": 25.0,
            "volume_period": 5,
            "volume_threshold": 1.2,
            "breakout_period": 20,
            "momentum_period": 3,
            "stop_loss_percent": 0.3,
            "take_profit_percent": 0.6,
            "max_position_size_percent": 50.0,
            "trade_cooldown_minutes": 30,
            "max_daily_trades": 10,
            "order_book_depth_threshold": 1.5
        },
        widget=forms.Textarea(attrs={
            'rows': 15,
            'cols': 80,
            'style': 'width: 100%; max-width: 100%; height: 300px; font-family: monospace; font-size: 12px;',
        }),
        help_text='''JSON configuration for the Breakout Strategy. Each parameter explained:
        
EMA Parameters:
- ema_fast_period: Fast EMA period for quick signals (default: 5)
- ema_slow_period: Slow EMA period for trend direction (default: 13)

RSI Parameters:
- rsi_period: RSI calculation period (default: 14)
- rsi_overbought: RSI overbought level (default: 75.0)
- rsi_oversold: RSI oversold level (default: 25.0)

Volume Analysis:
- volume_period: Volume SMA period (default: 5)
- volume_threshold: Volume ratio threshold, 120% of average (default: 1.2)

Breakout Detection:
- breakout_period: High/Low breakout detection period (default: 20)
- momentum_period: Momentum calculation period (default: 3)

Risk Management:
- stop_loss_percent: Stop loss percentage (default: 0.3)
- take_profit_percent: Take profit percentage (default: 0.6)
- max_position_size_percent: Maximum position size percentage (default: 50.0)

Trade Management:
- trade_cooldown_minutes: Cooldown between trades in minutes (default: 30)
- max_daily_trades: Maximum trades per day (default: 10)

Order Book Analysis:
- order_book_depth_threshold: Order book imbalance threshold (default: 1.5)''',
    )

    def clean_strategy_configs(self):
        """
        Validates the JSON configuration against the strategy's Pydantic schema.
        """
        strategy_name = self.cleaned_data.get('strategy')
        config_data = self.cleaned_data.get('strategy_configs')
        if not strategy_name or not config_data:
            return config_data

        schema = get_strategy_schema(strategy_name)
        try:
            schema(**config_data)
        except PydanticValidationError as e:
            raise forms.ValidationError(f"Invalid configuration for '{strategy_name}': {e.errors()}")
        return config_data

    class Meta:
        model = StrategyConfig
        fields = [
            'id',
            'strategy',
            'market',
            'store_client',
            'state',
            'is_active',
            'need_historical_data',
            'initial_history_period_days',
            'resolution',
            'strategy_configs',
            'sensitivity_percent',
        ]

