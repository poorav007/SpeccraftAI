
import ast
from pathlib import Path

from .diagnostics import Diagnostic


SUPPORTED_METHODS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
}

BUILTIN_RESPONSE_TYPES = {
    "str",
    "int",
    "float",
    "bool",
    "dict",
    "list",
    "tuple",
    "set",
    "bytes",
}


def make_diagnostic(code, message, file, line, hint):
    """Create and return a Diagnostic object."""
    severity = "error" if code.startswith("SC-E") else "warning"

    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        file=str(file),
        line=max(1, line or 1),
        hint=hint,
    )


def get_literal_string(node):
    """Return a string only when the AST node contains a literal string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    return None


def get_call_name(node):
    """Get the name of a function or method call."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def get_defined_models(tree):
    """Collect class names and imported names in a Python file."""
    defined_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            defined_names.add(node.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    defined_names.add(alias.asname or alias.name)

    return defined_names


def get_router_prefixes(tree):
    """Find APIRouter variables and their literal prefixes."""
    router_prefixes = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        value = node.value

        if not isinstance(value, ast.Call):
            continue

        if get_call_name(value.func) != "APIRouter":
            continue

        prefix = ""

        for keyword in value.keywords:
            if keyword.arg == "prefix":
                prefix = get_literal_string(keyword.value)

                if prefix is None:
                    prefix = ""

        targets = []

        if isinstance(node, ast.Assign):
            targets = node.targets
        else:
            targets = [node.target]

        for target in targets:
            if isinstance(target, ast.Name):
                router_prefixes[target.id] = prefix

    return router_prefixes


def join_paths(prefix, path):
    """Join router prefix and route path."""
    if not prefix:
        return path

    if not path:
        return prefix

    return "/" + "/".join(
        part.strip("/")
        for part in (prefix, path)
        if part.strip("/")
    )


def parse_file(file_path, project_root):
    """Parse one Python file and return its routes and diagnostics."""

    routes = []
    diagnostics = []

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

    except (SyntaxError, UnicodeDecodeError) as error:
        diagnostics.append(
            make_diagnostic(
                code="SC-W008",
                message=(
                    "What failed: Python file could not be parsed. "
                    "Why: The file contains invalid Python syntax or could not be decoded. "
                    "What to do next: Fix the file and try again."
                ),
                file=file_path.relative_to(project_root),
                line=getattr(error, "lineno", 1) or 1,
                hint="Check the syntax and encoding of this Python file.",
            )
        )

        return routes, diagnostics

    relative_file = file_path.relative_to(project_root)

    defined_models = get_defined_models(tree)
    router_prefixes = get_router_prefixes(tree)

    # Detect unsupported registration methods.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        method_name = get_call_name(node.func)

        if method_name in {"add_api_route", "mount"}:
            diagnostics.append(
                make_diagnostic(
                    code="SC-W003",
                    message=(
                        "What failed: API route could not be detected. "
                        "Why: The route uses an unsupported registration method. "
                        "What to do next: Use a supported FastAPI route decorator."
                    ),
                    file=relative_file,
                    line=node.lineno,
                    hint="Use a supported FastAPI route decorator.",
                )
            )

        # Check include_router references.
        if method_name == "include_router":
            if not isinstance(node.func, ast.Attribute):
                continue

            if not node.args:
                continue

            router_argument = node.args[0]

            if (
                isinstance(router_argument, ast.Name)
                and router_argument.id not in router_prefixes
                and router_argument.id not in defined_models
            ):
                diagnostics.append(
                    make_diagnostic(
                        code="SC-W002",
                        message=(
                            "What failed: Router prefix or include target could not be resolved. "
                            "Why: The included router could not be found in this file. "
                            "What to do next: Check the router reference."
                        ),
                        file=relative_file,
                        line=node.lineno,
                        hint="Check the APIRouter variable and its import.",
                    )
                )

    # Detect routes using supported decorators.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            if not isinstance(decorator.func, ast.Attribute):
                continue

            method = decorator.func.attr.lower()

            if method not in SUPPORTED_METHODS:
                continue

            router_name = None

            if isinstance(decorator.func.value, ast.Name):
                router_name = decorator.func.value.id

            # Read the route path.
            path = None

            if decorator.args:
                path = get_literal_string(decorator.args[0])

            if path is None:
                diagnostics.append(
                    make_diagnostic(
                        code="SC-W001",
                        message=(
                            "What failed: Route path is not a literal. "
                            "Why: The path uses a variable, expression or f-string. "
                            "What to do next: Use a literal route path."
                        ),
                        file=relative_file,
                        line=decorator.lineno,
                        hint="Use a fixed string such as '/users/{user_id}'.",
                    )
                )

                continue

            prefix = router_prefixes.get(router_name, "")
            full_path = join_paths(prefix, path)

            # Check function parameters.
            for argument in node.args.args:
                if argument.arg in {"self", "cls"}:
                    continue

                if argument.annotation is None:
                    diagnostics.append(
                        make_diagnostic(
                            code="SC-W004",
                            message=(
                                "What failed: Parameter has no annotation. "
                                "Why: Its data type cannot be determined. "
                                "What to do next: Add a type annotation."
                            ),
                            file=relative_file,
                            line=argument.lineno,
                            hint="Add a type annotation, such as str or int.",
                        )
                    )

            # Check dependency defaults.
            all_defaults = node.args.defaults

            for default in all_defaults:
                if isinstance(default, ast.Call):
                    if get_call_name(default.func) == "Depends":
                        diagnostics.append(
                            make_diagnostic(
                                code="SC-W005",
                                message=(
                                    "What failed: Dependency parameters were not expanded. "
                                    "Why: Depends dependencies may contain additional parameters. "
                                    "What to do next: Review the dependency manually."
                                ),
                                file=relative_file,
                                line=default.lineno,
                                hint="Check the Depends dependency manually.",
                            )
                        )

            for default in node.args.kw_defaults:
                if isinstance(default, ast.Call):
                    if get_call_name(default.func) == "Depends":
                        diagnostics.append(
                            make_diagnostic(
                                code="SC-W005",
                                message=(
                                    "What failed: Dependency parameters were not expanded. "
                                    "Why: Depends dependencies may contain additional parameters. "
                                    "What to do next: Review the dependency manually."
                                ),
                                file=relative_file,
                                line=default.lineno,
                                hint="Check the Depends dependency manually.",
                            )
                        )

            # Read response_model and status_code.
            response_model = None
            response_model_node = None
            status_code = None

            for keyword in decorator.keywords:
                if keyword.arg == "response_model":
                    response_model = ast.unparse(keyword.value)
                    response_model_node = keyword.value

                elif keyword.arg == "status_code":
                    if isinstance(keyword.value, ast.Constant):
                        status_code = keyword.value.value

            # Check whether the response model is defined or imported.
            if (
                isinstance(response_model_node, ast.Name)
                and response_model_node.id not in defined_models
                and response_model_node.id not in BUILTIN_RESPONSE_TYPES
            ):
                diagnostics.append(
                    make_diagnostic(
                        code="SC-W007",
                        message=(
                            "What failed: Model reference could not be resolved. "
                            "Why: The referenced response model was not found. "
                            "What to do next: Check the model definition or import."
                        ),
                        file=relative_file,
                        line=decorator.lineno,
                        hint="Define or import the response model.",
                    )
                )

            # Check whether a response model was declared.
            if response_model is None:
                diagnostics.append(
                    make_diagnostic(
                        code="SC-W006",
                        message=(
                            "What failed: Response schema was not declared. "
                            "Why: No response_model was found. "
                            "What to do next: Declare a response model."
                        ),
                        file=relative_file,
                        line=decorator.lineno,
                        hint="Add response_model to the route decorator.",
                    )
                )

            # Read function docstring.
            docstring = ast.get_docstring(node)

            # Save the detected route.
            routes.append(
                {
                    "method": method.upper(),
                    "path": full_path,
                    "function": node.name,
                    "file": str(relative_file),
                    "line": node.lineno,
                    "response_model": response_model,
                    "status_code": status_code,
                    "docstring": docstring,
                }
            )

    return routes, diagnostics


def parse_project(project_path):
    """
    Parse all Python files in a project.

    Returns:
        routes: List of detected API routes.
        diagnostics: List of Diagnostic objects.
    """

    project_root = Path(project_path).resolve()

    if not project_root.exists():
        raise FileNotFoundError(
            f"Project path does not exist: {project_root}"
        )

    if project_root.is_file():
        python_files = (
            [project_root] if project_root.suffix == ".py" else []
        )
        project_root = project_root.parent
    else:
        python_files = sorted(project_root.rglob("*.py"))

    all_routes = []
    all_diagnostics = []

    for file_path in python_files:
        routes, diagnostics = parse_file(file_path, project_root)

        all_routes.extend(routes)
        all_diagnostics.extend(diagnostics)

    return all_routes, all_diagnostics
