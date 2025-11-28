# app/models/__init__.py
from .inventory import Inventory
from .order import Order, OrderItem, OrderStatus,Restaurant, MenuItem
from .outbox import OutboxEvent
from .processed_event import ProcessedEvent

# Export all models
__all__ = [
    "Inventory",
    "Order", 
    "OrderItem",
    "OrderStatus",
    "OutboxEvent", 
    "ProcessedEvent",
    "Restaurant",
    "MenuItem"
]