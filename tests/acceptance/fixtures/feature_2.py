"""Feature 2: Specification Format fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_2_MINIMAL = """\
# Feature: Minimal Feature

## Scenarios

### Scenario: Basic scenario
priority: high

- Given a precondition
- When an action occurs
- Then an expected result
"""

_FEATURE_2_WITH_METADATA = """\
---
confidence: high
owner: test-team
component: auth-service
tags:
  - security
  - login
---
# Feature: Feature With Metadata

## Scenarios

### Scenario: Login with metadata
priority: critical

- Given a user with credentials
- When they attempt login
- Then they are authenticated
"""

_FEATURE_2_WITHOUT_METADATA = """\
# Feature: Feature Without Metadata

## Scenarios

### Scenario: Basic operation
priority: medium

- Given a system state
- When an operation occurs
- Then state changes
"""


@pytest.fixture
def feature_2_minimal(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Minimal valid feature file with one scenario."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "minimal-feature.md"
    feature_path.write_text(_FEATURE_2_MINIMAL)

    test_path = tests_dir / "test_minimal_feature.py"
    test_path.write_text("")  # Empty test file

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=feature_path,
            test_path=test_path,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )


@pytest.fixture
def feature_2_metadata_variants(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles, FeatureFiles]]:
    """Feature files with and without metadata for testing metadata handling."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Feature WITH metadata
    with_meta_path = features_dir / "feature-with-metadata.md"
    with_meta_path.write_text(_FEATURE_2_WITH_METADATA)
    with_meta_test = tests_dir / "test_feature_with_metadata.py"
    with_meta_test.write_text("")

    # Feature WITHOUT metadata
    without_meta_path = features_dir / "feature-without-metadata.md"
    without_meta_path.write_text(_FEATURE_2_WITHOUT_METADATA)
    without_meta_test = tests_dir / "test_feature_without_metadata.py"
    without_meta_test.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=with_meta_path,
            test_path=with_meta_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
        FeatureFiles(
            feature_path=without_meta_path,
            test_path=without_meta_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )
