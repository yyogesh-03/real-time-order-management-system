# scripts/seed_data.py
import asyncio
from tortoise import Tortoise
from app.core.db import DB_URL
from app.models.order import Restaurant, MenuItem
from app.models.inventory import Inventory

async def init():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["app.models.order", "app.models.inventory", "app.models.outbox", "app.models.processed_event"]})
    # don't generate schemas here (already created), but safe to call in dev:
    # await Tortoise.generate_schemas()

async def seed():
    # Create one restaurant
    rest, _ = await Restaurant.get_or_create(name="Demo Restaurant")
    print("Restaurant:", rest.id)

    # Create menu items
    m1, _ = await MenuItem.get_or_create(restaurant=rest, name="Paneer Wrap", defaults={"price": "149.00", "is_active": True})
    m2, _ = await MenuItem.get_or_create(restaurant=rest, name="Chili Paneer Rice", defaults={"price": "199.00", "is_active": True})
    m3, _ = await MenuItem.get_or_create(restaurant=rest, name="Cold Drink", defaults={"price": "49.00", "is_active": True})

    print("Menu items:", str(m1.id), str(m2.id), str(m3.id))

    # Create or update inventory for each menu item
    inv1, _ = await Inventory.get_or_create(menu_item=m1, defaults={"available_qty": 50, "threshold_qty": 5})
    inv2, _ = await Inventory.get_or_create(menu_item=m2, defaults={"available_qty": 30, "threshold_qty": 5})
    inv3, _ = await Inventory.get_or_create(menu_item=m3, defaults={"available_qty": 100, "threshold_qty": 10})

    # If existing, update quantities (idempotent)
    inv1.available_qty = 50
    inv2.available_qty = 30
    inv3.available_qty = 100
    await inv1.save(); await inv2.save(); await inv3.save()

    print("Inventory seeded.")

async def main():
    await init()
    await seed()
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
