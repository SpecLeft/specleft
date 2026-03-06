# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Filesystem abstraction for discovery miners."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from specleft.discovery.language_registry import SUPPORTED_EXTENSIONS
from specleft.discovery.models import SupportedLanguage

DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".eggs",
        "*.egg-info",
    }
)


class FileIndex:
    """Walk the repository once and provide filtered views."""

    def __init__(
        self,
        root: Path,
        exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS,
    ) -> None:
        self._root = root
        self._files: list[Path] = []
        self._by_language: dict[SupportedLanguage, list[Path]] = {}
        self._by_extension: dict[str, list[Path]] = {}
        self._exclude_dirs = exclude_dirs
        self._build()

    @property
    def root(self) -> Path:
        """Project root."""
        return self._root

    @property
    def total_files(self) -> int:
        """Number of discovered files."""
        return len(self._files)

    def files_by_language(self, lang: SupportedLanguage) -> list[Path]:
        """Return all files for a language."""
        return sorted(
            self._by_language.get(lang, []),
            key=lambda value: value.as_posix(),
        )

    def files_by_extension(self, *exts: str) -> list[Path]:
        """Return files matching any extension."""
        output: list[Path] = []
        for ext in exts:
            output.extend(self._by_extension.get(ext.lower(), []))
        return sorted(output, key=lambda value: value.as_posix())

    def files_matching(self, *patterns: str) -> list[Path]:
        """Return files whose names match any glob pattern."""
        matched: list[Path] = []
        for file_path in self._files:
            for pattern in patterns:
                if fnmatch.fnmatch(file_path.name, pattern):
                    matched.append(file_path)
                    break
        return sorted(matched, key=lambda value: value.as_posix())

    def files_under(self, *dirs: str) -> list[Path]:
        """Return files under the specified directory prefixes."""
        return sorted(
            [
                file_path
                for file_path in self._files
                if any(
                    file_path.parts[: len(Path(prefix).parts)]
                    == tuple(Path(prefix).parts)
                    for prefix in dirs
                )
            ],
            key=lambda value: value.as_posix(),
        )

    def _build(self) -> None:
        root = self._root.resolve()
        for current_root, dirnames, filenames in os.walk(root):
            dirnames.sort()
            filenames.sort()
            path_dirnames = list(dirnames)
            filtered: list[str] = []
            for dirname in path_dirnames:
                if self._is_excluded_dir(dirname):
                    continue
                filtered.append(dirname)
            dirnames[:] = filtered

            for filename in filenames:
                file_path = Path(current_root, filename)
                if file_path.is_dir():
                    continue
                rel_path = file_path.relative_to(root)
                self._files.append(rel_path)

                extension = rel_path.suffix.lower()
                self._by_extension.setdefault(extension, []).append(rel_path)

                language = SUPPORTED_EXTENSIONS.get(extension)
                if language is not None:
                    self._by_language.setdefault(language, []).append(rel_path)

    def _is_excluded_dir(self, dirname: str) -> bool:
        if dirname in self._exclude_dirs:
            return True
        return any(fnmatch.fnmatch(dirname, pattern) for pattern in self._exclude_dirs)
