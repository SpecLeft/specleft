"""Feature 3: Canonical JSON Output fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_3_USER_AUTH = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User logs in successfully
priority: critical

- Given a registered user
- When they submit valid credentials
- Then they are authenticated

### Scenario: User logout
priority: medium

- Given an authenticated user
- When they click logout
- Then the session is terminated
"""

_TEST_3_USER_AUTH = """\
from specleft import specleft

@specleft(feature_id="feature-user-authentication", scenario_id="user-logs-in-successfully")
def test_user_logs_in_successfully():
    pass
"""

_FEATURE_3_SLUGIFICATION = """\
# Feature: Slugification Test
priority: high

## Scenarios

### Scenario: User Logs In Successfully
priority: high

- Given a user
- When they log in
- Then success

### Scenario: Handle Edge-Case (Special Characters!)
priority: medium

- Given edge case
- When handled
- Then pass

### Scenario: Multi   Word   Spaces
priority: low

- Given words
- When spaced
- Then normalized
"""


@pytest.fixture
def feature_3_canonical_json(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with scenarios for testing canonical JSON output shape."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-user-authentication.md"
    feature_path.write_text(_FEATURE_3_USER_AUTH)

    test_path = tests_dir / "test_feature_user_authentication.py"
    test_path.write_text(_TEST_3_USER_AUTH)

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
def feature_3_slugification(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with varied title formats for testing ID slugification."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / "features"
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-slugification-test.md"
    feature_path.write_text(_FEATURE_3_SLUGIFICATION)

    test_path = tests_dir / "test_feature_slugification_test.py"
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
