from tortoise import fields, models
import uuid


class Inventory(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    # One-to-one link to ensure a single inventory record per menu item
    menu_item = fields.OneToOneField("models.MenuItem", related_name="inventory")
    available_qty = fields.IntField()
    threshold_qty = fields.IntField(default=10) # For low stock alert
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "inventory"