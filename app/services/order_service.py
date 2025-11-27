from tortoise.transactions import in_transaction
from typing import List, Dict, Optional
from decimal import Decimal
from app.models.order import Order, OrderItem, MenuItem, Restaurant, OrderStatus 
from app.events.outbox_utility import create_outbox_event
from uuid import UUID

async def place_order(user_id: str, restaurant_id: UUID, items: List[Dict]) -> Order:
    """
    FAST PATH: Creates Order/OrderItem and the OutboxEvent atomically.
    Delegates slow, complex work (Inventory deduction) to the consumer/worker.
    """
    async with in_transaction() as conn:
        # Input validation and existence check
        menu_item_ids = [UUID(it["menu_item_id"]) for it in items]
        menu_items = await MenuItem.filter(id__in=menu_item_ids, restaurant_id=restaurant_id, is_active=True).using_db(conn)
        menu_map = {str(m.id): m for m in menu_items}
        
        restaurant = await Restaurant.get_or_none(id=restaurant_id).using_db(conn)
        if not restaurant or not restaurant.is_active:
             raise ValueError("Restaurant not found or is inactive.")

        # 1. Create the Order header
        order = await Order.create(
            user_id=user_id, 
            restaurant=restaurant, 
            status=OrderStatus.PLACED, 
            total_amount=Decimal("0"), 
            using_db=conn
        )

        total = Decimal("0")
        event_items_payload = [] 

        for it in items:
            mid_str = str(it["menu_item_id"]) # Ensure UUID is converted to string for key lookup
            qty = int(it["quantity"])
            menu = menu_map.get(mid_str)

            if not menu:
                raise ValueError(f"Menu item {mid_str} not found or inactive.")
            
            line_total = (menu.price * qty)
            total += line_total

            # 2. Create Order Item line
            await OrderItem.create(
                order=order, 
                menu_item=menu, 
                quantity=qty, 
                unit_price=menu.price, 
                line_total=line_total, 
                using_db=conn
            )
            
            event_items_payload.append({"menu_item_id": mid_str, "quantity": qty})

        order.total_amount = total
        await order.save(using_db=conn)

        # 3. ATOMIC EVENT: Trigger Inventory Deduction (handled by consumer)
        await create_outbox_event(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.placed.v1",
            payload={
                "order_id": str(order.id),
                "restaurant_id": str(restaurant_id),
                "items": event_items_payload,
            },
            conn=conn
        )

    return order

async def get_order_by_id(order_id: UUID) -> Optional[Order]:
    """Fetches order details with items, including the menu item name/price."""
    # Pre-fetch related entities to minimize DB queries (N+1 avoidance)
    return await Order.get_or_none(id=order_id).prefetch_related('items', 'items__menu_item')

async def update_order_status(order_id: UUID, new_status: OrderStatus) -> Order:
    """
    Updates order status, enforces state machine rules, and emits specific events.
    """
    # Use the Tortoise in_transaction context manager for atomicity
    async with in_transaction() as conn:
        # Fetch order and prefetch items in case we need to cancel (compensation event)
        order = await Order.get_or_none(id=order_id).prefetch_related('items').using_db(conn)
        
        if not order:
            raise ValueError("Order not found")
        
        # --- 1. CRITICAL STATE MACHINE VALIDATION ---
        # Block status updates if the order is in a final, irreversible state.
        if order.status in [OrderStatus.CANCELLED, OrderStatus.DELIVERED]:
            # This prevents invalid transitions like CANCELLED -> OUT_FOR_DELIVERY 
            raise ValueError(f"Order is already in a final state: {order.status}. Status cannot be updated.")
            
        old_status = order.status
        order.status = new_status
        await order.save(using_db=conn) # Save the status update

        # --- 2. DYNAMIC EVENT EMISSION & COMPENSATION LOGIC ---
        
        # Default event type based on status (e.g., order.status.preparing.v1)
        event_type = f"order.status.{new_status.value.lower()}.v1"
        
        payload = {
            "order_id": str(order.id),
            "old_status": old_status,
            "new_status": new_status.value,
            "user_id": order.user_id,
        }

        # If the new status is CANCELLED, switch to the specific compensation event
        if new_status == OrderStatus.CANCELLED:
            event_type = "order.cancelled.v1" 
            # Items must be fetched for the payload (handled by prefetch_related above)
            payload["items"] = [
                {"menu_item_id": str(item.menu_item_id), "quantity": item.quantity} 
                for item in order.items
            ]

        # ATOMIC EVENT EMISSION
        # This insertion happens in the same DB transaction as the order.save()
        await create_outbox_event(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type=event_type,
            payload=payload,
            conn=conn
        )
        
    return order


async def cancel_order(order_id: UUID) -> Order:
    """
    Cancels an order and triggers an event to restore inventory.
    """
    async with in_transaction() as conn:
        # Prefetch items so we know what to restore
        order = await Order.get_or_none(id=order_id).prefetch_related('items').using_db(conn)
        if not order:
            raise ValueError("Order not found")

        # Validation: Cannot cancel if already completed or out for delivery
        if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.OUT_FOR_DELIVERY]:
            raise ValueError(f"Cannot cancel order in status {order.status}")

        order.status = OrderStatus.CANCELLED
        await order.save(using_db=conn)

        # Prepare payload for inventory restoration based on order items
        items_payload = [
            {"menu_item_id": str(item.menu_item_id), "quantity": item.quantity}
            for item in order.items
        ]

        # ATOMIC EVENT: Trigger Inventory Restoration (handled by consumer)
        await create_outbox_event(
            aggregate_type="order",
            aggregate_id=order.id,
            event_type="order.cancelled.v1",
            payload={
                "order_id": str(order.id),
                "items": items_payload
            },
            conn=conn
        )
    return order