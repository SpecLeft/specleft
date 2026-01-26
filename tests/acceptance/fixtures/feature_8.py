"""Feature 8: Agent Contract Introspection fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles, FeatureOnlyFiles

_FEATURE_8_TEST = """\
# Feature: Test Feature
priority: medium

## Scenarios

### Scenario: Basic test
- Given a precondition
- When an action occurs
- Then expected result
"""

_FEATURE_8_AUTH = """\
# Feature: Auth
priority: high

## Scenarios

### Scenario: User login
- Given valid credentials
- When login is attempted
- Then user is authenticated
"""


@pytest.fixture
def feature_8_contract(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Minimal feature for testing `specleft contract` output."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-test.md"
    feature_path.write_text(_FEATURE_8_TEST)

    test_path = tests_dir / "test_feature_test.py"
    test_path.write_text("")

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
def feature_8_contract_minimal(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureOnlyFiles]]:
    """Minimal feature for testing `specleft contract test` side-effect behavior.

    Only creates a feature file, no tests directory. Used by tests that verify
    `contract test` does not create files as side effects.
    """
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    feature_path = features_dir / "feature-test.md"
    feature_path.write_text(_FEATURE_8_TEST)

    yield (
        runner,
        workspace,
        FeatureOnlyFiles(
            feature_path=feature_path,
            features_dir=features_dir,
        ),
    )


@pytest.fixture
def feature_8_contract_test(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing `specleft contract test` compliance."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-auth.md"
    feature_path.write_text(_FEATURE_8_AUTH)

    test_path = tests_dir / "test_feature_auth.py"
    test_path.write_text("")

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
