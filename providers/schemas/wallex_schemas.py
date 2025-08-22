from pydantic import BaseModel, Field, condecimal
from typing import List, Optional, Dict, Any
from datetime import datetime


class CreateOrderRequestSchema(BaseModel):
    """
    Schema for creating an order request.

    Attributes:
        symbol (Optional[str]): The trading pair symbol (e.g., "BTCUSDT").
        type (Optional[str]): The type of order (e.g., "LIMIT").
        side (Optional[str]): The side of the order (e.g., "BUY" or "SELL").
        price (Optional[float]): The price at which the order should be executed.
        quantity (Optional[float]): The quantity of the asset to be traded.
    """
    symbol: Optional[str] = Field(None, description="The trading pair symbol (e.g., BTCUSDT).")
    type: Optional[str] = Field(None, description="The type of order (e.g., LIMIT or MARKET).")
    side: Optional[str] = Field(None, description="The side of the order (BUY or SELL).")
    price: Optional[float] = Field(None, description="The price at which the order should be executed.")
    quantity: Optional[float] = Field(None, description="The quantity of the asset to be traded.")


class OrderResultSchema(BaseModel):
    """
    Schema for the result of creating an order.

    Attributes:
        symbol (Optional[str]): The trading pair symbol.
        type (Optional[str]): The type of order.
        side (Optional[str]): The side of the order.
        price (Optional[str]): The price of the order as a string.
        orig_qty (Optional[str]): The original quantity as a string.
        orig_sum (Optional[str]): The original sum as a string.
        executed_price (Optional[str]): The executed price as a string.
        executed_qty (Optional[str]): The executed quantity as a string.
        executed_sum (Optional[str]): The executed sum as a string.
        executed_percent (Optional[int]): The percentage of the order that has been executed.
        status (Optional[str]): The status of the order (e.g., "NEW").
        active (Optional[bool]): Whether the order is active.
        client_order_id (Optional[str]): The client order ID.
    """
    symbol: Optional[str] =None
    type: Optional[str] =None
    side: Optional[str] =None
    price: Optional[str] =None
    orig_qty: Optional[str] =None
    orig_sum: Optional[str] = None
    executed_price: Optional[str] =None
    executed_qty: Optional[str] =None
    executed_sum: Optional[str] =None
    executed_percent: Optional[int] =None
    status: Optional[str] =None
    active: Optional[bool] =None
    timestamp_created_at: Optional[str] =None
    client_order_id: Optional[str] =None


class OrderResponseSchema(BaseModel):
    """
    Schema for the response of creating an order.

    Attributes:
        success (Optional[bool]): Indicates if the operation was successful.
        message (Optional[str]): The response message.
        result (Optional[OrderResultSchema]): The detailed result of the order creation.
    """
    success: Optional[bool]
    message: Optional[str]
    result: Optional[OrderResultSchema]


class ActiveOrdersResultSchema(BaseModel):
    """
    Schema for the detailed active orders response.

    Attributes:
        orders (List[OrderResultSchema]): A list of active orders with detailed information.
    """
    orders: Optional[List[OrderResultSchema]]


class ActiveOrdersResponseSchema(BaseModel):
    """
    Schema for the response of ActiveOrdersResponseSchema an order.

    Attributes:
        success (Optional[bool]): Indicates if the operation was successful.
        message (Optional[str]): The response message.
        result (Optional[OrderResultSchema]): The detailed result of the order creation.
    """
    success: Optional[bool]
    message: Optional[str]
    result: Optional[ActiveOrdersResultSchema]


class WallexCreateOrderRequest(BaseModel):
    """
    Schema for creating an order on Wallex.
    Note: Wallex API often expects a specific payload format for orders.
    """
    symbol: str = Field(..., description="The trading pair symbol (e.g., BTCUSDT).")
    type: str = Field(..., description="The type of order (e.g., LIMIT or MARKET).")
    side: str = Field(..., description="The side of the order (BUY or SELL).")
    price: Optional[condecimal(decimal_places=8)] = Field(None, description="The price at which the order should be executed.")
    quantity: Optional[condecimal(decimal_places=8)] = Field(None, description="The quantity of the asset to be traded.")

class WallexOrderInfoRequest(BaseModel):
    """
    Schema for requesting order information on Wallex.
    """
    clientOrderId: str = Field(..., description="The client order ID.")

class WallexCancelOrderRequest(BaseModel):
    """
    Schema for canceling an order on Wallex.
    """
    clientOrderId: str = Field(..., description="The client order ID of the order to cancel.")

class WallexGetBalanceRequest(BaseModel):
    """
    Schema for requesting balance data for a specific asset on Wallex.
    Wallex's get_balances API usually doesn't take a specific currency as a request parameter in body.
    It returns all balances. This schema might not be directly used for requests but for conceptual consistency.
    """
    pass # Wallex's balance endpoint is often a GET request with no body parameters

# --- Response Schemas ---

class WallexSuccessResponse(BaseModel):
    """
    Generic success response from Wallex APIs.
    """
    success: bool
    message: Optional[str] = None

class WallexErrorResponse(BaseModel):
    """
    Generic error response from Wallex APIs.
    """
    success: bool = Field(False)
    message: str

class WallexOrderResultData(BaseModel):
    """
    Schema for the result of a single order from Wallex.
    """
    symbol: str
    type: str
    side: str
    price: Optional[str] = None
    orig_qty: Optional[str] = None
    orig_sum: Optional[str] = None
    executed_price: Optional[str] = None
    executed_qty: Optional[str] = None
    executed_sum: Optional[str] = None
    executed_percent: Optional[int] = None
    status: str
    active: Optional[bool] = None
    client_order_id: Optional[str] = None
    timestamp_created_at: Optional[str] = None

class WallexCreateOrderResponse(WallexSuccessResponse):
    """
    Complete schema for Wallex create order response.
    """
    result: Optional[WallexOrderResultData]

class WallexActiveOrdersResponseResult(BaseModel):
    """
    Schema for the result of active orders response.
    """
    orders: List[WallexOrderResultData]

class WallexActiveOrdersResponse(WallexSuccessResponse):
    """
    Complete schema for Wallex active orders response.
    """
    result: Optional[WallexActiveOrdersResponseResult]

class WallexOrderInfoResponse(WallexSuccessResponse):
    """
    Complete schema for Wallex order information response.
    """
    result: Optional[WallexOrderResultData]

class WallexCancelOrderResponse(WallexSuccessResponse):
    """
    Schema for Wallex cancel order response.
    Wallex's cancel response might just be success/message.
    """
    pass # Specific result fields might vary, often just success/message

class WallexBalanceDetail(BaseModel):
    """
    Schema for individual currency balance details from Wallex.
    """
    currency: str
    total: str
    available: str
    locked: str

class WallexGetBalancesResponseResult(BaseModel):
    """
    Schema for the result of Wallex get balances response.
    """
    balances: List[WallexBalanceDetail]

class WallexGetBalancesResponse(WallexSuccessResponse):
    """
    Complete schema for Wallex get balances response.
    """
    result: Optional[WallexGetBalancesResponseResult]


class WallexCandlestickData(BaseModel):
    """
    Conceptual schema for a single OHLCV candlestick from Wallex API.
    This assumes a structure similar to common exchange APIs for historical data.
    """
    time: int    # Unix timestamp (seconds)
    open: float
    high: float
    low: float
    close: float
    volume: float

class WallexOHLCVResponseResult(BaseModel):
    """
    Conceptual schema for the result list of OHLCV data.
    """
    candles: List[WallexCandlestickData]

class WallexOHLCVResponse(WallexSuccessResponse):
    """
    Conceptual schema for the Wallex historical OHLCV data response.
    This is a conceptual schema as a direct public OHLCV endpoint for Wallex.ir
    is not clearly documented.
    """
    result: Optional[WallexOHLCVResponseResult]
