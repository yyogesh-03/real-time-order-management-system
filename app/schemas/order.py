from enum import Enum
from tortoise import fields, models
from pydantic import BaseModel
from typing import List, Optional
import uuid
from decimal import Decimal

class OrderStatus(str, Enum):
    PLACED = "PLACED"  # Initial state, waiting for inventory check (Fast Path Success)
    PREPARING = "PREPARING" # Inventory check success (Slow Path Success)
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class OrderItemRequest(BaseModel):
    """Schema for a single item in the order request."""
    menu_item_id: uuid.UUID
    quantity: int

class OrderRequest(BaseModel):
    """Schema for the full order placement request body."""
    restaurant_id: uuid.UUID
    items: List[OrderItemRequest]

class OrderPlacementResponse(BaseModel):
    """Response schema for a newly placed order (202 Accepted)."""
    order_id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    message: str

class OrderStatusUpdate(BaseModel):
    """Schema for updating an order status."""
    status: OrderStatus

class OrderItemResponse(BaseModel):
    """Schema for an item inside the detailed order response."""
    name: str
    quantity: int
    price: str  # Use string for Decimal type serialization

class OrderDetailResponse(BaseModel):
    """Schema for fetching detailed order information."""
    id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    items: List[OrderItemResponse]
    created_at: str

