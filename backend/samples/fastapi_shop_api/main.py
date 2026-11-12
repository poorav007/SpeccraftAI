"""FastAPI Sample Shop Application for SpecCraft AI AST Benchmarking."""

from fastapi import FastAPI
from routers.items import router as items_router
from routers.orders import router as orders_router

app = FastAPI(
    title="FastAPI Shop API",
    version="1.0.0",
    description="Sample e-commerce shop backend used for SpecCraft AI AST extraction and OpenAPI generation.",
)

# Mount sub-routers
app.include_router(items_router)
app.include_router(orders_router)


@app.get("/health", tags=["system"], summary="Service Health Check")
def health_check():
    """Returns system status and version info."""
    return {"status": "ok", "service": "fastapi-shop-api", "version": "1.0.0"}

