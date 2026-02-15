# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared version resolution for SpecLeft."""

from __future__ import annotations

import re
from importlib import metadata
from pathlib import Path

PACKAGE_NAME = "specleft"
DEFAULT_VERSION = "0.0.0"


def _version_from_metadata(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _version_from_pyproject(pyproject_path: Path) -> str | None:
    if not pyproject_path.exists():
        return None
    try:
        content = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return None
    project_match = re.search(
        r"^\[project\]\s*(.*?)(?=^\[[^\]]+\]|\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not project_match:
        return None
    version_match = re.search(
        r'^\s*version\s*=\s*"([^"]+)"\s*$',
        project_match.group(1),
        flags=re.MULTILINE,
    )
    if not version_match:
        return None
    return version_match.group(1)


def resolve_version(package_name: str = PACKAGE_NAME) -> str:
    package_version = _version_from_metadata(package_name)
    if package_version:
        return package_version
    pyproject_version = _version_from_pyproject(
        Path(__file__).resolve().parents[2] / "pyproject.toml"
    )
    if pyproject_version:
        return pyproject_version
    return DEFAULT_VERSION


SPECLEFT_VERSION = resolve_version()
