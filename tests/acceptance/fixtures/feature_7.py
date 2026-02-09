"""Feature 7: Autonomous Agent Test Execution fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_7_API_GATEWAY = """\
# Feature: API Gateway
priority: high

## Scenarios

### Scenario: Authenticate request
priority: critical

- Given an incoming API request
- When authentication is checked
- Then valid tokens are accepted

### Scenario: Rate limit exceeded
priority: high

- Given a client exceeding rate limits
- When request is received
- Then 429 response is returned

### Scenario: Log request metrics
priority: low

- Given any API request
- When processing completes
- Then metrics are logged
"""

_TEST_7_API_GATEWAY_LOW_ONLY = '''\
from specleft import specleft

@specleft(feature_id="feature-api-gateway", scenario_id="log-request-metrics")
def test_log_request_metrics():
    """Only low priority implemented - critical and high remain."""
    pass
'''

_FEATURE_7_DATA_EXPORT = """\
# Feature: Data Export
priority: high

## Scenarios

### Scenario: Export to CSV
priority: critical

- Given data records exist
- When CSV export is requested
- Then a valid CSV file is generated

### Scenario: Export to JSON
priority: high

- Given data records exist
- When JSON export is requested
- Then a valid JSON file is generated
"""

_FEATURE_7_CACHE_SERVICE = """\
# Feature: Cache Service
priority: high

## Scenarios

### Scenario: Cache hit returns data
priority: critical

- Given data exists in cache
- When cache lookup is performed
- Then cached data is returned

### Scenario: Cache miss triggers fetch
priority: high

- Given data not in cache
- When cache lookup is performed
- Then data is fetched from source
"""

_TEST_7_CACHE_IMPLEMENTED = '''\
from specleft import specleft

@specleft(
    feature_id="feature-cache-service",
    scenario_id="cache-hit-returns-data",
)
def test_cache_hit_returns_data():
    """Cache hit returns data - IMPLEMENTED by agent."""
    with specleft.step("Given data exists in cache"):
        cache = {"key": "value"}

    with specleft.step("When cache lookup is performed"):
        result = cache.get("key")

    with specleft.step("Then cached data is returned"):
        assert result == "value"
'''

_FEATURE_7_USER_SERVICE = """\
# Feature: User Service
priority: high

## Scenarios

### Scenario: Create user
priority: critical

- Given valid user data
- When create user is called
- Then user is created

### Scenario: Update user
priority: high

- Given existing user
- When update is called
- Then user is updated

### Scenario: Delete user
priority: medium

- Given existing user
- When delete is called
- Then user is removed
"""

_TEST_7_USER_SERVICE_PARTIAL = '''\
from specleft import specleft

@specleft(
    feature_id="feature-user-service",
    scenario_id="create-user",
)
def test_create_user():
    """Create user - IMPLEMENTED."""
    with specleft.step("Given valid user data"):
        user_data = {"name": "test"}

    with specleft.step("When create user is called"):
        result = {"id": 1, **user_data}

    with specleft.step("Then user is created"):
        assert result["id"] == 1

@specleft(
    feature_id="feature-user-service",
    scenario_id="update-user",
    skip=True,
    reason="Not yet implemented",
)
def test_update_user():
    """Update user - SKIPPED."""
    pass

# Note: delete-user has no test at all (also unimplemented)
'''


@pytest.fixture
def feature_7_next_scenario(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with unimplemented scenarios for testing `specleft next`."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-api-gateway.md"
    feature_path.write_text(_FEATURE_7_API_GATEWAY)

    test_path = tests_dir / "test_api_gateway.py"
    test_path.write_text(_TEST_7_API_GATEWAY_LOW_ONLY)

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
def feature_7_skeleton(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for testing `specleft test skeleton` generation."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    # Create tmp output directory for skeleton generation
    (workspace / "tmp").mkdir(exist_ok=True)

    feature_path = features_dir / "feature-data-export.md"
    feature_path.write_text(_FEATURE_7_DATA_EXPORT)

    test_path = tests_dir / "test_feature_data_export.py"
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
def feature_7_agent_implements(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with implemented test for testing status reflection."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-cache-service.md"
    feature_path.write_text(_FEATURE_7_CACHE_SERVICE)

    test_path = tests_dir / "test_cache_service.py"
    test_path.write_text(_TEST_7_CACHE_IMPLEMENTED)

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
def feature_7_coverage(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature with partial implementation for testing coverage reporting."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-user-service.md"
    feature_path.write_text(_FEATURE_7_USER_SERVICE)

    test_path = tests_dir / "test_user_service.py"
    test_path.write_text(_TEST_7_USER_SERVICE_PARTIAL)

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
