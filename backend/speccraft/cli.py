"""Command-line interface (CLI) for SpecCraft AI static AST extraction & spec diff."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from speccraft.ai import DiffSummaryProposal, get_enricher_service
from speccraft.diff_engine import SpecDiffEngine
from speccraft.exporters import MockServerGenerator, SDKGenerator
from speccraft.exporters.postman_exporter import parse_openapi_input
from speccraft.models import DiffReport
from speccraft.openapi_generator import OpenAPIGenerator
from speccraft.overlay import get_overlay_store
from speccraft.route_extractor import RouteExtractor


def _load_spec_from_input(input_path: Path) -> Dict[str, Any]:
    """Load an OpenAPI spec from a JSON/YAML file or statically extract from code."""
    suffix = input_path.suffix.lower()
    if input_path.is_file() and suffix in {".json", ".yaml", ".yml"}:
        return parse_openapi_input(input_path.read_text(encoding="utf-8"))

    extractor = RouteExtractor()
    if suffix == ".zip":
        result = extractor.extract_from_zip(input_path)
    else:
        result = extractor.extract_from_path(input_path)

    result = get_overlay_store().apply_to_extraction_result(result)
    return OpenAPIGenerator().generate(result)


def format_diff_markdown(report: DiffReport, ai_summary: DiffSummaryProposal) -> str:
    """Format a Markdown PR/CI summary for DiffReport + AI mobile review cards."""
    s = report.summary
    lines: List[str] = [
        "# SpecCraft AI — OpenAPI Diff Report",
        "",
        f"- **Risk Level**: `{ai_summary.risk_level.upper()}` ({ai_summary.provider})",
        f"- **Total Changes**: {s.total_changes}",
        f"- **Breaking Changes**: {s.breaking_changes}",
        f"- **Non-Breaking Changes**: {s.non_breaking_changes}",
        "",
        f"## Summary",
        "",
        ai_summary.executive_summary,
        "",
    ]

    if ai_summary.cards:
        lines.extend(
            [
                "| Severity | Endpoint | Impact | Before | After |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )
        for card in ai_summary.cards:
            sev_badge = "BREAKING" if card.severity == "breaking" else "NON-BREAKING"
            lines.append(
                f"| `{sev_badge}` | `{card.endpoint}` | {card.one_line_impact} "
                f"| `{card.before}` | `{card.after}` |"
            )
        lines.append("")

    return "\n".join(lines)


def _run_extract_cli(argv: List[str]) -> int:
    """Run static AST route extraction CLI."""
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
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable SHA-256 incremental AST caching across unchanged files.",
    )

    args = parser.parse_args(argv)
    target_path = Path(args.target).resolve()

    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1

    extractor = RouteExtractor()
    if target_path.suffix.lower() == ".zip":
        result = extractor.extract_from_zip(target_path)
    else:
        result = extractor.extract_from_path(target_path, incremental=args.incremental)

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

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
            f"{(ep.operation_id or ''):<25} "
            f"{status_code:<6}"
        )

    print("=" * 85)

    if result.diagnostics:
        errors = [d for d in result.diagnostics if d.severity.value == "error"]
        warnings = [d for d in result.diagnostics if d.severity.value == "warning"]
        print(f"[DIAGNOSTICS] {len(errors)} Error(s), {len(warnings)} Warning(s):")
        for diag in result.diagnostics:
            print(f"  * {diag.format_terminal()}")
        print("=" * 85)
        if errors:
            return 1
    else:
        print("[DIAGNOSTICS] All checks clean (0 errors, 0 warnings).")
        print("=" * 85)

    return 0


def _run_diff_cli(argv: List[str]) -> int:
    """Compare baseline and target specs/codebases, emit cards.json & fail optionally on breaking."""
    parser = argparse.ArgumentParser(
        prog="speccraft diff",
        description="Compare two OpenAPI specs or FastAPI codebases and emit mobile review cards.",
    )
    parser.add_argument("baseline", type=str, help="Baseline OpenAPI JSON/YAML file or source directory.")
    parser.add_argument("target", type=str, help="Target OpenAPI JSON/YAML file or source directory.")
    parser.add_argument(
        "--cards-out",
        type=str,
        default=None,
        help="Optional output path to write JSON diff summary + mobile cards array.",
    )
    parser.add_argument(
        "--summary-out",
        type=str,
        default=None,
        help="Optional output path to write Markdown summary (e.g. for $GITHUB_STEP_SUMMARY).",
    )
    parser.add_argument(
        "--fail-on-breaking",
        action="store_true",
        help="Exit with code 1 if any breaking change is detected.",
    )

    args = parser.parse_args(argv)
    baseline_path = Path(args.baseline).resolve()
    target_path = Path(args.target).resolve()

    for label, p in (("Baseline", baseline_path), ("Target", target_path)):
        if not p.exists():
            print(f"Error: {label} path does not exist: {p}", file=sys.stderr)
            return 1

    baseline_spec = _load_spec_from_input(baseline_path)
    target_spec = _load_spec_from_input(target_path)

    report = SpecDiffEngine().compare(baseline_spec, target_spec)
    ai_summary = asyncio.run(get_enricher_service().summarize_diff(report.model_dump()))

    markdown_summary = format_diff_markdown(report, ai_summary)
    print(markdown_summary)

    if args.cards_out:
        cards_payload = {
            **ai_summary.model_dump(),
            "summary": report.summary.model_dump(),
        }
        cards_file = Path(args.cards_out)
        cards_file.parent.mkdir(parents=True, exist_ok=True)
        cards_file.write_text(
            json.dumps(cards_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if args.summary_out:
        summary_file = Path(args.summary_out)
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(markdown_summary, encoding="utf-8")

    if args.fail_on_breaking and report.summary.breaking_changes > 0:
        print(
            f"[CI GATE] Failing with exit code 1: detected {report.summary.breaking_changes} breaking change(s).",
            file=sys.stderr,
        )
        return 1

    return 0


def _run_sdk_cli(argv: List[str]) -> int:
    """Generate TypeScript or Python client SDK from an OpenAPI spec."""
    parser = argparse.ArgumentParser(prog="speccraft sdk")
    parser.add_argument("spec", type=str, help="Path to OpenAPI JSON/YAML spec.")
    parser.add_argument("--lang", choices=["typescript", "python"], default="typescript")
    parser.add_argument("--out", type=str, default=None, help="Output file path.")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        print(f"Error: Spec path does not exist: {spec_path}", file=sys.stderr)
        return 1

    files = SDKGenerator().generate(spec_path.read_text(encoding="utf-8"), language=args.lang)
    fname, code = next(iter(files.items()))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code, encoding="utf-8")
        print(f"Wrote {args.lang} SDK ({fname}) to {out_path}")
    else:
        print(code)
    return 0


def _run_mock_cli(argv: List[str]) -> int:
    """Generate standalone runnable FastAPI mock_server.py from an OpenAPI spec."""
    parser = argparse.ArgumentParser(prog="speccraft mock")
    parser.add_argument("spec", type=str, help="Path to OpenAPI JSON/YAML spec.")
    parser.add_argument("--out", type=str, default=None, help="Output file path.")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        print(f"Error: Spec path does not exist: {spec_path}", file=sys.stderr)
        return 1

    code = MockServerGenerator().to_fastapi_mock_code(spec_path.read_text(encoding="utf-8"))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code, encoding="utf-8")
        print(f"Wrote FastAPI mock server to {out_path}")
    else:
        print(code)
    return 0


def run_cli(argv: Optional[List[str]] = None) -> int:
    """Entry point supporting `speccraft <target>`, `diff`, `sdk`, and `mock`."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    cmd = raw_argv[:1]
    if cmd == ["diff"]:
        return _run_diff_cli(raw_argv[1:])
    if cmd == ["sdk"]:
        return _run_sdk_cli(raw_argv[1:])
    if cmd == ["mock"]:
        return _run_mock_cli(raw_argv[1:])
    return _run_extract_cli(raw_argv)


if __name__ == "__main__":
    sys.exit(run_cli())
