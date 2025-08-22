from pydantic import BaseModel, Field, condecimal
from typing import List, Optional, Dict, Any


class NobitexCreateOrderRequest(BaseModel):
    """
    Schema for creating an order on Nobitex.
    """
    type: str = Field(..., description="Order type: 'buy' or 'sell'")
    srcCurrency: str = Field(..., description="Source currency (e.g., 'BTC')")
    dstCurrency: str = Field(..., description="Destination currency (e.g., 'USDT', 'RLS')")
    amount: condecimal(decimal_places=8) = Field(..., description="Quantity of the source currency")
    price: Optional[condecimal(decimal_places=8)] = Field(None, description="Price for LIMIT orders")

class NobitexOrderInfoRequest(BaseModel):
    """
    Schema for requesting order information on Nobitex.
    """
    id: int = Field(..., description="Nobitex internal order ID")

class NobitexCancelOrderRequest(BaseModel):
    """
    Schema for canceling an order on Nobitex.
    """
    order: int = Field(..., description="Nobitex internal order ID")
    status: str = Field("canceled", const=True, description="Status to set for cancellation")

class NobitexGetBalanceRequest(BaseModel):
    """
    Schema for requesting balance of a specific currency on Nobitex.
    If currency is None, the endpoint should return all balances if supported.
    """
    currency: Optional[str] = Field(None, description="Currency symbol (e.g., 'btc', 'usdt')")

# --- Response Schemas ---

class NobitexOrderData(BaseModel):
    """
    Base schema for Nobitex order details in responses.
    """
    id: int
    type: str # 'buy' or 'sell'
    srcCurrency: str
    dstCurrency: str
    amount: str
    price: str
    matchedAmount: str
    unmatchedAmount: str
    status: str # 'New', 'Partially Filled', 'Done', 'Canceled'
    created_at: str
    totalPrice: Optional[str] = None # Often present in order info responses

class NobitexCreateOrderResponseResult(BaseModel):
    """
    Schema for the result section of a Nobitex create order response.
    """
    order: NobitexOrderData

class NobitexSuccessResponse(BaseModel):
    """
    Generic success response from Nobitex APIs.
    """
    status: str = Field(..., pattern="ok")
    # message: Optional[str] = None # Nobitex typically uses status: ok/failed

class NobitexCreateOrderResponse(NobitexSuccessResponse):
    """
    Complete schema for Nobitex create order response.
    """
    result: NobitexCreateOrderResponseResult


class NobitexActiveOrdersResponseResult(BaseModel):
    """
    Schema for the result of active orders response.
    """
    orders: List[NobitexOrderData]

class NobitexActiveOrdersResponse(NobitexSuccessResponse):
    """
    Complete schema for Nobitex active orders response.
    """
    result: NobitexActiveOrdersResponseResult


class NobitexOrderInfoResponseResult(BaseModel):
    """
    Schema for the result of order info response.
    """
    order: NobitexOrderData

class NobitexOrderInfoResponse(NobitexSuccessResponse):
    """
    Complete schema for Nobitex order information response.
    """
    result: NobitexOrderInfoResponseResult


class NobitexCancelOrderResponse(NobitexSuccessResponse):
    """
    Schema for Nobitex cancel order response.
    """
    updatedStatus: str = Field(..., pattern="Canceled") # Expected status after successful cancellation

class NobitexBalanceDetail(BaseModel):
    """
    Schema for individual currency balance details.
    """
    total: str
    available: str
    locked: str

class NobitexGetBalancesResponse(NobitexSuccessResponse):
    """
    Schema for Nobitex get balances response.
    The 'balance' field is a dictionary where keys are currency symbols.
    """
    balance: Dict[str, NobitexBalanceDetail]


class NobitexCandlestick(BaseModel):
    """
    Schema for a single OHLCV candlestick from Nobitex API.
    """
    t: int  # Unix timestamp
    o: float # Open price
    h: float # High price
    l: float # Low price
    c: float # Close price
    v: float # Volume

class NobitexOHLCVResponse(NobitexSuccessResponse):
    """
    Schema for the Nobitex historical OHLCV data response.
    """
    # The fields are lists of values, corresponding to t, o, h, l, c, v
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: List[float]


# --- Common API Response for your system ---
# These are the schemas you already have, potentially updated to use Pydantic types.
# You might want to move these to a common `algo_trade/schemas.py` or similar.


class OrderResultSchema(BaseModel):
    symbol: Optional[str] = None
    type: Optional[str] = None
    side: Optional[str] = None
    price: Optional[str] = None
    orig_qty: Optional[str] = None
    orig_sum: Optional[str] = None
    executed_price: Optional[str] = None
    executed_qty: Optional[str] = None
    executed_sum: Optional[str] = None
    executed_percent: Optional[int] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    timestamp_created_at: Optional[str] = None
    client_order_id: Optional[str] = None

class OrderResponseSchema(BaseModel):
    success: Optional[bool]
    message: Optional[str]
    result: Optional[OrderResultSchema]

class ActiveOrdersResultSchema(BaseModel):
    orders: Optional[List[OrderResultSchema]]

class ActiveOrdersResponseSchema(BaseModel):
    success: Optional[bool]
    message: Optional[str]
    result: Optional[ActiveOrdersResultSchema]
