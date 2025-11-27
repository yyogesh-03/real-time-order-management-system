from tortoise import fields, models
import uuid


class OutboxEvent(models.Model):
    """
    The Outbox table stores events atomically with the database transaction.
    This is the core of the Transactional Outbox Pattern.
    """
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    aggregate_type = fields.CharField(max_length=64) # e.g., 'order', 'restaurant'
    aggregate_id = fields.UUIDField(null=True) # ID of the entity that generated the event
    event_type = fields.CharField(max_length=128) # e.g., 'order.placed.v1'
    payload = fields.JSONField() # The actual event data
    published = fields.BooleanField(default=False)
    attempts = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "outbox_events"