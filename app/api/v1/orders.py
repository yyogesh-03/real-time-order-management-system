import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.response import SuccessResponse
from app.services.order_service import place_order, get_order_by_id, update_order_status, cancel_order
from app.models.order import OrderStatus
from app.schemas.order import OrderRequest, OrderPlacementResponse, OrderStatusUpdate, OrderDetailResponse
from typing import Dict, Any
from uuid import UUID

router = APIRouter()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("uvicorn")


@router.post("/", status_code=status.HTTP_202_ACCEPTED, response_model=SuccessResponse)
async def create_order_endpoint(request_data: OrderRequest, user_id: str = "user-12345"):
    """
    Places a new order. Returns 202 Accepted because inventory check is async.
    """
    try:
        # We must explicitly convert UUIDs to strings before passing them to the service layer 
        # that handles event serialization (which usually expects strings for JSON/database storage).
        items_data = [
            {
                "menu_item_id": str(item.menu_item_id),
                "quantity": item.quantity
            }
            for item in request_data.items
        ]
        
        if not items_data:
            raise HTTPException(status_code=400, detail="Order must contain items.")

        order = await place_order(
            user_id=user_id,
            restaurant_id=str(request_data.restaurant_id),
            items=items_data
        )
        log.info(f"Order {order.id} placed successfully for user {user_id}.")
        data=OrderPlacementResponse(
            order_id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            message="Order Accepted and is being processed."
        ).model_dump()
        return SuccessResponse(data=data)
    except ValueError as e:
        log.error(f"Value error placing order: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as he:
        log.error(f"HTTP error placing order: {he.detail}")
        raise he
    except Exception as e:
        log.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail="Server failed to place order.")


@router.get("/{order_id}", response_model=SuccessResponse)
async def get_order_endpoint(order_id: UUID):
    """Fetches details for a specific order."""
    try:
        
        order = await get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Prepare items data for clean output using the response schema
        items = [
            {
                "name": i.menu_item.name, 
                "quantity": i.quantity, 
                "price": str(i.unit_price)
            } 
            for i in order.items
        ]
        
        data=OrderDetailResponse(
            id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            items=items,
            created_at=str(order.created_at)
        ).model_dump()
        return SuccessResponse(data=data)
    except Exception as e:
        log.error(f"Error fetching order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Server failed to fetch order details.")


@router.patch("/{order_id}/status", response_model=SuccessResponse)
async def update_status_endpoint(order_id: UUID, payload: OrderStatusUpdate):
    """
    Updates status (e.g. 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED').
    """
    try:
        # Pydantic ensures payload.status is a valid OrderStatus Enum value
        order = await update_order_status(order_id, payload.status)
        data=OrderPlacementResponse(
            order_id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            message=f"Order status successfully updated to {order.status}"
        ).model_dump()
        return SuccessResponse(data=data)
    except ValueError as e:
        log.error(f"Value error updating order status: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error updating order status: {e}")
        raise HTTPException(status_code=500, detail="Server failed to update order status.")

@router.post("/{order_id}/cancel", response_model=SuccessResponse)
async def cancel_order_endpoint(order_id: UUID):
    """
    Cancels the order, updates status to CANCELLED, and triggers async inventory restoration.
    """
    try:
        order = await cancel_order(order_id)
        data=OrderPlacementResponse(
            order_id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            message="Order cancelled. Inventory restoration queued."
        )
        return SuccessResponse(data=data)
    except ValueError as e:
        log.error(f"Value error cancelling order: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Error cancelling order: {e}")
        raise HTTPException(status_code=500, detail="Server failed to cancel order.")