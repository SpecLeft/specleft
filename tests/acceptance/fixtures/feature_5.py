"""Feature 5: Policy Enforcement fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_5_USER_AUTH = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User login critical
priority: critical

- Given a registered user
- When they submit valid credentials
- Then they are authenticated

### Scenario: User password reset
priority: high

- Given a user forgot password
- When they request reset
- Then email is sent

### Scenario: User logout
priority: medium

- Given an authenticated user
- When they click logout
- Then session is terminated
"""

_TEST_5_MEDIUM_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-user-authentication", scenario_id="user-logout")
def test_user_logout():
    """Only medium priority implemented."""
    pass
'''

_FEATURE_5_PAYMENT = """\
# Feature: Payment Processing
priority: high

## Scenarios

### Scenario: Process payment
priority: critical

- Given a valid payment method
- When payment is submitted
- Then transaction succeeds

### Scenario: Refund payment
priority: high

- Given a completed transaction
- When refund is requested
- Then amount is returned

### Scenario: View payment history
priority: low

- Given a user account
- When viewing history
- Then transactions are listed
"""

_TEST_5_PAYMENT_FULL = '''\
from specleft import specleft

@specleft(feature_id="feature-payment-processing", scenario_id="process-payment")
def test_process_payment():
    """Critical scenario implemented."""
    pass

@specleft(feature_id="feature-payment-processing", scenario_id="refund-payment")
def test_refund_payment():
    """High priority scenario implemented."""
    pass

# Note: view-payment-history (low priority) intentionally not implemented
'''

_FEATURE_5_USER_MGMT = """\
# Feature: User Management
priority: high

## Scenarios

### Scenario: Create user
priority: critical

- Given an admin
- When creating a user
- Then user is created
"""


@pytest.fixture
def feature_5_policy_violation(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with unimplemented critical/high scenarios for policy violation test."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-user-authentication.md"
    feature_path.write_text(_FEATURE_5_USER_AUTH)

    test_path = tests_dir / "test_auth.py"
    test_path.write_text(_TEST_5_MEDIUM_ONLY)

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
def feature_5_policy_satisfied(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with all critical/high scenarios implemented for passing enforcement."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-payment-processing.md"
    feature_path.write_text(_FEATURE_5_PAYMENT)

    test_path = tests_dir / "test_payment.py"
    test_path.write_text(_TEST_5_PAYMENT_FULL)

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
def feature_5_invalid_signature(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing invalid policy signature rejection."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-user-management.md"
    feature_path.write_text(_FEATURE_5_USER_MGMT)

    test_path = tests_dir / "test_user_management.py"
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
