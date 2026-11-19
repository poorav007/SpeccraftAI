"""Pydantic schemas for the sample FastAPI shop application."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Lifecycle statuses for a customer order."""
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ItemBase(BaseModel):
    """Base item model with shared attributes."""
    name: str = Field(..., description="Product title or catalog name")
    description: Optional[str] = Field(default=None, description="Detailed product description")
    price: float = Field(..., gt=0.0, description="Product price in USD")
    category: str = Field(default="general", description="Product category for filtering")
    tags: List[str] = Field(default_factory=list, description="Search and categorization tags")


class ItemCreate(ItemBase):
    """Payload required to create a new catalog item."""
    pass


class ItemResponse(ItemBase):
    """Public representation of a catalog item."""
    id: int = Field(..., description="Unique database identifier")
    in_stock: bool = Field(default=True, description="Inventory availability flag")


class OrderItem(BaseModel):
    """Item reference and quantity within an order."""
    item_id: int = Field(..., description="Referenced catalog item ID")
    quantity: int = Field(default=1, ge=1, description="Number of units ordered")
    unit_price: float = Field(..., description="Price per unit at purchase time")


class OrderCreate(BaseModel):
    """Payload to initiate a new checkout order."""
    customer_email: str = Field(..., description="Customer contact email")
    shipping_address: str = Field(..., description="Physical delivery destination")
    items: List[OrderItem] = Field(..., description="List of items in the order")


class OrderResponse(BaseModel):
    """Customer-facing order summary."""
    order_id: str = Field(..., description="Unique order tracking code")
    customer_email: str = Field(..., description="Customer contact email")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Current fulfillment status")
    total_amount: float = Field(..., description="Sum of all ordered items")
    items_count: int = Field(..., description="Total quantity of products")

