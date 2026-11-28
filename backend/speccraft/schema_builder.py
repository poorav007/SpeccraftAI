"""Static AST Pydantic schema extractor for SpecCraft AI.

Parses Python AST ClassDef nodes representing Pydantic BaseModel classes,
extracting field types, docstrings, defaults, and requirements without code execution.
Generates OpenAPI 3.0-compliant JSON Schema objects.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional, Set, Tuple


# Mapping of common Python type names to OpenAPI/JSON Schema types
PYTHON_TYPE_MAP: Dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array",
    "bytes": "string",
    "UUID": "string",
    "datetime": "string",
    "date": "string",
    "time": "string",
    "Decimal": "number",
    "Any": "object",
}


def _ast_to_literal(node: Optional[ast.AST]) -> Any:
    """Safely convert a simple AST constant/literal node to Python primitive."""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_ast_to_literal(elt) for elt in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _ast_to_literal(k): _ast_to_literal(v)
            for k, v in zip(node.keys, node.values)
            if k is not None
        }
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
        return -node.operand.value
    return None


class PydanticSchemaExtractor:
    """Extracts JSON Schema representations from AST nodes of Pydantic models."""

    def __init__(self) -> None:
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.known_model_names: Set[str] = set()
        self._class_bases: Dict[str, List[str]] = {}
        self._pending_classes: Dict[str, ast.ClassDef] = {}

    @staticmethod
    def _collect_class_defs(tree: ast.AST) -> List[ast.ClassDef]:
        """Collect ClassDef nodes by walking statement blocks without descending into expressions."""
        classes: List[ast.ClassDef] = []
        stack: List[ast.stmt] = list(getattr(tree, "body", []))
        while stack:
            stmt = stack.pop()
            if isinstance(stmt, ast.ClassDef):
                classes.append(stmt)
                stack.extend(stmt.body)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.With, ast.AsyncWith)):
                stack.extend(stmt.body)
            elif isinstance(stmt, ast.If):
                stack.extend(stmt.body)
                stack.extend(stmt.orelse)
            elif isinstance(stmt, ast.Try) or (hasattr(ast, "TryStar") and isinstance(stmt, ast.TryStar)):
                stack.extend(stmt.body)
                stack.extend(stmt.orelse)
                stack.extend(stmt.finalbody)
                for handler in stmt.handlers:
                    stack.extend(handler.body)
        return classes

    def extract_from_ast(self, tree: ast.AST, finalize: bool = True) -> Dict[str, Dict[str, Any]]:
        """Scan AST tree for ClassDefs inheriting from BaseModel, Schema, or Enum."""
        class_nodes = self._collect_class_defs(tree)

        for node in class_nodes:
            self._pending_classes[node.name] = node
            self._class_bases[node.name] = [
                base.id if isinstance(base, ast.Name) else base.attr
                for base in node.bases
                if isinstance(base, (ast.Name, ast.Attribute))
            ]
            # Defer parsing until finalize_schemas when batching, or parse eagerly below
            if not finalize and (self._is_pydantic_model(node) or self._is_enum(node)):
                self.known_model_names.add(node.name)

        if finalize:
            self.finalize_schemas()

        return self.schemas

    def finalize_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Resolve multi-file model inheritance and materialize all Pydantic/Enum schemas once."""
        changed = True
        while changed:
            changed = False
            for cls_name, node in self._pending_classes.items():
                if cls_name not in self.known_model_names and (
                    self._is_pydantic_model(node) or self._is_enum(node)
                ):
                    self.known_model_names.add(cls_name)
                    changed = True

        for cls_name, node in self._pending_classes.items():
            if cls_name in self.known_model_names and cls_name not in self.schemas:
                self.schemas[cls_name] = (
                    self._parse_enum_class(node)
                    if self._is_enum(node)
                    else self._parse_class_def(node)
                )

        self.finalize_inheritance()
        return self.schemas

    def finalize_inheritance(self) -> None:
        """Merge inherited parent Pydantic schema properties & required fields across files."""
        resolved: Dict[str, Dict[str, Any]] = {}

        def resolve_one(name: str, seen: Set[str]) -> Dict[str, Any]:
            if name in resolved:
                return resolved[name]
            base_schema = dict(self.schemas.get(name) or {})
            if name in seen or base_schema.get("type") != "object":
                return base_schema
            seen_next = seen | {name}

            merged_props: Dict[str, Any] = {}
            merged_req: List[str] = []
            for parent_name in self._class_bases.get(name, []):
                if parent_name in self.schemas and parent_name not in seen_next:
                    parent_resolved = resolve_one(parent_name, seen_next)
                    for k, v in (parent_resolved.get("properties") or {}).items():
                        merged_props[k] = v
                    for req_key in parent_resolved.get("required") or []:
                        if req_key not in merged_req:
                            merged_req.append(req_key)

            for k, v in (base_schema.get("properties") or {}).items():
                merged_props[k] = v
            for req_key in base_schema.get("required") or []:
                if req_key not in merged_req:
                    merged_req.append(req_key)

            base_schema["properties"] = merged_props
            if merged_req:
                base_schema["required"] = merged_req
            resolved[name] = base_schema
            return base_schema

        for schema_name in list(self.schemas.keys()):
            self.schemas[schema_name] = resolve_one(schema_name, set())

    def _is_enum(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from Enum, str+Enum, or IntEnum."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ("Enum", "IntEnum", "StrEnum"):
                return True
            if isinstance(base, ast.Attribute) and base.attr in ("Enum", "IntEnum", "StrEnum"):
                return True
        return False

    def _parse_enum_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Convert a Python Enum class AST node into an OpenAPI JSON Schema object."""
        docstring = ast.get_docstring(node)
        enum_values: List[Any] = []
        is_int = any(
            (isinstance(b, ast.Name) and b.id in ("int", "IntEnum"))
            or (isinstance(b, ast.Attribute) and b.attr == "IntEnum")
            for b in node.bases
        )

        for item in node.body:
            if isinstance(item, ast.Assign) and item.value:
                lit = _ast_to_literal(item.value)
                if lit is not None:
                    enum_values.append(lit)

        enum_type = "integer" if is_int else "string"
        schema: Dict[str, Any] = {
            "title": node.name,
            "type": enum_type,
            "enum": enum_values,
        }
        if docstring:
            schema["description"] = docstring.strip()

        return schema

    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        """Heuristic check if class inherits from BaseModel or has model characteristics."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ("BaseModel", "Schema"):
                return True
            if isinstance(base, ast.Attribute) and base.attr in ("BaseModel", "Schema"):
                return True
            if isinstance(base, ast.Name) and base.id in self.known_model_names:
                return True
        return False

    def _parse_class_def(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Convert a Pydantic ClassDef AST node into an OpenAPI JSON Schema object."""
        docstring = ast.get_docstring(node)
        properties: Dict[str, Any] = {}
        required_fields: List[str] = []

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_schema, is_required = self._parse_field_annotation(item.annotation, item.value)
                properties[field_name] = field_schema
                if is_required:
                    required_fields.append(field_name)

        schema: Dict[str, Any] = {
            "title": node.name,
            "type": "object",
            "properties": properties,
        }
        if docstring:
            schema["description"] = docstring.strip()
        if required_fields:
            schema["required"] = required_fields

        return schema

    def _parse_field_annotation(
        self,
        annotation_node: ast.AST,
        value_node: Optional[ast.AST],
    ) -> Tuple[Dict[str, Any], bool]:
        """Parse field annotation and default value, returning (schema_dict, is_required)."""
        prop_schema, is_optional = self._resolve_type_node(annotation_node)
        is_required = not is_optional

        # Check default value or Field(...) call
        if value_node is not None:
            if isinstance(value_node, ast.Call):
                # e.g. Field(..., description="xyz", default=...)
                call_name = ""
                if isinstance(value_node.func, ast.Name):
                    call_name = value_node.func.id
                elif isinstance(value_node.func, ast.Attribute):
                    call_name = value_node.func.attr

                if call_name == "Field":
                    field_req, field_desc, field_def = self._parse_field_call(value_node)
                    if field_desc:
                        prop_schema["description"] = field_desc
                    if field_def is not None:
                        prop_schema["default"] = field_def
                        is_required = False
                    elif field_req is False:
                        is_required = False
            else:
                default_val = _ast_to_literal(value_node)
                if default_val is not None:
                    prop_schema["default"] = default_val
                    is_required = False
                elif isinstance(value_node, ast.Constant) and value_node.value is None:
                    is_required = False

        return prop_schema, is_required

    def _parse_field_call(self, call_node: ast.Call) -> Tuple[Optional[bool], Optional[str], Any]:
        """Extract attributes from a Pydantic Field(...) call."""
        is_required: Optional[bool] = None
        description: Optional[str] = None
        default_val: Any = None

        # Check first positional argument for Ellipsis (...) or default value
        if call_node.args:
            first_arg = call_node.args[0]
            if isinstance(first_arg, ast.Constant) and first_arg.value is ...:
                is_required = True
            else:
                lit = _ast_to_literal(first_arg)
                if lit is not None:
                    default_val = lit
                    is_required = False

        for kw in call_node.keywords:
            if kw.arg == "default":
                if isinstance(kw.value, ast.Constant) and kw.value.value is ...:
                    is_required = True
                else:
                    default_val = _ast_to_literal(kw.value)
                    is_required = False
            elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                description = str(kw.value.value)
            elif kw.arg == "default_factory":
                is_required = False

        return is_required, description, default_val

    def _resolve_type_node(self, node: ast.AST) -> Tuple[Dict[str, Any], bool]:
        """Map AST annotation node to OpenAPI JSON Schema type and optionality."""
        # Simple Name: str, int, float, bool, or custom class
        if isinstance(node, ast.Name):
            type_name = node.id
            if type_name in PYTHON_TYPE_MAP:
                return {"type": PYTHON_TYPE_MAP[type_name]}, False
            # Reference to another schema (e.g. nested Pydantic model)
            return {"$ref": f"#/components/schemas/{type_name}"}, False

        # Subscript: Optional[T], Union[T, None], List[T], Dict[K, V]
        if isinstance(node, ast.Subscript):
            base_type = ""
            if isinstance(node.value, ast.Name):
                base_type = node.value.id
            elif isinstance(node.value, ast.Attribute):
                base_type = node.value.attr

            # Optional[T] or Union[T, None]
            if base_type == "Optional":
                inner_schema, _ = self._resolve_type_node(node.slice)
                inner_schema["nullable"] = True
                return inner_schema, True

            if base_type == "Union":
                # Handle Union[T, None]
                elts = []
                if isinstance(node.slice, ast.Tuple):
                    elts = node.slice.elts
                else:
                    elts = [node.slice]

                has_none = any(
                    isinstance(e, ast.Constant) and e.value is None or (isinstance(e, ast.Name) and e.id == "None")
                    for e in elts
                )
                non_none_elts = [
                    e for e in elts
                    if not (isinstance(e, ast.Constant) and e.value is None or (isinstance(e, ast.Name) and e.id == "None"))
                ]

                if non_none_elts:
                    primary_schema, _ = self._resolve_type_node(non_none_elts[0])
                    if has_none:
                        primary_schema["nullable"] = True
                        return primary_schema, True
                    return primary_schema, False

            # List[T] or list[T]
            if base_type in ("List", "list"):
                item_schema, _ = self._resolve_type_node(node.slice)
                return {"type": "array", "items": item_schema}, False

            # Dict[str, Any] or dict[str, Any]
            if base_type in ("Dict", "dict"):
                return {"type": "object"}, False

        # Binary operation: Python 3.10+ union syntax e.g. str | None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = node.left
            right = node.right
            has_none = False
            main_node = left
            if isinstance(right, ast.Constant) and right.value is None or (isinstance(right, ast.Name) and right.id == "None"):
                has_none = True
                main_node = left
            elif isinstance(left, ast.Constant) and left.value is None or (isinstance(left, ast.Name) and left.id == "None"):
                has_none = True
                main_node = right

            primary_schema, _ = self._resolve_type_node(main_node)
            if has_none:
                primary_schema["nullable"] = True
                return primary_schema, True
            return primary_schema, False

        # Default fallback
        return {"type": "string"}, False

