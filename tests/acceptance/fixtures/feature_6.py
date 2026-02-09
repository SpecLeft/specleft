"""Feature 6: CI Experience & Messaging fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_6_ORDER = """\
# Feature: Order Processing
priority: high

## Scenarios

### Scenario: Process critical order
priority: critical

- Given a pending order
- When processing is triggered
- Then order is fulfilled

### Scenario: Archive old orders
priority: low

- Given orders older than 90 days
- When archival runs
- Then orders are archived
"""

_TEST_6_ORDER_LOW_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-order-processing", scenario_id="archive-old-orders")
def test_archive_old_orders():
    """Only low priority implemented - critical is missing."""
    pass
'''

_FEATURE_6_NOTIFICATION = """\
# Feature: Notification Service
priority: high

## Scenarios

### Scenario: Send critical alert
priority: critical

- Given a critical event
- When alert is triggered
- Then notification is sent

### Scenario: Log notification history
priority: medium

- Given notifications sent
- When history is queried
- Then records are returned
"""

_TEST_6_NOTIFICATION_MEDIUM_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-notification-service", scenario_id="log-notification-history")
def test_log_notification_history():
    """Only medium priority implemented."""
    pass
'''


@pytest.fixture
def feature_6_ci_failure(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with unimplemented critical scenario for CI failure messaging test."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-order-processing.md"
    feature_path.write_text(_FEATURE_6_ORDER)

    test_path = tests_dir / "test_orders.py"
    test_path.write_text(_TEST_6_ORDER_LOW_ONLY)

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
def feature_6_doc_links(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing documentation/support link presence on CI failure."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-notification-service.md"
    feature_path.write_text(_FEATURE_6_NOTIFICATION)

    test_path = tests_dir / "test_notifications.py"
    test_path.write_text(_TEST_6_NOTIFICATION_MEDIUM_ONLY)

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
