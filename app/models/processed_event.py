from tortoise import fields, models
import uuid


class ProcessedEvent(models.Model):
    """
    Table used for Idempotency in Consumers. Stores the UUID of an OutboxEvent 
    to ensure it's processed only once by any consumer.
    """
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    event_id = fields.CharField(max_length=128, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "processed_events"