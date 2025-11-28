
import uuid
from pydantic import BaseModel
from pydantic import BaseModel, Field


class InventoryResponse(BaseModel):
    """Schema for fetching inventory stock."""
    menu_item_id: uuid.UUID
    available_qty: int
    updated_at: str

class RestaurantRequest(BaseModel):
    name: str = Field(..., description="Name of the restaurant.")
    is_active: bool = Field(True, description="Whether the restaurant is currently active.")

class InventoryItemRequest(BaseModel):
    name: str = Field(..., description="Name of the menu item (e.g., Chicken Biryani).")
    price: float = Field(..., gt=0, description="Selling price of the item.")
    initial_qty: int = Field(..., ge=0, description="Initial available stock quantity.")
    threshold_qty: int = Field(10, ge=0, description="Minimum stock level before an alert is triggered.")
    is_active: bool = Field(True, description="Whether the menu item is active.")