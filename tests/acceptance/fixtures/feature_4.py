"""Feature 4: Status & Coverage Inspection fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_4_USER_AUTH = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User logs in successfully
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

_TEST_4_USER_AUTH_PARTIAL = '''\
from specleft import specleft

@specleft(feature_id="feature-user-authentication", scenario_id="user-logs-in-successfully")
def test_user_logs_in_successfully():
    """This test IS implemented (no skip=True)."""
    pass
'''

_FEATURE_4_PAYMENT = """\
# Feature: Payment Processing
priority: high

## Scenarios

### Scenario: Process credit card payment
priority: critical

- Given a valid credit card
- When payment is submitted
- Then transaction succeeds

### Scenario: Process refund
priority: high

- Given a completed transaction
- When refund is requested
- Then amount is returned

### Scenario: Payment history
priority: low

- Given a user account
- When viewing history
- Then transactions are listed
"""

_TEST_4_PAYMENT_PARTIAL = '''\
from specleft import specleft

@specleft(feature_id="feature-payment-processing", scenario_id="process-credit-card-payment")
def test_process_credit_card_payment():
    """Implemented test."""
    pass

@specleft(feature_id="feature-payment-processing", scenario_id="process-refund")
def test_process_refund():
    """Implemented test."""
    pass

# Note: payment-history is NOT implemented
'''

_FEATURE_4_AUTH_FILTER = """\
# Feature: User Authentication
priority: high

## Scenarios

### Scenario: User login
priority: critical

- Given a user
- When they log in
- Then success

### Scenario: User signup
priority: high

- Given a new user
- When they sign up
- Then account created
"""

_FEATURE_4_BILLING = """\
# Feature: Billing System
priority: high

## Scenarios

### Scenario: Generate invoice
priority: critical

- Given a completed order
- When billing runs
- Then invoice is generated

### Scenario: Apply discount
priority: medium

- Given a coupon code
- When applied
- Then price is reduced
"""

_TEST_4_AUTH_ONLY = """\
from specleft import specleft

@specleft(feature_id="feature-auth", scenario_id="user-login")
def test_user_login():
    pass
"""


@pytest.fixture
def feature_4_unimplemented(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with partial implementation for testing --unimplemented filter."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-user-authentication.md"
    feature_path.write_text(_FEATURE_4_USER_AUTH)

    test_path = tests_dir / "test_feature_user_authentication.py"
    test_path.write_text(_TEST_4_USER_AUTH_PARTIAL)

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
def feature_4_implemented(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with partial implementation for testing --implemented filter."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    feature_path = features_dir / "feature-payment-processing.md"
    feature_path.write_text(_FEATURE_4_PAYMENT)

    test_path = tests_dir / "test_feature_payment_processing.py"
    test_path.write_text(_TEST_4_PAYMENT_PARTIAL)

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
def feature_4_multi_feature_filter(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles, FeatureFiles]]:
    """Multiple features for testing --feature filter."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Auth feature
    auth_path = features_dir / "feature-auth.md"
    auth_path.write_text(_FEATURE_4_AUTH_FILTER)
    auth_test = tests_dir / "test_feature_auth.py"
    auth_test.write_text(_TEST_4_AUTH_ONLY)

    # Billing feature (no tests)
    billing_path = features_dir / "feature-billing.md"
    billing_path.write_text(_FEATURE_4_BILLING)
    billing_test = tests_dir / "test_feature_billing.py"
    billing_test.write_text("")

    yield (
        runner,
        workspace,
        FeatureFiles(
            feature_path=auth_path,
            test_path=auth_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
        FeatureFiles(
            feature_path=billing_path,
            test_path=billing_test,
            features_dir=features_dir,
            tests_dir=tests_dir,
        ),
    )
