# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for discovery pipeline configuration."""

from __future__ import annotations

from pathlib import Path

from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.file_index import DEFAULT_EXCLUDE_DIRS


def test_discovery_config_from_pyproject_loads_custom_values(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("""
[tool.specleft.discovery]
exclude_dirs = [".git", "node_modules", "dist"]
source_dirs = ["src", "lib", "service"]
max_git_commits = 50
""".strip())

    config = DiscoveryConfig.from_pyproject(tmp_path)

    assert config.exclude_dirs == frozenset({".git", "node_modules", "dist"})
    assert config.source_dirs == ("src", "lib", "service")
    assert config.max_git_commits == 50


def test_discovery_config_from_pyproject_uses_defaults_when_section_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text("""
[tool.black]
line-length = 88
""".strip())

    config = DiscoveryConfig.from_pyproject(tmp_path)

    assert config.exclude_dirs == DEFAULT_EXCLUDE_DIRS
    assert config.source_dirs == ("src", "lib", "app", "core")
    assert config.max_git_commits == 200


def test_discovery_config_default_returns_default_values() -> None:
    config = DiscoveryConfig.default()

    assert config.exclude_dirs == DEFAULT_EXCLUDE_DIRS
    assert config.source_dirs == ("src", "lib", "app", "core")
    assert config.max_git_commits == 200


def test_discovery_config_invalid_values_fall_back_to_defaults(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("""
[tool.specleft.discovery]
exclude_dirs = []
source_dirs = []
max_git_commits = -1
""".strip())

    config = DiscoveryConfig.from_pyproject(tmp_path)

    assert config.exclude_dirs == DEFAULT_EXCLUDE_DIRS
    assert config.source_dirs == ("src", "lib", "app", "core")
    assert config.max_git_commits == 200
