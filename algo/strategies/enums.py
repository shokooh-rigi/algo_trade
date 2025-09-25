from enum import Enum
from django.utils.translation import gettext_lazy as _

class StrategyEnum(Enum):
    """
    Enum for specifying the name of Strategies.
    """
    BreakoutStrategy = 'BreakoutStrategy'
    StrategyMacdEmaCross = 'StrategyMacdEmaCross'  # Keep for backward compatibility

    @classmethod
    def choices(cls):
        return [(member.value, _(member.name)) for member in cls]


class ProcessedSideEnum(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    BUY_AND_SELL = 'BUY_AND_SELL'
    NONE = 'NONE'

    @classmethod
    def choices(cls):
        """
        Returns choices in (value, display_name) format for Django models.
        Iterates over enum members to ensure proper initialization.
        """
        return [
            (member.value, _(member.name)) for member in cls
        ]

class StrategyState(Enum):
    """
    Enum for specifying the current state of a strategy instance.
    """
    STARTED = 0  # The strategy has been initialized and is ready to begin.
    RUNNING = 1  # The strategy is actively fetching data and analyzing signals.
    UPDATED = 2  # A change has been made to the strategy's configuration.
    STOPPED = 3  # The strategy has been intentionally shut down.
    NOT_ORDERING = 4 # The strategy is running but is currently not placing any new orders.

    @classmethod
    def choices(cls):
        """Returns choices in (value, display_name) format for Django models."""
        return [
            (cls.STARTED.value, _('Started')),
            (cls.RUNNING.value, _('Running')),
            (cls.UPDATED.value, _('Updated')),
            (cls.STOPPED.value, _('Stopped')),
            (cls.NOT_ORDERING.value, _('Not Ordering')),
        ]
