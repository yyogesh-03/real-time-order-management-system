from pydantic import BaseModel, Field
from typing import Any, Optional
import uuid
from datetime import datetime

def _rid():
    return uuid.uuid4().hex

class SuccessResponse(BaseModel):
    """Simple success response wrapper with just data, success, and request_id"""
    success: Optional[bool] = Field(default=True)
    request_id: str = Field(default_factory=_rid)
    data: Optional[Any] = None