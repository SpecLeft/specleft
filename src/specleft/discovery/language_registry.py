# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Language detection and parser abstractions for discovery miners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specleft.discovery.models import SupportedLanguage

SUPPORTED_EXTENSIONS: dict[str, SupportedLanguage] = {
    ".py": SupportedLanguage.PYTHON,
    ".ts": SupportedLanguage.TYPESCRIPT,
    ".tsx": SupportedLanguage.TYPESCRIPT,
    ".js": SupportedLanguage.JAVASCRIPT,
    ".jsx": SupportedLanguage.JAVASCRIPT,
    ".mjs": SupportedLanguage.JAVASCRIPT,
}


class LanguageRegistry:
    """Cache language grammars and expose shared parse operations."""

    def __init__(self) -> None:
        self._language_cache: dict[SupportedLanguage, Any] = {}
        self._parser_cache: dict[SupportedLanguage, Any] = {}

    def detect_language(self, file_path: Path) -> SupportedLanguage | None:
        """Return the detected language by file extension, or `None`."""
        return SUPPORTED_EXTENSIONS.get(file_path.suffix.lower())

    def parse(self, file_path: Path) -> tuple[Any, SupportedLanguage] | None:
        """Parse bytes from disk and return ``(root_node, language)``.

        Unsupported extensions, parse failures, or malformed files return ``None``.
        """
        language = self.detect_language(file_path)
        if language is None:
            return None

        try:
            source = file_path.read_bytes()
        except OSError:
            return None

        try:
            root_node = self.parse_source(source, language)
        except Exception:
            return None

        if root_node is None:
            return None
        return root_node, language

    def parse_source(self, source: bytes, language: SupportedLanguage) -> Any | None:
        """Parse raw source bytes directly and return tree root node."""
        parser = self._parser_for(language)
        if parser is None:
            return None

        try:
            tree = parser.parse(source)
        except Exception:
            return None

        root_node = tree.root_node
        if getattr(root_node, "has_error", False):
            return None

        return root_node

    def _parser_for(self, language: SupportedLanguage) -> Any | None:
        parser = self._parser_cache.get(language)
        if parser is not None:
            return parser

        language_obj = self._language_for(language)
        if language_obj is None:
            return None

        try:
            from tree_sitter import Parser  # type: ignore[import-untyped]

            parser = Parser()
            parser.set_language(language_obj)
            self._parser_cache[language] = parser
            return parser
        except Exception:
            return None

    def _language_for(self, language: SupportedLanguage) -> Any | None:
        if language in self._language_cache:
            return self._language_cache[language]

        if language == SupportedLanguage.PYTHON:
            try:
                import tree_sitter_python  # type: ignore[import-not-found]

                language_obj = tree_sitter_python.language()
            except Exception:
                return None
        elif language in (SupportedLanguage.TYPESCRIPT, SupportedLanguage.JAVASCRIPT):
            try:
                import tree_sitter_typescript  # type: ignore[import-not-found]

                language_obj = tree_sitter_typescript.language_typescript()
            except Exception:
                return None
        else:
            return None

        self._language_cache[language] = language_obj
        return language_obj
