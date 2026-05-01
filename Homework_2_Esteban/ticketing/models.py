from datetime import datetime

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    event_id: str = Field(..., description="Event associated with the order item.")
    zone_name: str = Field(..., description="Zone selected by the customer.")
    price_at_moment: float = Field(..., ge=0, description="Price captured at checkout time.")
    quantity: int = Field(..., ge=1, description="Number of tickets requested.")


class Order(BaseModel):
    id: str = Field(..., description="Unique identifier for the order.")
    customer_id: str = Field(..., description="Customer placing the order.")
    status: str = Field(..., description="Current order lifecycle state.")
    total: float = Field(..., ge=0, description="Total amount to be paid for the order.")
    items: list[OrderItem] = Field(..., description="Items included in the order.")
    created_at: datetime = Field(..., description="Timestamp when the order was created.")
    delivered_at: datetime | None = Field(None, description="Timestamp when digital tickets were delivered.")


class CheckoutRequest(BaseModel):
    customer_id: str = Field(..., description="Customer requesting checkout.")
    event_id: str = Field(..., description="Target event identifier.")
    zone_name: str = Field(..., description="Requested zone name.")
    quantity: int = Field(..., ge=1, description="Number of tickets requested.")