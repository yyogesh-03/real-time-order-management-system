import asyncio
import logging
from tortoise.transactions import in_transaction
from app.models.order import Order, OrderStatus
from app.models.processed_event import ProcessedEvent
from app.events.outbox_utility import create_outbox_event
from typing import Dict, Any
from uuid import UUID

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("order_status_consumer")

async def handle_inventory_success(event_payload: Dict[str, Any], event_id: UUID):
    """
    Consumer logic for 'inventory.deducted.success.v1'. 
    Moves the Order status from PLACED to PREPARING.
    """
    order_id = UUID(event_payload.get("order_id"))
    event_id_str = str(event_id)

    log.info(f"\n--- Worker: UPDATING STATUS for Order {order_id} to PREPARING ---")
    
    try:
        # Idempotency Check
        if await ProcessedEvent.filter(event_id=event_id_str).exists():
            log.info(f"Idempotency: Event {event_id_str} already processed.")
            return

        async with in_transaction() as conn:
            order = await Order.get_or_none(id=order_id).using_db(conn)
            if not order:
                log.info(f"Order {order_id} not found.")
                return

            # Only update if still in the initial PLACED state
            if order.status == OrderStatus.PLACED:
                order.status = OrderStatus.PREPARING
                await order.save(update_fields=['status', 'updated_at'], using_db=conn)
                log.info(f"Status UPDATE: Order {order_id} moved to PREPARING.")
                
            await ProcessedEvent.create(event_id=event_id_str, using_db=conn)
            log.info(f"Event {event_id_str} marked as processed.")
    except Exception as e:
        log.error(f"Error handling Inventory Success for Order {order_id}: {e}")

async def handle_cancellation_required(event_payload: Dict[str, Any], event_id: UUID):
    """
    Consumer logic for 'order.cancellation.required.v1' (triggered by inventory failure).
    Moves the Order status to CANCELLED.
    """
    order_id = UUID(event_payload.get("order_id"))
    event_id_str = str(event_id)
    reason = event_payload.get("reason", "Inventory check failed.")
    log.info(f"\n--- Worker: CANCELLING Order {order_id} ---")
    
    try:
        # Idempotency Check
        if await ProcessedEvent.filter(event_id=event_id_str).exists():
            log.info(f"Idempotency: Event {event_id_str} already processed.")
            return

        async with in_transaction() as conn:
            order = await Order.get_or_none(id=order_id).using_db(conn)
            if not order:
                log.error(f"Order {order_id} not found.")
                return
            
            # Only update if the order isn't already finalized or cancelled
            if order.status in [OrderStatus.PLACED, OrderStatus.PREPARING]:
                order.status = OrderStatus.CANCELLED
                await order.save(update_fields=['status', 'updated_at'], using_db=conn)
                log.error(f"Status UPDATE: Order {order_id} automatically CANCELLED due to: {reason}")
                
            await ProcessedEvent.create(event_id=event_id_str, using_db=conn)
            
    except Exception as e:
        log.error(f"Error handling Cancellation for Order {order_id}: {e}")