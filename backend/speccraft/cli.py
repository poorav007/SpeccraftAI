"""Command-line interface (CLI) for SpecCraft AI static AST extraction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from speccraft.route_extractor import RouteExtractor


def run_cli() -> int:
    """Entry point for terminal CLI execution."""
    parser = argparse.ArgumentParser(
        prog="speccraft",
        description="SpecCraft AI — Static AST route extractor & OpenAPI spec generator.",
    )
    parser.add_argument(
        "target",
        type=str,
        help="Path to target directory, .py file, or .zip archive to analyze.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON format instead of human-readable table.",
    )

    args = parser.parse_args()
    target_path = Path(args.target).resolve()

    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    extractor = RouteExtractor()
    if target_path.suffix.lower() == ".zip":
        result = extractor.extract_from_zip(target_path)
    else:
        result = extractor.extract_from_path(target_path)

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    # Print ASCII table
    print("=" * 85)
    print("SpecCraft AI — Static AST Route Extraction Report")
    print(
        f"Files Scanned: {result.files_scanned} | Total LOC: {result.total_loc} | "
        f"Endpoints Found: {len(result.endpoints)} | Duration: {result.parse_duration_ms}ms"
    )
    print("=" * 85)
    print(f"{'METHOD':<8} {'PATH':<35} {'OPERATION ID':<25} {'STATUS':<6}")
    print("-" * 85)

    for ep in result.endpoints:
        status_code = next(iter(ep.responses.keys())) if ep.responses else "200"
        print(
            f"{ep.method.value.upper():<8} "
            f"{ep.path:<35} "
            f"{ep.operation_id:<25} "
            f"{status_code:<6}"
        )

    print("=" * 85)

    # Print Diagnostics if present
    if result.diagnostics:
        errors = [d for d in result.diagnostics if d.severity.value == "error"]
        warnings = [d for d in result.diagnostics if d.severity.value == "warning"]
        print(f"[DIAGNOSTICS] {len(errors)} Error(s), {len(warnings)} Warning(s):")
        for diag in result.diagnostics:
            print(f"  • {diag.format_terminal()}")
        print("=" * 85)
        if errors:
            return 1
    else:
        print("[DIAGNOSTICS] All checks clean (0 errors, 0 warnings).")
        print("=" * 85)

    return 0


if __name__ == "__main__":
    sys.exit(run_cli())

