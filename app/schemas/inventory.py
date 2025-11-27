
import uuid
from pydantic import BaseModel


class InventoryResponse(BaseModel):
    """Schema for fetching inventory stock."""
    menu_item_id: uuid.UUID
    available_qty: int
    updated_at: str