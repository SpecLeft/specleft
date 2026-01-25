"""Common fixtures and dataclasses shared across all acceptance tests."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from click.testing import CliRunner


@dataclass
class FeatureFiles:
    """Paths to feature-related files created by acceptance test fixtures."""

    feature_path: Path
    test_path: Path
    features_dir: Path
    tests_dir: Path


@dataclass
class FeatureOnlyFiles:
    """Paths to feature-only files (no test files) for contract verification tests."""

    feature_path: Path
    features_dir: Path


@dataclass
class PrdFiles:
    """Paths to PRD-related files for planning mode tests."""

    prd_path: Path
    features_dir: Path


@pytest.fixture
def acceptance_workspace() -> Iterator[tuple[CliRunner, Path]]:
    """Provide an isolated workspace with a default features directory."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        workspace = Path.cwd()
        (workspace / "features").mkdir(exist_ok=True)
        yield runner, workspace
