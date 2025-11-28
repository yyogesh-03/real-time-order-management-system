import logging
from fastapi import APIRouter, HTTPException, status
from app.models.inventory import Inventory
from app.models.order import MenuItem, Restaurant
from app.schemas.inventory import InventoryItemRequest, InventoryResponse, RestaurantRequest
from uuid import UUID
from typing import Dict, Any

log = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

router = APIRouter()

@router.get("/{menu_item_id}", response_model=InventoryResponse)
async def get_inventory_stock(menu_item_id: UUID):
    """Fetches the available stock for a specific menu item."""
    try:
        # FastAPI path converter ensures menu_item_id is a valid UUID
        inventory = await Inventory.get_or_none(menu_item_id=menu_item_id)
        if not inventory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found for item.")
        
        return InventoryResponse(
            menu_item_id=inventory.menu_item_id,
            available_qty=inventory.available_qty,
            updated_at=str(inventory.updated_at)
        )
    except Exception as e:
        log.error(f"Error fetching inventory: {e}")
        raise HTTPException(status_code=500, detail="Server failed to fetch inventory.")


@router.post("/add/{restaurant_id}/item", status_code=status.HTTP_201_CREATED)
async def add_inventory_item(restaurant_id: UUID, item_data: InventoryItemRequest):
    """
    Adds a new menu item and its initial inventory to a specified restaurant. 
    This is the user-friendly way to add data via the API.
    """
    try:
        # 1. Validate Restaurant Exists
        try:
            restaurant = await Restaurant.get(id=restaurant_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant with ID {restaurant_id} not found."
            )

        # 2. Create the Menu Item
        menu_item = await MenuItem.create(
            restaurant=restaurant,
            name=item_data.name,
            price=item_data.price,
            is_active=item_data.is_active
        )
        
        # 3. Create the Initial Inventory Record
        inventory = await Inventory.create(
            menu_item=menu_item,
            available_qty=item_data.initial_qty,
            threshold_qty=item_data.threshold_qty
        )

        return {
            "message": f"Successfully added '{item_data.name}' to {restaurant.name}.",
            "menu_item_id": str(menu_item.id),
            "initial_stock": inventory.available_qty
        }

    except HTTPException:
        # Re-raise explicit HTTP exceptions (like 404)
        raise
    except Exception as e:
        log.error(f"Error adding inventory item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing request: {e}"
        )

@router.post("/add/restaurant", status_code=status.HTTP_201_CREATED)
async def add_restaurant(restaurant_data: RestaurantRequest):
    """
    Creates a new restaurant record.
    """
    try:
        restaurant = await Restaurant.create(
            name=restaurant_data.name,
            is_active=restaurant_data.is_active
        )
        return {
            "message": f"Restaurant '{restaurant.name}' created successfully.",
            "restaurant_id": str(restaurant.id)
        }
    except Exception as e:
        log.error(f"Error creating restaurant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing request: {e}"
        )