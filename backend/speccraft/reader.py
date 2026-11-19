"""Safe source code reader for SpecCraft AI static analysis engine.

Safely ingests Python source files and project directories without ever executing code.
Enforces path traversal protection, file size thresholds, and encoding fallbacks.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Set, Union

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


class SourceFileReader:
    """Safely reads source files and directories into structured SourceFile models."""

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
        """Wrap an in-memory code string (e.g. from frontend paste) into a SourceFile.

        Args:
            code: Raw source code string.
            virtual_name: Synthetic filename for reporting.

        Returns:
            SourceFile instance.
        """
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
        """Safely read a single file from disk.

        Args:
            filepath: Path to the target file.
            base_dir: Base directory boundary. If None, uses target's parent directory.

        Returns:
            SourceFile with content and LOC count.

        Raises:
            PathSecurityError: If filepath escapes base_dir.
            FileTooLargeError: If file exceeds maximum allowed size.
            FileNotFoundError: If file does not exist.
        """
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

        # Safe decode with replacement fallback for foreign characters
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
        """Recursively scan a directory for valid Python source files.

        Skips ignored directories (.git, node_modules, __pycache__, etc.) and
        enforces total scan byte limits to prevent denial-of-service.

        Args:
            base_dir: Directory path to scan.
            custom_ignore: Additional directory names to ignore.

        Returns:
            List of SourceFile models.
        """
        root_dir = Path(base_dir).resolve()
        if not root_dir.is_dir():
            raise NotADirectoryError(f"Scanned path is not a directory: {root_dir}")

        source_files: List[SourceFile] = []
        accumulated_bytes = 0

        for current_root, dirs, files in os.walk(root_dir):
            # Prune ignored directories in-place so os.walk does not recurse into them
            dirs[:] = [d for d in dirs if not is_ignored_directory(d, custom_ignore)]

            for filename in sorted(files):
                ext = Path(filename).suffix.lower()
                if ext not in self.allowed_extensions:
                    continue

                file_path = Path(current_root) / filename
                file_size = file_path.stat().st_size

                if file_size > self.max_file_size:
                    continue  # Skip oversized individual files

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

