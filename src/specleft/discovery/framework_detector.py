# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Framework detection orchestrator and shared detection context."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import cast

from specleft.discovery.file_index import FileIndex
from specleft.discovery.frameworks import io
from specleft.discovery.frameworks.python.policies import PythonFrameworkPolicy
from specleft.discovery.frameworks.types import LanguagePolicy
from specleft.discovery.frameworks.typescript.policies import TypeScriptFrameworkPolicy
from specleft.discovery.models import SupportedLanguage


class FrameworkDetector:
    """Detect test frameworks by combining manifest and file-pattern signals."""

    def __init__(self, policies: tuple[LanguagePolicy, ...] | None = None) -> None:
        self._policies = policies if policies is not None else _default_policies()

    def detect(
        self,
        root: Path,
        file_index: FileIndex,
    ) -> dict[SupportedLanguage, list[str]]:
        """Detect framework names by language."""
        ctx = DetectionContext(root=root, file_index=file_index)
        detected: dict[SupportedLanguage, list[str]] = {}

        for policy in self._policies:
            frameworks = policy.detect(ctx)
            if frameworks:
                detected[policy.language] = frameworks

        return detected


@dataclass(frozen=True)
class DetectionContext:
    """Cached evidence shared by all framework policies and rules."""

    root: Path
    file_index: FileIndex

    @cached_property
    def pyproject(self) -> dict[str, object]:
        return io.load_pyproject(self.root)

    @cached_property
    def package_json(self) -> dict[str, object]:
        return io.load_package_json(self.root)

    @cached_property
    def requirements_lines(self) -> tuple[str, ...]:
        lines: list[str] = []
        for requirements_file in sorted(self.root.glob("requirements*.txt")):
            raw = io.read_text(requirements_file)
            if raw is None:
                continue
            lines.extend(line.strip().lower() for line in raw.splitlines())
        return tuple(lines)

    @cached_property
    def python_test_files(self) -> list[Path]:
        return [
            path
            for path in self.file_index.files_matching("test_*.py")
            if io.is_project_file(path)
        ]

    @cached_property
    def conftest_files(self) -> list[Path]:
        return [
            path
            for path in self.file_index.files_matching("conftest.py")
            if io.is_project_file(path)
        ]

    @cached_property
    def has_unittest_testcases(self) -> bool:
        for python_file in self.python_test_files:
            source = io.read_text(self.root / python_file)
            if source is None:
                continue
            if io.contains_unittest_testcase(source):
                return True

        return False

    @cached_property
    def typescript_manifest_frameworks(self) -> set[str]:
        return io.manifest_typescript_frameworks(self.package_json)

    @cached_property
    def jest_configs(self) -> list[Path]:
        return self.file_index.files_matching(
            "jest.config.js",
            "jest.config.ts",
            "jest.config.mjs",
            "jest.config.cjs",
            "jest.config.json",
        )

    @cached_property
    def vite_configs(self) -> list[Path]:
        return self.file_index.files_matching(
            "vite.config.js",
            "vite.config.ts",
            "vite.config.mjs",
            "vite.config.cjs",
        )

    @cached_property
    def vitest_tests(self) -> list[Path]:
        return self.file_index.files_matching(
            "*.test.ts",
            "*.test.tsx",
            "*.test.js",
            "*.test.jsx",
        )


def _default_policies() -> tuple[LanguagePolicy, ...]:
    return cast(
        tuple[LanguagePolicy, ...],
        (PythonFrameworkPolicy(), TypeScriptFrameworkPolicy()),
    )


__all__ = ["DetectionContext", "FrameworkDetector"]
