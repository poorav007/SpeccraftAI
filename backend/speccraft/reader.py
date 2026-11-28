"""Safe source code reader for SpecCraft AI static analysis engine.

Safely ingests Python source files, project directories, and .zip archives without ever executing code.
Enforces Zip-Slip protection, path traversal protection, file size thresholds, and framework detection.
"""

from __future__ import annotations

import ast
import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import BinaryIO, List, Optional, Set, Union

from speccraft.diagnostics import Diagnostic, DiagnosticCode
from speccraft.models import SourceFile
from speccraft.utils.path_safety import (
    ALLOWED_EXTENSIONS,
    DEFAULT_IGNORE_DIRS,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_SCAN_BYTES,
    FileTooLargeError,
    PathSecurityError,
    is_ignored_directory,
    validate_safe_path,
)

# Limits from PRD F02 for safe project import
MAX_ARCHIVE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB per archive
MAX_ARCHIVE_FILES: int = 2000                   # 2,000 files maximum


class ArchiveSecurityError(ValueError):
    """Raised when an uploaded zip archive violates security or size limits."""
    pass


class SourceFileReader:
    """Safely reads source files, directories, and zip archives into structured SourceFile models."""

    def __init__(
        self,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
        max_total_scan_size: int = MAX_TOTAL_SCAN_BYTES,
        allowed_extensions: Optional[Set[str]] = None,
    ) -> None:
        self.max_file_size = max_file_size
        self.max_total_scan_size = max_total_scan_size
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS

    @staticmethod
    def count_loc(content: str) -> int:
        """Count total lines of code in content."""
        if not content:
            return 0
        return len(content.splitlines())

    def read_code_string(self, code: str, virtual_name: str = "inline_snippet.py") -> SourceFile:
        """Wrap an in-memory code string (e.g. from frontend paste) into a SourceFile."""
        encoded_bytes = len(code.encode("utf-8"))
        if encoded_bytes > self.max_file_size:
            raise FileTooLargeError(
                f"Pasted code size ({encoded_bytes} bytes) exceeds limit of {self.max_file_size} bytes."
            )

        return SourceFile(
            relative_path=virtual_name,
            absolute_path=None,
            content=code,
            loc=self.count_loc(code),
        )

    def read_file(
        self,
        filepath: Union[str, Path],
        base_dir: Optional[Union[str, Path]] = None,
    ) -> SourceFile:
        """Safely read a single file from disk with path traversal verification."""
        raw_path = Path(filepath)
        effective_base = Path(base_dir).resolve() if base_dir else raw_path.parent.resolve()
        safe_path = validate_safe_path(raw_path, effective_base)

        if not safe_path.is_file():
            raise FileNotFoundError(f"File not found: {safe_path}")

        file_size = safe_path.stat().st_size
        if file_size > self.max_file_size:
            raise FileTooLargeError(
                f"File '{safe_path.name}' ({file_size} bytes) exceeds limit of {self.max_file_size} bytes."
            )

        try:
            content = safe_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = safe_path.read_text(encoding="latin-1")

        rel_path = safe_path.relative_to(effective_base).as_posix()
        return SourceFile(
            relative_path=rel_path,
            absolute_path=str(safe_path),
            content=content,
            loc=self.count_loc(content),
        )

    def read_directory(
        self,
        base_dir: Union[str, Path],
        custom_ignore: Optional[Set[str]] = None,
    ) -> List[SourceFile]:
        """Recursively scan a directory for valid Python source files."""
        root_dir = Path(base_dir).resolve()
        if not root_dir.is_dir():
            raise NotADirectoryError(f"Scanned path is not a directory: {root_dir}")

        source_files: List[SourceFile] = []
        accumulated_bytes = 0

        for current_root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not is_ignored_directory(d, custom_ignore)]

            for filename in sorted(files):
                ext = Path(filename).suffix.lower()
                if ext not in self.allowed_extensions:
                    continue

                file_path = Path(current_root) / filename
                file_size = file_path.stat().st_size

                if file_size > self.max_file_size:
                    continue

                accumulated_bytes += file_size
                if accumulated_bytes > self.max_total_scan_size:
                    raise FileTooLargeError(
                        f"Total scan size exceeded {self.max_total_scan_size} bytes at '{file_path.name}'."
                    )

                try:
                    source_file = self.read_file(file_path, base_dir=root_dir)
                    source_files.append(source_file)
                except (PathSecurityError, UnicodeDecodeError, OSError):
                    continue

        return source_files

    def read_zip_archive(
        self,
        zip_source: Union[str, Path, bytes, BinaryIO],
        max_archive_size: int = MAX_ARCHIVE_SIZE_BYTES,
        max_file_count: int = MAX_ARCHIVE_FILES,
    ) -> List[SourceFile]:
        """Safely extract and read a .zip archive into SourceFiles with Zip-Slip defense.

        Args:
            zip_source: Path to zip file, or raw bytes / stream.
            max_archive_size: Maximum allowed uncompressed size in bytes.
            max_file_count: Maximum number of entries permitted.

        Returns:
            List of safely extracted SourceFile models.

        Raises:
            ArchiveSecurityError: If archive exceeds limits, is encrypted, or attempts Zip-Slip.
        """
        # Create a ZipFile instance
        if isinstance(zip_source, (str, Path)):
            zf_stream = open(zip_source, "rb")
        elif isinstance(zip_source, bytes):
            zf_stream = io.BytesIO(zip_source)
        else:
            zf_stream = zip_source

        try:
            with zipfile.ZipFile(zf_stream, "r") as zf:
                infolist = zf.infolist()

                if len(infolist) > max_file_count:
                    raise ArchiveSecurityError(
                        f"Archive rejected (SC-E002): Contains {len(infolist)} files (limit: {max_file_count})."
                    )

                # Check for password encryption and size
                total_uncompressed = 0
                for info in infolist:
                    if info.flag_bits & 0x1:
                        raise ArchiveSecurityError("Archive rejected (SC-E002): Encrypted archives are not supported.")

                    # Reject symlinks (UNIX mode check)
                    is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
                    if is_symlink:
                        raise ArchiveSecurityError("Archive rejected (SC-E002): Symlinks in archives are prohibited.")

                    total_uncompressed += info.file_size
                    if total_uncompressed > max_archive_size:
                        raise ArchiveSecurityError(
                            f"Archive rejected (SC-E002): Total uncompressed size ({total_uncompressed} bytes) "
                            f"exceeds limit ({max_archive_size} bytes)."
                        )

                # Extract into a secure temporary directory and parse
                with tempfile.TemporaryDirectory(prefix="speccraft_zip_") as temp_dir:
                    dest_dir = Path(temp_dir).resolve()

                    for info in infolist:
                        # Zip-Slip Guard: Ensure every member resolves strictly inside dest_dir
                        target_path = (dest_dir / info.filename).resolve()
                        try:
                            target_path.relative_to(dest_dir)
                        except ValueError:
                            raise ArchiveSecurityError(
                                f"Archive rejected (SC-E002): Zip-Slip path traversal attempt in '{info.filename}'."
                            )

                        if info.is_dir():
                            target_path.mkdir(parents=True, exist_ok=True)
                        else:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(info) as src, open(target_path, "wb") as dst:
                                dst.write(src.read())

                    return self.read_directory(dest_dir)
        finally:
            if isinstance(zip_source, (str, Path)) and not zf_stream.closed:
                zf_stream.close()

    @staticmethod
    def detect_framework(source_files: List[SourceFile]) -> str:
        """Scan source files for supported frameworks (FastAPI, Flask, Express).

        Returns:
            'fastapi', 'flask', 'express', 'mixed', or 'unsupported'.
        """
        detected: Set[str] = set()

        for sf in source_files:
            lower_path = sf.relative_path.lower()
            lower_content = sf.content.lower()

            if lower_path.endswith((".js", ".mjs", ".ts")):
                if "express" in lower_content or ".get(" in lower_content or ".post(" in lower_content:
                    detected.add("express")
                continue

            if "fastapi" in lower_content or "flask" in lower_content:
                try:
                    tree = ast.parse(sf.content, filename=sf.relative_path)
                    for node in ast.walk(tree):
                        names: List[str] = []
                        if isinstance(node, ast.Import):
                            names = [a.name.lower() for a in node.names]
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            names = [node.module.lower()]
                        for name in names:
                            if name == "fastapi" or name.startswith("fastapi."):
                                detected.add("fastapi")
                            elif name == "flask" or name.startswith("flask."):
                                detected.add("flask")
                except SyntaxError:
                    continue

        if not detected:
            return "unsupported"
        if len(detected) == 1:
            return next(iter(detected))
        return "mixed"
