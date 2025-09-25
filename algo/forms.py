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
        widget=forms.Textarea(attrs={
            'placeholder': '''{
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
            }''',
            'rows': 8,
        }),
        help_text='''JSON configuration for the selected strategy. Each parameter explained:
        
MACD Parameters:
- fast_ema_period: Fast EMA period for MACD calculation (default: 12)
- slow_ema_period: Slow EMA period for MACD calculation (default: 26) 
- signal_ema_period: Signal line EMA for MACD (default: 9)

EMA Cross Parameters:
- short_ema_period: Short-term EMA for trend confirmation (default: 50)
- long_ema_period: Long-term EMA for trend confirmation (default: 200)

Risk Management:
- order_book_depth_threshold: Buy/sell ratio threshold 0.0-1.0 (default: 0.8)
- min_adx: Minimum ADX for trend strength, avoid choppy markets (default: 18.0)
- min_atr_percent: Minimum volatility threshold as % of price (default: 0.15)

Volume Analysis:
- volume_percentile_window: Lookback period for volume analysis (default: 50)
- volume_percentile_threshold: Volume must be above this percentile 0-100 (default: 70)

Higher Timeframe Confirmation:
- htf_resolution: Higher timeframe resolution (default: "4h")
- htf_ema_length: EMA length on higher timeframe (default: 50)

Trade Management:
- trade_cooldown_minutes: Cooldown between opposite trades in minutes (default: 45)''',
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

