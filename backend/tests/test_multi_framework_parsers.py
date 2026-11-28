"""Tests for Flask and Express.js static AST/route adapters (zero code execution)."""

from pathlib import Path

from speccraft.route_extractor import RouteExtractor


def test_flask_static_ast_extraction_with_blueprint_and_converters(tmp_path: Path):
    flask_file = tmp_path / "flask_app.py"
    flask_file.write_text(
        '''
from flask import Blueprint, Flask

app = Flask(__name__)
orders_bp = Blueprint("orders_bp", __name__, url_prefix="/api/v1")

@app.route("/health", methods=["GET"])
def health():
    """Service health endpoint."""
    return {"status": "ok"}

@orders_bp.post("/orders/<int:order_id>")
def update_order(order_id):
    return {"id": order_id}
''',
        encoding="utf-8",
    )

    res = RouteExtractor().extract_from_path(tmp_path)
    assert [d for d in res.diagnostics if d.code.value == "SC-E001"] == []
    paths = {(ep.method.value, ep.path): ep for ep in res.endpoints}

    assert ("get", "/health") in paths
    assert paths[("get", "/health")].summary == "Service health endpoint."

    assert ("post", "/api/v1/orders/{order_id}") in paths
    ep = paths[("post", "/api/v1/orders/{order_id}")]
    assert ep.parameters[0].name == "order_id"
    assert ep.parameters[0].param_type == "integer"


def test_express_static_route_extraction_without_execution(tmp_path: Path):
    index_js = tmp_path / "app.js"
    index_js.write_text(
        '''
const express = require("express");
const app = express();
const usersRouter = express.Router();

app.use("/api/users", usersRouter);

/** Fetch single user by ID */
usersRouter.get("/:user_id", (req, res) => {
  res.json({ id: req.params.user_id });
});

// Create user account
app.post("/register", (req, res) => {
  res.status(201).json({});
});
''',
        encoding="utf-8",
    )

    res = RouteExtractor().extract_from_path(tmp_path)
    assert [d for d in res.diagnostics if d.code.value == "SC-E001"] == []
    paths = {(ep.method.value, ep.path): ep for ep in res.endpoints}

    assert ("get", "/api/users/{user_id}") in paths
    get_user = paths[("get", "/api/users/{user_id}")]
    assert get_user.summary == "Fetch single user by ID"
    assert get_user.parameters[0].name == "user_id"

    assert ("post", "/register") in paths
    assert paths[("post", "/register")].summary == "Create user account"

