from typing import Dict, Any
from app.models.outbox import OutboxEvent
from uuid import UUID
from tortoise.exceptions import DoesNotExist

async def create_outbox_event(
    aggregate_type: str,
    aggregate_id: UUID,
    event_type: str,
    payload: Dict[str, Any],
    conn: Any = None
) -> None:
    """
    Creates a new Outbox event record using the provided database connection (transaction).
    
    CRITICAL: Passing 'conn' ensures the event is created atomically with the business data.
    """
    await OutboxEvent.create(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
        published=False,
        attempts=0,
        using_db=conn 
    )