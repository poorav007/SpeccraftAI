"""Route extraction pipeline orchestrator for SpecCraft AI.

Ingests source projects (directory, zip archive, or inline code), runs static
multi-framework AST/route analysis (FastAPI, Flask, Express) with optional
SHA-256 incremental caching, maps metadata, and emits a deterministic ExtractionResult.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from speccraft.diagnostics import Diagnostic, DiagnosticCode
from speccraft.incremental_cache import IncrementalParseCache
from speccraft.metadata_mapper import map_and_normalize_endpoints
from speccraft.models import APIEndpoint, ExtractionResult, ExtractionWarning, SourceFile
from speccraft.parser import ExpressParser, FastAPIParser, FlaskParser
from speccraft.reader import ArchiveSecurityError, SourceFileReader
from speccraft.utils.path_safety import FileTooLargeError, PathSecurityError
from speccraft.utils.timing import Timer


class RouteExtractor:
    """High-level facade orchestrating source ingestion, parsing, and metadata mapping."""

    def __init__(self) -> None:
        self.reader = SourceFileReader()
        self.parser = FastAPIParser()
        self.adapters = [FastAPIParser(), FlaskParser(), ExpressParser()]

    def _parse_with_adapters(self, source_files: List[SourceFile]) -> ExtractionResult:
        """Dispatch each source file to matching framework adapters cleanly."""
        if not source_files:
            return ExtractionResult()

        all_endpoints: List[APIEndpoint] = []
        all_schemas: Dict[str, Dict[str, Any]] = {}
        all_warnings: List[ExtractionWarning] = []
        all_diagnostics: List[Diagnostic] = []
        total_loc = sum(sf.loc for sf in source_files)

        for adapter in self.adapters:
            matching = [sf for sf in source_files if adapter.can_parse(sf)]
            if not matching:
                continue
            sub_res = adapter.parse_files(matching)
            all_endpoints.extend(sub_res.endpoints)
            all_schemas.update(sub_res.schemas)
            all_warnings.extend(sub_res.warnings)
            all_diagnostics.extend(sub_res.diagnostics)

        return ExtractionResult(
            endpoints=all_endpoints,
            schemas=all_schemas,
            warnings=all_warnings,
            diagnostics=all_diagnostics,
            files_scanned=len(source_files),
            total_loc=total_loc,
        )

    def _parse_incremental(
        self,
        source_files: List[SourceFile],
        cache_path: Optional[Union[str, Path]] = None,
    ) -> tuple[ExtractionResult, int, int]:
        """Parse only modified/new files via SHA-256 IncrementalParseCache."""
        cache = IncrementalParseCache(Path(cache_path) if cache_path else None)
        hits, misses, db = cache.partition(source_files)

        all_endpoints: List[APIEndpoint] = []
        all_schemas: Dict[str, Dict[str, Any]] = {}
        all_diagnostics: List[Diagnostic] = []

        for entry in hits:
            all_endpoints.extend(APIEndpoint.model_validate(ep) for ep in entry.get("endpoints", []))
            all_schemas.update(entry.get("schemas") or {})
            all_diagnostics.extend(Diagnostic.model_validate(d) for d in entry.get("diagnostics", []))

        for sf in misses:
            per_file_res = self._parse_with_adapters([sf])
            all_endpoints.extend(per_file_res.endpoints)
            all_schemas.update(per_file_res.schemas)
            all_diagnostics.extend(per_file_res.diagnostics)
            db[sf.relative_path] = cache.serialize_file_result(
                sf, per_file_res.endpoints, per_file_res.schemas, per_file_res.diagnostics
            )

        cache.save(db)
        combined = ExtractionResult(
            endpoints=all_endpoints,
            schemas=all_schemas,
            diagnostics=all_diagnostics,
            files_scanned=len(source_files),
            total_loc=sum(sf.loc for sf in source_files),
        )
        return combined, len(hits), len(misses)

    def extract_from_path(
        self,
        target_path: Union[str, Path],
        incremental: bool = False,
        cache_path: Optional[Union[str, Path]] = None,
    ) -> ExtractionResult:
        """Extract all routes from a project directory or source file."""
        path_obj = Path(target_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Path not found: {path_obj}")

        with Timer() as timer:
            if path_obj.is_dir():
                source_files = self.reader.read_directory(path_obj)
            else:
                source_files = [self.reader.read_file(path_obj)]

            framework = self.reader.detect_framework(source_files)
            initial_diagnostics: List[Diagnostic] = []
            if framework == "unsupported":
                initial_diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_E001,
                        file=str(path_obj.name),
                        custom_message=f"No supported API framework (FastAPI, Flask, Express) detected in '{path_obj.name}'.",
                    )
                )

            cache_hits = 0
            cache_misses = len(source_files)
            if incremental:
                result, cache_hits, cache_misses = self._parse_incremental(source_files, cache_path)
            else:
                result = self._parse_with_adapters(source_files)

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
            cache_hits=cache_hits,
            cache_misses=cache_misses,
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
            initial_diagnostics: List[Diagnostic] = []
            if framework == "unsupported":
                initial_diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_E001,
                        file="archive.zip",
                        custom_message="No supported API framework (FastAPI, Flask, Express) detected in uploaded archive.",
                    )
                )

            result = self._parse_with_adapters(source_files)
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
            cache_misses=result.files_scanned,
        )

    def extract_from_code_string(
        self,
        code: str,
        virtual_name: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract routes from a raw pasted code string (e.g. from Web UI)."""
        target_name = virtual_name or filename or "snippet.py"
        with Timer() as timer:
            source = self.reader.read_code_string(code, target_name)
            result = self._parse_with_adapters([source])
            sorted_endpoints = map_and_normalize_endpoints(result.endpoints)

        return ExtractionResult(
            endpoints=sorted_endpoints,
            schemas=result.schemas,
            warnings=result.warnings,
            diagnostics=result.diagnostics,
            files_scanned=1,
            total_loc=source.loc,
            parse_duration_ms=timer.duration_ms,
            cache_misses=1,
        )
