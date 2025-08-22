from django import forms
from pydantic import BaseModel

from algo.models import StrategyConfig
from algo.strategies.enums import StrategyEnum


# --- Conceptual Utility for Strategy Configs ---
# You'll need to implement these Pydantic schemas and this function
# in a separate file (e.g., `algo/strategies/schemas.py`).
class StrategyMacdEmaCrossSchema(BaseModel):
    fast_ema_period: int
    slow_ema_period: int
    signal_ema_period: int
    short_ema_period: int
    long_ema_period: int
    order_book_depth_threshold: float

def get_strategy_schema(strategy_name: str):
    schemas = {
        StrategyEnum.StrategyMacdEmaCross.name: StrategyMacdEmaCrossSchema
    }
    return schemas.get(strategy_name, BaseModel)

# --- Custom Form for StrategyConfig Model ---

class StrategyConfigAdminForm(forms.ModelForm):
    """
    Custom form for the StrategyConfig model to provide a better user experience
    for the JSONField and other fields.
    """
    strategy_configs = forms.JSONField(
        widget=forms.Textarea(attrs={
            'placeholder': '{"fast_ema_period": 12, "slow_ema_period": 26, ...}',
            'rows': 5,
        }),
        help_text='JSON configuration for the selected strategy. Refer to the strategy documentation for required fields.',
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

