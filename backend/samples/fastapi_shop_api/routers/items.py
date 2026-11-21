"""Items catalog API routes."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from models.schemas import ItemCreate, ItemResponse

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=List[ItemResponse], summary="List Catalog Items")
def list_items(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
):
    """Retrieve catalog items with optional category filtering and pagination."""
    return []


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, summary="Create Catalog Item")
def create_item(payload: ItemCreate):
    """Add a new product to the shop inventory."""
    return {
        "id": 1,
        "name": payload.name,
        "description": payload.description,
        "price": payload.price,
        "category": payload.category,
        "tags": payload.tags,
        "in_stock": True,
    }


@router.get("/{item_id}", response_model=ItemResponse, summary="Get Single Item")
def get_item(item_id: int):
    """Fetch item details by unique item ID."""
    if item_id <= 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, "name": "Sample Item", "price": 19.99, "category": "general", "tags": [], "in_stock": True}


@router.put("/{item_id}", response_model=ItemResponse, summary="Update Item")
def update_item(item_id: int, payload: ItemCreate):
    """Update fields of an existing catalog product."""
    return {"id": item_id, "name": payload.name, "price": payload.price, "category": payload.category, "tags": payload.tags, "in_stock": True}


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Item")
def delete_item(item_id: int):
    """Remove a product from inventory permanently."""
    return None

