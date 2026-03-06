# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""User-facing configuration for discovery orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specleft.discovery.file_index import DEFAULT_EXCLUDE_DIRS


@dataclass(frozen=True)
class DiscoveryConfig:
    """Configuration for discovery pipeline and miners."""

    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS
    source_dirs: tuple[str, ...] = ("src", "lib", "app", "core")
    max_git_commits: int = 200

    @classmethod
    def from_pyproject(cls, root: Path) -> DiscoveryConfig:
        """Load discovery config from ``[tool.specleft.discovery]`` if present."""
        data = _load_pyproject(root)
        section = _extract_discovery_section(data)
        if not section:
            return cls.default()

        default = cls.default()

        raw_exclude_dirs = section.get("exclude_dirs")
        exclude_dirs = (
            frozenset(value for value in raw_exclude_dirs if isinstance(value, str))
            if isinstance(raw_exclude_dirs, list)
            else default.exclude_dirs
        )
        if not exclude_dirs:
            exclude_dirs = default.exclude_dirs

        raw_source_dirs = section.get("source_dirs")
        source_dirs = (
            tuple(value for value in raw_source_dirs if isinstance(value, str))
            if isinstance(raw_source_dirs, list)
            else default.source_dirs
        )
        if not source_dirs:
            source_dirs = default.source_dirs

        raw_max_git_commits = section.get("max_git_commits")
        if isinstance(raw_max_git_commits, int) and raw_max_git_commits > 0:
            max_git_commits = raw_max_git_commits
        else:
            max_git_commits = default.max_git_commits

        return cls(
            exclude_dirs=exclude_dirs,
            source_dirs=source_dirs,
            max_git_commits=max_git_commits,
        )

    @classmethod
    def default(cls) -> DiscoveryConfig:
        """Return config with all defaults."""
        return cls()


def _extract_discovery_section(data: dict[str, Any]) -> dict[str, Any]:
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return {}

    specleft = tool.get("specleft")
    if not isinstance(specleft, dict):
        return {}

    discovery = specleft.get("discovery")
    if not isinstance(discovery, dict):
        return {}

    return discovery


def _load_pyproject(root: Path) -> dict[str, Any]:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        return {}

    try:
        raw = pyproject_path.read_bytes()
    except OSError:
        return {}

    toml_module = _resolve_toml_loader()
    if toml_module is None:
        return {}

    try:
        parsed = toml_module.loads(raw.decode("utf-8"))
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def _resolve_toml_loader() -> Any | None:
    try:
        import tomllib

        return tomllib
    except ModuleNotFoundError:
        try:
            import tomli

            return tomli
        except ModuleNotFoundError:
            return None
