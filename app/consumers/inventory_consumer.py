import asyncio
from tortoise.transactions import in_transaction
from app.models.inventory import Inventory
from app.models.processed_event import ProcessedEvent
from app.events.outbox_utility import create_outbox_event
from typing import Dict, Any
from uuid import UUID

async def check_for_low_stock(inventory: Inventory, order_id: UUID, conn: Any):
    """Checks if current stock is below threshold and emits an alert if so."""
    if inventory.available_qty <= inventory.threshold_qty:
        print(f"ALERT: Low stock detected for Item {inventory.menu_item_id}! Qty: {inventory.available_qty}")
        # Emit a low stock event (e.g., for notification service)
        await create_outbox_event(
            aggregate_type="inventory", 
            aggregate_id=inventory.id,
            event_type="inventory.low_stock_alert.v1",
            payload={
                "menu_item_id": str(inventory.menu_item_id),
                "available_qty": inventory.available_qty,
                "threshold": inventory.threshold_qty,
                "triggered_by_order_id": str(order_id)
            },
            conn=conn
        )


async def handle_order_placed(event_payload: Dict[str, Any], event_id: UUID):
    """
    Consumer logic for 'order.placed.v1'. Attempts to deduct inventory.
    (Slow Path: Ensures ACID compliance with row locking).
    """
    order_id = UUID(event_payload.get("order_id"))
    items = event_payload.get("items", [])
    event_id_str = str(event_id)
    
    print(f"\n--- Worker: DEDUCTING for Order {order_id} ---")

    try:
        # Idempotency Check
        if await ProcessedEvent.filter(event_id=event_id_str).exists():
            return

        async with in_transaction() as conn:
            menu_item_ids = [UUID(item["menu_item_id"]) for item in items]
            
            # CRITICAL: Lock rows for atomicity and consistency
            # This prevents two concurrent consumers from reading the same stock level
            # before writing the updated level.
            
            locked_inventories = await Inventory.filter(menu_item_id__in=menu_item_ids).using_db(conn).select_for_update()
            inv_map = {str(inv.menu_item_id): inv for inv in locked_inventories}
            
            for item in items:
                mid = item["menu_item_id"]
                qty = item["quantity"]
                inv = inv_map.get(mid)
                
                # Check for item existence and quantity
                if not inv or inv.available_qty < qty:
                    raise ValueError(f"Insufficient inventory: {mid}. Requested: {qty}, Available: {inv.available_qty if inv else 0}")
                
                inv.available_qty -= qty
                await inv.save(update_fields=['available_qty', 'updated_at'], using_db=conn)
                await check_for_low_stock(inv, order_id, conn)

            await ProcessedEvent.create(event_id=event_id_str, using_db=conn)
            
            # Emit Success Event
            await create_outbox_event(
                aggregate_type="order", aggregate_id=order_id,
                event_type="inventory.deducted.success.v1", payload={"order_id": str(order_id)},
                conn=conn
            )
            print(f"SUCCESS: Inventory deducted for Order {order_id}")

    except Exception as e:
        # Emit Failure Event (requires order cancellation)
        await create_outbox_event(
            aggregate_type="order", aggregate_id=order_id,
            event_type="order.cancellation.required.v1", payload={"order_id": str(order_id), "reason": str(e)},
        )
        print(f"FAILURE: Inventory deduction failed for Order {order_id}. Reason: {e}")

async def handle_order_cancelled(event_payload: Dict[str, Any], event_id: UUID):
    """
    Consumer logic for 'order.cancelled.v1'. Restores inventory.
    (Slow Path: Ensures ACID compliance with row locking).
    """
    order_id = UUID(event_payload.get("order_id"))
    items = event_payload.get("items", [])
    event_id_str = str(event_id)

    print(f"\n--- Worker: RESTORING for Order {order_id} ---")

    try:
        # Idempotency Check
        if await ProcessedEvent.filter(event_id=event_id_str).exists():
            return

        async with in_transaction() as conn:
            menu_item_ids = [UUID(item["menu_item_id"]) for item in items]
            
            # CRITICAL: Lock rows to ensure consistent increment
            locked_inventories = await Inventory.filter(menu_item_id__in=menu_item_ids).using_db(conn).select_for_update()
            inv_map = {str(inv.menu_item_id): inv for inv in locked_inventories}

            for item in items:
                mid = item["menu_item_id"]
                qty = item["quantity"]
                inv = inv_map.get(mid)
                if inv:
                    inv.available_qty += qty
                    await inv.save(update_fields=['available_qty', 'updated_at'], using_db=conn)

            await ProcessedEvent.create(event_id=event_id_str, using_db=conn)
            print(f"SUCCESS: Inventory restored for Order {order_id}")

    except Exception as e:
        print(f"CRITICAL ERROR: Failed to restore inventory for {order_id}: {e}")