"""Base parser abstraction for SpecCraft AI.

Defines the contract for framework-specific static AST analysis adapters
(FastAPI adapter first, with Express/tree-sitter adapter slot for Level 4 Stretch).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from speccraft.models import ExtractionResult, SourceFile


class BaseParser(ABC):
    """Abstract base class for all language and framework AST parsers."""

    @abstractmethod
    def can_parse(self, source_file: SourceFile) -> bool:
        """Return True if this parser can handle the given source file."""
        pass

    @abstractmethod
    def parse_files(self, source_files: List[SourceFile]) -> ExtractionResult:
        """Parse a list of source files and extract endpoints, schemas, and warnings.

        Must NEVER execute user code. All analysis must be performed via static AST inspection.
        """
        pass

