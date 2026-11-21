"""FastAPI application server for SpecCraft AI.

Exposes REST API endpoints and handles CORS configuration for Vite React frontend.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from speccraft.api.routes import api_router


def create_app() -> FastAPI:
    """Create and configure the SpecCraft AI FastAPI application instance."""
    app = FastAPI(
        title="SpecCraft AI API",
        version="0.1.0",
        description="Automated API documentation & OpenAPI 3.0 specification generator REST API.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS for local frontend clients
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "*",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routes under /api
    app.include_router(api_router, prefix="/api")

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": "SpecCraft AI API",
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs",
            "endpoints": {
                "health": "/api/health",
                "parse": "/api/parse",
                "generate": "/api/generate",
                "validate": "/api/validate",
            },
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("speccraft.api.server:app", host="127.0.0.1", port=8000, reload=True)

