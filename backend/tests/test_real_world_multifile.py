"""Battle-test suites modeling real-world multi-file FastAPI and Express.js repos."""

from pathlib import Path

from speccraft.route_extractor import RouteExtractor


def test_real_world_3_level_nested_fastapi_routers(tmp_path: Path):
    """Test app.include_router -> api_v1.include_router -> items.router prefix composition."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "api").mkdir()
    (tmp_path / "app" / "api" / "v1").mkdir()
    (tmp_path / "app" / "api" / "v1" / "endpoints").mkdir()

    (tmp_path / "app" / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "from app.api.v1.router import api_router\n"
        "app = FastAPI()\n"
        'app.include_router(api_router, prefix="/api/v1")\n',
        encoding="utf-8",
    )
    (tmp_path / "app" / "api" / "v1" / "router.py").write_text(
        "from fastapi import APIRouter\n"
        "from .endpoints import items\n"
        "api_router = APIRouter()\n"
        'api_router.include_router(items.router, prefix="/items", tags=["catalog"])\n',
        encoding="utf-8",
    )
    (tmp_path / "app" / "api" / "v1" / "endpoints" / "items.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        '@router.get("/{item_id}")\n'
        "def read_item(item_id: int):\n"
        "    return {'id': item_id}\n",
        encoding="utf-8",
    )

    res = RouteExtractor().extract_from_path(tmp_path)
    paths = [(ep.method.value, ep.path, ep.tags) for ep in res.endpoints]
    assert ("get", "/api/v1/items/{item_id}", ["catalog"]) in paths


def test_real_world_cross_file_pydantic_inheritance_reverse_parse_order(tmp_path: Path):
    """Subclasses parsed before parent BaseModel files still inherit all fields cleanly."""
    # a_routes.py sorted alphabetically BEFORE z_models.py
    (tmp_path / "a_routes.py").write_text(
        "from fastapi import FastAPI\n"
        "from pydantic import BaseModel\n"
        "from z_models import ItemBase\n"
        "app = FastAPI()\n"
        "class ItemCreate(ItemBase):\n"
        "    pass\n"
        '@app.post("/items")\n'
        "def create_item(payload: ItemCreate):\n"
        "    return payload\n",
        encoding="utf-8",
    )
    (tmp_path / "z_models.py").write_text(
        "from pydantic import BaseModel\n"
        "class ItemBase(BaseModel):\n"
        "    name: str\n"
        "    price: float\n",
        encoding="utf-8",
    )

    res = RouteExtractor().extract_from_path(tmp_path)
    item_create = res.schemas["ItemCreate"]
    assert "name" in item_create["properties"]
    assert "price" in item_create["properties"]
    assert set(["name", "price"]).issubset(set(item_create["required"]))


def test_real_world_aliased_fastapi_router_import(tmp_path: Path):
    """Supports `from pkg.endpoints.users import router as users_ep_router`."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "users.py").write_text(
        "from fastapi import APIRouter\n"
        'router = APIRouter(prefix="/users")\n'
        '@router.get("/me")\n'
        "def current_user(): return {}\n",
        encoding="utf-8",
    )
    (tmp_path / "server.py").write_text(
        "from fastapi import FastAPI\n"
        "from pkg.users import router as users_ep_router\n"
        "app = FastAPI()\n"
        'app.include_router(users_ep_router, prefix="/v2", tags=["auth"])\n',
        encoding="utf-8",
    )

    res = RouteExtractor().extract_from_path(tmp_path)
    assert any(ep.path == "/v2/users/me" and "auth" in ep.tags for ep in res.endpoints)


def test_real_world_multifile_express_nested_subrouters(tmp_path: Path):
    """Test Express app.js -> routes/api.js -> routes/orders.js cross-file mounts."""
    (tmp_path / "routes").mkdir()
    (tmp_path / "app.js").write_text(
        'const express = require("express");\n'
        'const apiRouter = require("./routes/api");\n'
        "const app = express();\n"
        'app.use("/api/v1", apiRouter);\n',
        encoding="utf-8",
    )
    (tmp_path / "routes" / "api.js").write_text(
        'import ordersRouter from "./orders";\n'
        'const express = require("express");\n'
        "const router = express.Router();\n"
        'router.use("/orders", ordersRouter);\n'
        "module.exports = router;\n",
        encoding="utf-8",
    )
    (tmp_path / "routes" / "orders.js").write_text(
        'const express = require("express");\n'
        "const router = express.Router();\n"
        "/** Fetch one order by ID */\n"
        'router.get("/:order_id", (req, res) => res.json({}));\n'
        "module.exports = router;\n",
        encoding="utf-8",
    )

    res = RouteExtractor().extract_from_path(tmp_path)
    ep = next(e for e in res.endpoints if e.path == "/api/v1/orders/{order_id}")
    assert ep.method.value == "get"
    assert ep.summary == "Fetch one order by ID"
    assert ep.parameters[0].name == "order_id"


def test_real_world_missing_external_router_import_does_not_crash(tmp_path: Path):
    """Gracefully handles third-party or missing router imports without crashing."""
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "from non_existent_pkg import ext_router\n"
        "app = FastAPI()\n"
        'app.include_router(ext_router, prefix="/ext")\n'
        '@app.get("/alive")\n'
        "def alive(): return {'ok': True}\n",
        encoding="utf-8",
    )
    res = RouteExtractor().extract_from_path(tmp_path)
    assert any(ep.path == "/alive" for ep in res.endpoints)

