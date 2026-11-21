from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/items")
def list_items():
    return []

@app.post("/items", status_code=201)
def create_item(payload: Item):
    return payload

@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"id": item_id}

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    return {"deleted": True}

