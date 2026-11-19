"""Path safety and traversal validation utilities.

Ensures that user-supplied paths, uploaded files, or repository directories cannot
escape target boundaries (preventing directory traversal attacks like ../../etc/passwd).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set, Union

# Common directories that should always be ignored when scanning codebases
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "dist",
    ".egg-info",
    ".idea",
    ".vscode",
}

# Supported file extensions for backend AST analysis
ALLOWED_EXTENSIONS: Set[str] = {".py"}

# Maximum file sizes for security (anti-DoS)
MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB per file
MAX_TOTAL_SCAN_BYTES: int = 50 * 1024 * 1024  # 50 MB total per scan


class PathSecurityError(ValueError):
    """Raised when a path violates security boundaries (e.g. traversal attempt)."""
    pass


class FileTooLargeError(ValueError):
    """Raised when an uploaded file exceeds the configured size limit."""
    pass


def validate_safe_path(target_path: Union[str, Path], base_dir: Union[str, Path]) -> Path:
    """Validate that target_path resolves strictly within base_dir.

    Args:
        target_path: Path to validate (can be relative or absolute).
        base_dir: Root directory that must contain target_path.

    Returns:
        Resolved canonical Path.

    Raises:
        PathSecurityError: If target_path escapes base_dir or contains null bytes.
    """
    raw_str = str(target_path)
    if "\0" in raw_str:
        raise PathSecurityError(f"Null byte detected in path: {raw_str!r}")

    base_resolved = Path(base_dir).resolve()
    try:
        target_resolved = (base_resolved / target_path).resolve()
    except (ValueError, RuntimeError) as exc:
        raise PathSecurityError(f"Invalid path structure: {raw_str}") from exc

    # Ensure target is strictly inside base directory
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise PathSecurityError(
            f"Directory traversal detected: '{target_path}' resolves to '{target_resolved}', "
            f"which is outside base directory '{base_resolved}'"
        )

    return target_resolved


def is_ignored_directory(dir_name: str, custom_ignore: Optional[Set[str]] = None) -> bool:
    """Check if a directory name matches standard or custom ignore rules."""
    ignored = DEFAULT_IGNORE_DIRS if custom_ignore is None else (DEFAULT_IGNORE_DIRS | custom_ignore)
    return dir_name in ignored or dir_name.startswith(".")

