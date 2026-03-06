# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Framework detection for discovery pipeline and onboarding flows."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from specleft.discovery.file_index import FileIndex
from specleft.discovery.models import SupportedLanguage

_PYTEST_REQUIREMENT_PATTERN = re.compile(r"^\s*pytest(?:\b|[<>=!~])")
_UNITTEST_CLASS_PATTERN = re.compile(
    r"class\s+\w+\s*\(\s*(?:\w+\.)?TestCase\s*\)\s*:",
)


class FrameworkDetector:
    """Detect test frameworks by combining manifests and file patterns."""

    def detect(
        self,
        root: Path,
        file_index: FileIndex,
    ) -> dict[SupportedLanguage, list[str]]:
        """Detect framework names by language."""
        detected: dict[SupportedLanguage, list[str]] = {}

        python_frameworks = self._detect_python_frameworks(root, file_index)
        if python_frameworks:
            detected[SupportedLanguage.PYTHON] = python_frameworks

        typescript_frameworks = self._detect_typescript_frameworks(root, file_index)
        if typescript_frameworks:
            detected[SupportedLanguage.TYPESCRIPT] = typescript_frameworks

        return detected

    def _detect_python_frameworks(self, root: Path, file_index: FileIndex) -> list[str]:
        pyproject = _load_pyproject(root)
        manifest_pytest = _manifest_signals_pytest(pyproject)

        requirements_pytest = False
        requirements_unittest = False
        for requirements_file in sorted(root.glob("requirements*.txt")):
            raw = _read_text(requirements_file)
            if raw is None:
                continue
            for line in raw.splitlines():
                normalized = line.strip().lower()
                if _PYTEST_REQUIREMENT_PATTERN.match(normalized):
                    requirements_pytest = True
                if "unittest" in normalized:
                    requirements_unittest = True

        pytest_tests = [
            path
            for path in file_index.files_matching("test_*.py")
            if _is_project_file(path)
        ]
        conftest_files = file_index.files_matching("conftest.py")
        pytest_confirmed = bool(pytest_tests or conftest_files)

        # Explicit pytest config without test file patterns is treated as ambiguous.
        if manifest_pytest and not pytest_tests:
            return ["unknown"]

        frameworks: list[str] = []
        if (
            manifest_pytest or requirements_pytest or pytest_confirmed
        ) and pytest_confirmed:
            frameworks.append("pytest")

        unittest_confirmed = self._has_unittest_testcases(root, file_index)
        if (requirements_unittest or unittest_confirmed) and unittest_confirmed:
            frameworks.append("unittest")

        return frameworks

    def _detect_typescript_frameworks(
        self,
        root: Path,
        file_index: FileIndex,
    ) -> list[str]:
        package_json = _load_package_json(root)
        manifest_frameworks = _manifest_typescript_frameworks(package_json)

        pattern_frameworks: set[str] = set()
        jest_configs = file_index.files_matching(
            "jest.config.js",
            "jest.config.ts",
            "jest.config.mjs",
            "jest.config.cjs",
            "jest.config.json",
        )
        if jest_configs:
            pattern_frameworks.add("jest")

        vite_configs = file_index.files_matching(
            "vite.config.js",
            "vite.config.ts",
            "vite.config.mjs",
            "vite.config.cjs",
        )
        vitest_tests = file_index.files_matching(
            "*.test.ts",
            "*.test.tsx",
            "*.test.js",
            "*.test.jsx",
        )
        if vite_configs and vitest_tests:
            pattern_frameworks.add("vitest")

        # File patterns are the source of truth whenever they are present.
        frameworks = pattern_frameworks if pattern_frameworks else manifest_frameworks

        return [name for name in ("jest", "vitest") if name in frameworks]

    def _has_unittest_testcases(self, root: Path, file_index: FileIndex) -> bool:
        for python_file in file_index.files_matching("test_*.py"):
            if not _is_project_file(python_file):
                continue
            source = _read_text(root / python_file)
            if source is None:
                continue
            if "TestCase" not in source:
                continue
            if "unittest.TestCase" in source or _UNITTEST_CLASS_PATTERN.search(source):
                return True

        return False


def _manifest_signals_pytest(pyproject: dict[str, Any]) -> bool:
    tool = pyproject.get("tool")
    if isinstance(tool, dict):
        pytest_tool = tool.get("pytest")
        if isinstance(pytest_tool, dict) and isinstance(
            pytest_tool.get("ini_options"),
            dict,
        ):
            return True

    build_system = pyproject.get("build-system")
    if not isinstance(build_system, dict):
        return False

    requires = build_system.get("requires")
    if not isinstance(requires, list):
        return False

    return any(isinstance(dep, str) and "pytest" in dep.lower() for dep in requires)


def _manifest_typescript_frameworks(package_json: dict[str, Any]) -> set[str]:
    framework_names: set[str] = set()
    dependency_groups = (
        package_json.get("dependencies"),
        package_json.get("devDependencies"),
    )

    for group in dependency_groups:
        if not isinstance(group, dict):
            continue

        lower_keys = {str(key).lower() for key in group}
        if {"jest", "@jest/core"} & lower_keys:
            framework_names.add("jest")
        if {"vitest", "@vitest/ui"} & lower_keys:
            framework_names.add("vitest")

    return framework_names


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None
    except UnicodeDecodeError:
        return None


def _load_pyproject(root: Path) -> dict[str, Any]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}

    raw = _read_text(path)
    if raw is None:
        return {}

    toml_module = _resolve_toml_loader()
    if toml_module is None:
        return {}

    try:
        parsed = toml_module.loads(raw)
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def _load_package_json(root: Path) -> dict[str, Any]:
    path = root / "package.json"
    if not path.is_file():
        return {}

    raw = _read_text(path)
    if raw is None:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def _is_project_file(path: Path) -> bool:
    if not path.parts:
        return False
    if path.parts[0].startswith("."):
        return False
    return "site-packages" not in path.parts


def _resolve_toml_loader() -> Any | None:
    try:
        import tomllib

        return tomllib
    except ModuleNotFoundError:
        try:
            import tomli  # type: ignore[import-not-found]

            return tomli
        except ModuleNotFoundError:
            return None
