from fastapi import APIRouter, HTTPException, status
from app.services.order_service import place_order, get_order_by_id, update_order_status, cancel_order
from app.models.order import OrderStatus
from app.schemas.order import OrderRequest, OrderPlacementResponse, OrderStatusUpdate, OrderDetailResponse
from typing import Dict, Any
from uuid import UUID

router = APIRouter()


@router.post("/", status_code=status.HTTP_202_ACCEPTED, response_model=OrderPlacementResponse)
async def create_order_endpoint(request_data: OrderRequest, user_id: str = "user-12345"):
    """
    Places a new order. Returns 202 Accepted because inventory check is async.
    (Fast Path - ensures <200ms latency)
    """
    try:
        # We must explicitly convert UUIDs to strings before passing them to the service layer 
        # that handles event serialization (which usually expects strings for JSON/database storage).
        items_data = [
            {
                "menu_item_id": str(item.menu_item_id),  # <-- FIX: Cast UUID to string
                "quantity": item.quantity
            }
            for item in request_data.items
        ]
        
        if not items_data:
            raise HTTPException(status_code=400, detail="Order must contain items.")

        order = await place_order(
            user_id=user_id,
            restaurant_id=str(request_data.restaurant_id), # <-- FIX: Cast UUID to string
            items=items_data
        )
        
        # FastAPI handles automatic conversion of Order model fields to OrderPlacementResponse fields
        return OrderPlacementResponse(
            order_id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            message="Order accepted. Processing inventory in background (Fast Path completed)."
        )
    except ValueError as e:
        # Handles business logic errors raised by place_order (e.g., insufficient stock)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error for debugging purposes
        # This will catch the 'UUID' object has no attribute 'replace' error if place_order raises it
        print(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail="Server failed to place order.")


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_endpoint(order_id: UUID):
    """Fetches details for a specific order."""
    try:
        # ... (rest of the function is unchanged)
        order = await get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Prepare items data for clean output using the response schema
        items = [
            {
                "name": i.menu_item.name, 
                "quantity": i.quantity, 
                "price": str(i.unit_price) # Convert Decimal to string for clean JSON
            } 
            for i in order.items
        ]
        
        return OrderDetailResponse(
            id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            items=items,
            created_at=str(order.created_at)
        )
    except Exception as e:
        # If order_id is not a valid UUID, FastAPI's path converter handles the 422 error automatically.
        raise HTTPException(status_code=500, detail="Server failed to fetch order details.")


@router.patch("/{order_id}/status", response_model=OrderPlacementResponse)
async def update_status_endpoint(order_id: UUID, payload: OrderStatusUpdate):
    """
    Updates status (e.g. 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED').
    """
    try:
        # Pydantic ensures payload.status is a valid OrderStatus Enum value
        order = await update_order_status(order_id, payload.status)
        return OrderPlacementResponse(
            order_id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            message=f"Order status successfully updated to {order.status}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{order_id}/cancel", response_model=OrderPlacementResponse)
async def cancel_order_endpoint(order_id: UUID):
    """
    Cancels the order, updates status to CANCELLED, and triggers async inventory restoration.
    """
    try:
        order = await cancel_order(order_id)
        return OrderPlacementResponse(
            order_id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            message="Order cancelled. Inventory restoration queued."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))