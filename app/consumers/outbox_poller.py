import asyncio
from app.models.outbox import OutboxEvent
# Import all handler functions
from app.consumers.inventory_consumer import handle_order_placed, handle_order_cancelled
from app.consumers.order_status_consumer import handle_inventory_success, handle_cancellation_required
from app.core.db import init_db
from app.core.config import POLLING_INTERVAL, MAX_ATTEMPTS, BATCH_SIZE
import traceback

async def mock_dispatch_event(event: OutboxEvent):
    """
    Routes an OutboxEvent to the correct business logic handler.
    This simulates a message broker (like Kafka/RabbitMQ) dispatcher.
    """
    event_type = event.event_type
    event_id = event.id
    payload = event.payload
    
    print(f"Poller DISPATCHING: {event_type} (ID: {event_id.hex[:8]}...)")

    # Routing based on event type
    if event_type == "order.placed.v1":
        # Consumer 1: Inventory Deduction
        await handle_order_placed(payload, event_id)
        
    elif event_type == "inventory.deducted.success.v1":
        # Consumer 2: Order Status Update (Placed -> Preparing)
        await handle_inventory_success(payload, event_id)
        
    elif event_type == "order.cancellation.required.v1":
        # Consumer 2: Order Status Update (Auto-Cancellation due to inventory failure)
        await handle_cancellation_required(payload, event_id)

    elif event_type == "order.cancelled.v1":
        # Consumer 1: Inventory Restoration (Manual Cancellation)
        await handle_order_cancelled(payload, event_id)
        
    elif event_type == "order.status_changed.v1":
        # Consumer N: Notification/Analytics/External System (Simulated here)
        print(f"EXTERNAL NOTIFICATION: Order {payload.get('order_id')} status updated to {payload.get('new_status')}")

    elif event_type == "inventory.low_stock_alert.v1":
        # Consumer N: Alerting System (Simulated here)
        print(f"!!! SYSTEM ALERT !!! Item {payload.get('menu_item_id')} has low stock ({payload.get('available_qty')} remaining).")
        
    else:
        print(f"WARNING: No handler found for event type: {event_type}")

async def poll_outbox_for_new_events():
    """
    Queries the Outbox table for unpublished events and attempts to dispatch them.
    """
    # Select events that haven't been published and haven't exceeded max attempts
    events = await OutboxEvent.filter(published=False, attempts__lt=MAX_ATTEMPTS).limit(BATCH_SIZE).order_by('created_at')
    
    if not events:
        return

    for event in events:
        try:
            # 1. Dispatch the event (calls the business logic handler)
            await mock_dispatch_event(event)
            
            # 2. Mark the event as published on success
            event.published = True
            await event.save(update_fields=['published'])

        except Exception:
            # 3. Increment attempts on failure and save
            event.attempts += 1
            await event.save(update_fields=['attempts'])
            traceback.print_exc()
            
async def start_outbox_poller():
    """Main loop for the poller service."""
    await init_db()
    print("--- Outbox Poller Service Started ---")
    
    while True:
        try:
            await poll_outbox_for_new_events()
        except Exception as e:
            print(f"Poller encountered a critical DB error: {e}.")
            
        await asyncio.sleep(POLLING_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(start_outbox_poller())
    except KeyboardInterrupt:
        print("Poller service stopped.")