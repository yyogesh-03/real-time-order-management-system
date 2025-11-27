from fastapi import APIRouter, HTTPException, status
from app.models.inventory import Inventory
from app.models.order import MenuItem, Restaurant
from app.schemas.inventory import InventoryResponse
from uuid import UUID
from typing import Dict, Any

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
        # Catches other potential DB/Tortoise errors
        print(f"Error fetching inventory: {e}")
        raise HTTPException(status_code=500, detail="Server failed to fetch inventory.")


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_initial_data():
    """Seeds the database with initial Restaurant, Menu, and Inventory data for testing."""
    try:
        restaurant_id = UUID("729d4791-c9f2-411a-826c-949479b12270")
        item1_id = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11") # High Stock
        item2_id = UUID("b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a12") # Low Stock (triggers alert logic)
        
        # 1. Create/Update Restaurant
        await Restaurant.update_or_create(
            id=restaurant_id, 
            defaults={"name": "The Great Biryani Spot", "is_active": True}
        )
        
        # 2. Create/Update Menu Items
        await MenuItem.update_or_create(
            id=item1_id, 
            defaults={"restaurant_id": restaurant_id, "name": "Chicken Biryani", "price": 450.00, "is_active": True}
        )
        await MenuItem.update_or_create(
            id=item2_id, 
            defaults={"restaurant_id": restaurant_id, "name": "Veg Thali", "price": 300.00, "is_active": True}
        )
        
        # 3. Create/Update Inventory
        await Inventory.update_or_create(
            menu_item_id=item1_id, 
            defaults={"available_qty": 100, "threshold_qty": 10}
        )
        await Inventory.update_or_create(
            menu_item_id=item2_id, 
            defaults={"available_qty": 5, "threshold_qty": 10} # Initial low stock
        )
        
        return {"message": "Database successfully seeded. Use the following IDs for testing:",
                "restaurant_id": str(restaurant_id),
                "chicken_biryani_id": str(item1_id),
                "veg_thali_id": str(item2_id),
                "notes": "Veg Thali (item2) is initially low stock (5 available)."
                }
    except Exception as e:
        print(f"Error seeding data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to seed data: {e}")