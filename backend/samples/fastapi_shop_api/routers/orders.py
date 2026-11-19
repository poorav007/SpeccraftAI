"""Orders fulfillment API routes."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from models.schemas import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=List[OrderResponse], summary="List Orders")
def list_orders(skip: int = 0, limit: int = 50):
    """Retrieve recent customer orders."""
    return []


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create New Order")
def create_order(payload: OrderCreate):
    """Place a new order with selected line items."""
    return {
        "order_id": "ord-12345",
        "customer_email": payload.customer_email,
        "status": "pending",
        "total_amount": sum(item.unit_price * item.quantity for item in payload.items),
        "items_count": len(payload.items),
    }


@router.get("/{order_id}", response_model=OrderResponse, summary="Get Order Details")
def get_order(order_id: str):
    """Fetch order status and tracking information."""
    if not order_id.startswith("ord-"):
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": order_id,
        "customer_email": "customer@example.com",
        "status": "paid",
        "total_amount": 99.50,
        "items_count": 2,
    }

