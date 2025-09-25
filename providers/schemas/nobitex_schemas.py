from pydantic import BaseModel, Field, condecimal
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class NobitexCreateOrderRequest(BaseModel):
    """
    Schema for creating an order on Nobitex.
    Endpoint: POST market/orders/add
    """
    type: str = Field(..., description="Order type: 'buy' or 'sell'")
    srcCurrency: str = Field(..., description="Source currency (e.g., 'BTC')")
    dstCurrency: str = Field(..., description="Destination currency (e.g., 'USDT', 'RLS')")
    amount: condecimal(decimal_places=8) = Field(..., description="Quantity of the source currency")
    price: Optional[condecimal(decimal_places=8)] = Field(None, description="Price for LIMIT orders")

class NobitexOrderInfoRequest(BaseModel):
    """
    Schema for requesting order information on Nobitex.
    Endpoint: POST v1/market/orders/status
    """
    id: int = Field(..., description="Nobitex internal order ID")

class NobitexCancelOrderRequest(BaseModel):
    """
    Schema for canceling an order on Nobitex.
    Endpoint: POST v1/market/orders/update-status
    """
    order: int = Field(..., description="Nobitex internal order ID")
    status: Literal["canceled"] = Field("canceled", description="Status to set for cancellation")

class NobitexGetBalanceRequest(BaseModel):
    """
    Schema for requesting balance of a specific currency on Nobitex.
    If currency is None, the endpoint should return all balances if supported.
    """
    currency: Optional[str] = Field(None, description="Currency symbol (e.g., 'btc', 'usdt')")

# --- Response Schemas ---

class NobitexSuccessResponse(BaseModel):
    """
    Generic success response from Nobitex APIs.
    Nobitex usually returns 'status': 'ok'.
    """
    status: str = Field(..., pattern="ok")

class NobitexOrderData(BaseModel):
    """
    Base schema for Nobitex order details in responses (active orders, order info).
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


class NobitexCreateOrderResponse(NobitexSuccessResponse):
    """
    Complete schema for Nobitex create order response.
    Endpoint: POST market/orders/add
    Nobitex's create order response directly contains the order fields.
    """
    order: NobitexOrderData


class NobitexActiveOrdersResponseResult(BaseModel):
    """
    Schema for the result of active orders response.
    """
    orders: List[NobitexOrderData]

class NobitexActiveOrdersResponse(NobitexSuccessResponse):
    """
    Complete schema for Nobitex active orders response.
    Endpoint: GET v1/account/openOrders
    """
    result: NobitexActiveOrdersResponseResult


class NobitexOrderInfoResponse(NobitexSuccessResponse):
    """
    Complete schema for Nobitex order information response.
    Endpoint: POST v1/market/orders/status
    Nobitex's order info response directly contains the order fields.
    """
    order: NobitexOrderData


class NobitexCancelOrderResponse(BaseModel): # Nobitex status might be outside 'status: ok'
    """
    Schema for Nobitex cancel order response.
    Endpoint: POST v1/market/orders/update-status
    """
    status: str = Field(..., pattern="ok")
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
    Endpoint: POST v2/users/wallets/balance
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

class NobitexOHLCVResponse(BaseModel):
    """
    Schema for the Nobitex historical OHLCV data response.
    """
    s: str = Field(..., description="Status: 'ok', 'error', or 'no_data'")
    t: Optional[List[int]] = Field(None, description="Timestamps")
    o: Optional[List[float]] = Field(None, description="Open prices")
    h: Optional[List[float]] = Field(None, description="High prices")
    l: Optional[List[float]] = Field(None, description="Low prices")
    c: Optional[List[float]] = Field(None, description="Close prices")
    v: Optional[List[float]] = Field(None, description="Volumes")
    errmsg: Optional[str] = Field(None, description="Error message if s='error'")


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
