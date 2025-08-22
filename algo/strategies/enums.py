from enum import Enum
from django.utils.translation import gettext_lazy as _


class StrategyEnum(Enum):
    """
    Enum for specifying the name of Strategies.
    """
    StrategyMacdEmaCross = 'StrategyMacdEmaCross'


class ProcessedSideEnum(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    BUY_AND_SELL = 'BUY_AND_SELL'
    NONE = 'NONE'


class StrategyState(Enum):
    """
    Enum for specifying the current state of a strategy instance.
    """
    STARTED = 0  # The strategy has been initialized and is ready to begin.
    RUNNING = 1  # The strategy is actively fetching data and analyzing signals.
    UPDATED = 2  # A change has been made to the strategy's configuration.
    STOPPED = 3  # The strategy has been intentionally shut down.
    NOT_ORDERING = 4 # The strategy is running but is currently not placing any new orders.

    CHOICES = [
        (STARTED.value, _('Started')),
        (RUNNING.value, _('Running')),
        (UPDATED.value, _('Updated')),
        (STOPPED.value, _('Stopped')),
        (NOT_ORDERING.value, _('Not Ordering')),
    ]