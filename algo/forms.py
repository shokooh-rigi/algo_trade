from django import forms
from pydantic import BaseModel

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

