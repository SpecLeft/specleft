# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""IO and parsing helpers for framework detection."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_PYTEST_REQUIREMENT_PATTERN = re.compile(r"^\s*pytest(?:\b|[<>=!~])")
_UNITTEST_CLASS_PATTERN = re.compile(
    r"class\s+\w+\s*\(\s*(?:\w+\.)?TestCase\s*\)\s*:",
)


def is_pytest_requirement_line(line: str) -> bool:
    """Return whether a requirements line references pytest."""
    return _PYTEST_REQUIREMENT_PATTERN.match(line) is not None


def contains_unittest_testcase(source: str) -> bool:
    """Return whether source contains an explicit unittest TestCase class."""
    if "TestCase" not in source:
        return False
    if "unittest.TestCase" in source:
        return True
    return _UNITTEST_CLASS_PATTERN.search(source) is not None


def manifest_signals_pytest(pyproject: dict[str, Any]) -> bool:
    """Return whether pyproject manifest indicates pytest usage."""
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


def manifest_typescript_frameworks(package_json: dict[str, Any]) -> set[str]:
    """Return TS/JS frameworks inferred from package.json dependencies."""
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


def read_text(path: Path) -> str | None:
    """Read UTF-8 text from path, returning None on file/decode errors."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None
    except UnicodeDecodeError:
        return None


def load_pyproject(root: Path) -> dict[str, Any]:
    """Load pyproject TOML as dict, returning {} when unavailable/invalid."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}

    raw = read_text(path)
    if raw is None:
        return {}

    toml_module = resolve_toml_loader()
    if toml_module is None:
        return {}

    try:
        parsed = toml_module.loads(raw)
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def load_package_json(root: Path) -> dict[str, Any]:
    """Load package.json as dict, returning {} when unavailable/invalid."""
    path = root / "package.json"
    if not path.is_file():
        return {}

    raw = read_text(path)
    if raw is None:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def is_project_file(path: Path) -> bool:
    """Return whether an indexed path should be considered project-owned."""
    if not path.parts:
        return False
    if path.parts[0].startswith("."):
        return False
    return "site-packages" not in path.parts


def resolve_toml_loader() -> Any | None:
    """Return TOML module object (`tomllib` or fallback `tomli`)."""
    try:
        import tomllib

        return tomllib
    except ModuleNotFoundError:
        try:
            import tomli  # type: ignore[import-not-found]

            return tomli
        except ModuleNotFoundError:
            return None
