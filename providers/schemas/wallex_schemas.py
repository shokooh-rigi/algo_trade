from pydantic import BaseModel, Field
from typing import Optional, List

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

