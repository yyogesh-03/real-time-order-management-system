from enum import Enum
from tortoise import fields, models
import uuid


class OrderStatus(str, Enum):
    PLACED = "PLACED"  # Initial state, waiting for inventory check (Fast Path Success)
    PREPARING = "PREPARING" # Inventory check success (Slow Path Success)
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Restaurant(models.Model):
    id = fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    
    class Meta:
        table = "restaurants"
        indexes = [
            ("is_active",),  # For filtering active restaurants
        ]


class MenuItem(models.Model):
    id = fields.UUIDField(primary_key=True)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="menu_items")
    name = fields.CharField(max_length=255)
    price = fields.DecimalField(max_digits=12, decimal_places=2)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "menu_items"
        indexes = [
            ("restaurant_id",),  # Fast restaurant menu queries
            ("is_active",),      # Filter active items
            ("restaurant_id", "is_active"),  # Composite: restaurant's active items
        ]


class Order(models.Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(max_length=64)
    restaurant = fields.ForeignKeyField("models.Restaurant", related_name="orders")
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.PLACED)
    total_amount = fields.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "orders"
        indexes = [
            ("restaurant_id",),          # Restaurant order queries
            ("status",),                 # Status-based filtering
            ("user_id",),                # User order history
            ("created_at",),             # Time-based queries
            ("updated_at",),             # Recent updates
            ("status", "created_at"),    # Composite: status with time
        ]


class OrderItem(models.Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    order = fields.ForeignKeyField("models.Order", related_name="items")
    menu_item = fields.ForeignKeyField("models.MenuItem", related_name="order_items")
    quantity = fields.IntField()
    unit_price = fields.DecimalField(max_digits=12, decimal_places=2)
    line_total = fields.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        table = "order_items"
        indexes = [
            ("order_id",),              # Order line items
            ("menu_item_id",),          # Menu item popularity
            ("order_id", "menu_item_id"),  # Composite: order+item lookup
        ]