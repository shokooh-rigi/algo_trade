from django.utils.translation import gettext_lazy as _
from enum import Enum


class OrderType:
    """Enum for Order Type."""
    LIMIT = 'LIMIT'
    MARKET = 'MARKET'

    CHOICES = [
        (LIMIT, _('LIMIT')),
        (MARKET, _('MARKET')),
    ]


class OrderSide:
    """Enum for Order Side."""
    BUY = 'BUY'
    SELL = 'SELL'

    CHOICES = [
        (BUY, _('BUY')),
        (SELL, _('SELL')),
    ]


class OrderStatus:
    """Enum for Order Status."""
    NEW = 'NEW'
    FILLED = 'FILLED'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    CANCELED = 'CANCELED'

    CHOICES = [
        (NEW, _('New')),
        (FILLED, _('Filled')),
        (PARTIALLY_FILLED, _('Partially Filled')),
        (CANCELED, _('Canceled')),
    ]


class QuoteEnum(Enum):
    USDT = 'USDT'
    TMN = 'TMN'


class BalanceState:
    """Enum for balance state."""
    UPPER_BALANCE = 'UPPER_BALANCE'
    LOWER_BALANCE = 'LOWER_BALANCE'
    UPPER_UNBALANCE = 'UPPER_UNBALANCE'
    LOWER_UNBALANCE = 'LOWER_UNBALANCE'
    DESIRED = 'DESIRED'


    CHOICES = [
        (UPPER_BALANCE, _('UPPER_BALANCE')),
        (LOWER_BALANCE, _('LOWER_BALANCE')),
        (UPPER_UNBALANCE, _('UPPER_UNBALANCE')),
        (LOWER_UNBALANCE, _('LOWER_UNBALANCE')),
        (DESIRED, _('DESIRED')),
    ]

class StateTransition(Enum):
    STABLE = "STABLE"
    UNSTABLE = "UNSTABLE"
    NONE = "NONE"



class DesiredBalanceAsset:
    """
    Enum for desired balance asset.
    This is used to define the asset for which the desired balance is calculated.
    """
    USDT = 'USDT'
    TMN = 'TMN'

    CHOICES = [
        (USDT, _('USDT')),
        (TMN, _('TMN')),
    ]