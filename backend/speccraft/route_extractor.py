"""Route extraction pipeline orchestrator for SpecCraft AI.

Ingests source projects (directory, zip archive, or inline code), runs static AST analysis,
maps metadata, normalizes routes, resolves operation IDs, and produces a deterministic ExtractionResult.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from speccraft.diagnostics import Diagnostic, DiagnosticCode
from speccraft.metadata_mapper import map_and_normalize_endpoints
from speccraft.models import ExtractionResult
from speccraft.parser.fastapi_adapter import FastAPIParser
from speccraft.reader import ArchiveSecurityError, SourceFileReader
from speccraft.utils.path_safety import FileTooLargeError, PathSecurityError
from speccraft.utils.timing import Timer


class RouteExtractor:
    """High-level facade orchestrating source ingestion, AST parsing, and metadata mapping."""

    def __init__(self) -> None:
        self.reader = SourceFileReader()
        self.parser = FastAPIParser()

    def extract_from_path(self, target_path: Union[str, Path]) -> ExtractionResult:
        """Extract all routes from a project directory or Python file.

        Args:
            target_path: Path to target directory or file.

        Returns:
            Fully normalized and deterministically sorted ExtractionResult.
        """
        path_obj = Path(target_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Path not found: {path_obj}")

        with Timer() as timer:
            # 1. Read files
            if path_obj.is_dir():
                source_files = self.reader.read_directory(path_obj)
            else:
                source_files = [self.reader.read_file(path_obj)]

            # 2. Framework check
            framework = self.reader.detect_framework(source_files)
            initial_diagnostics = []
            if framework == "unsupported":
                initial_diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_E001,
                        file=str(path_obj.name),
                        custom_message=f"No FastAPI imports detected in project '{path_obj.name}'.",
                    )
                )

            # 3. Parse ASTs
            result = self.parser.parse_files(source_files)
            all_diagnostics = initial_diagnostics + result.diagnostics

            # 4. Map, normalize, and deterministically sort endpoints
            sorted_endpoints = map_and_normalize_endpoints(result.endpoints)

        return ExtractionResult(
            endpoints=sorted_endpoints,
            schemas=result.schemas,
            warnings=result.warnings,
            diagnostics=all_diagnostics,
            files_scanned=result.files_scanned,
            total_loc=result.total_loc,
            parse_duration_ms=timer.duration_ms,
        )

    def extract_from_zip(self, zip_source: Union[str, Path, bytes]) -> ExtractionResult:
        """Safely extract all routes from a .zip archive with Zip-Slip protection."""
        with Timer() as timer:
            try:
                source_files = self.reader.read_zip_archive(zip_source)
            except (ArchiveSecurityError, FileTooLargeError, PathSecurityError) as err:
                diag = Diagnostic.create(
                    code=DiagnosticCode.SC_E002,
                    file="archive.zip",
                    custom_message=str(err),
                )
                return ExtractionResult(
                    endpoints=[],
                    schemas={},
                    warnings=[],
                    diagnostics=[diag],
                    files_scanned=0,
                    total_loc=0,
                    parse_duration_ms=timer.duration_ms,
                )

            framework = self.reader.detect_framework(source_files)
            initial_diagnostics = []
            if framework == "unsupported":
                initial_diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_E001,
                        file="archive.zip",
                        custom_message="No FastAPI imports detected in uploaded archive.",
                    )
                )

            result = self.parser.parse_files(source_files)
            all_diagnostics = initial_diagnostics + result.diagnostics
            sorted_endpoints = map_and_normalize_endpoints(result.endpoints)

        return ExtractionResult(
            endpoints=sorted_endpoints,
            schemas=result.schemas,
            warnings=result.warnings,
            diagnostics=all_diagnostics,
            files_scanned=result.files_scanned,
            total_loc=result.total_loc,
            parse_duration_ms=timer.duration_ms,
        )

    def extract_from_code_string(self, code: str, virtual_name: str = "snippet.py") -> ExtractionResult:
        """Extract routes from a raw pasted code string (e.g. from Web UI)."""
        with Timer() as timer:
            source = self.reader.read_code_string(code, virtual_name)
            result = self.parser.parse_files([source])
            sorted_endpoints = map_and_normalize_endpoints(result.endpoints)

        return ExtractionResult(
            endpoints=sorted_endpoints,
            schemas=result.schemas,
            warnings=result.warnings,
            diagnostics=result.diagnostics,
            files_scanned=1,
            total_loc=source.loc,
            parse_duration_ms=timer.duration_ms,
        )

