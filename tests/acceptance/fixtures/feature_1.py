"""Feature 1: Planning Mode - PRD-based fixtures.

Note: Feature 1 tests the `specleft plan` command which generates feature
files FROM a PRD. These fixtures only write PRD content, not feature files.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import PrdFiles

# PRD content for test_generate_feature_files_from_prd
_PRD_MULTI_FEATURE = """\
# Product Requirements

## Feature 1: User Authentication
priority: critical

### Scenarios

#### Scenario: User logs in successfully
- Given a registered user
- When they submit valid credentials
- Then they are authenticated

## Feature 2: Payment Processing
priority: high

### Scenarios

#### Scenario: Process credit card payment
- Given a valid credit card
- When payment is submitted
- Then the transaction succeeds
"""

# PRD content for test_derive_feature_filenames_from_prd_headings
_PRD_SLUG_TEST = """\
# Product Requirements Document

## Feature: User Authentication & Login
priority: critical

### Scenarios

#### Scenario: Basic login
- Given a user
- When they log in
- Then they succeed

## Feature: Data Export (CSV/JSON)
priority: high

### Scenarios

#### Scenario: Export data
- Given data exists
- When export is requested
- Then file is created
"""


@pytest.fixture
def feature_1_prd_multi_feature(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, PrdFiles]]:
    """PRD with multiple features for testing feature file generation."""
    runner, workspace = acceptance_workspace

    prd_path = workspace / "prd.md"
    prd_path.write_text(_PRD_MULTI_FEATURE)

    yield (
        runner,
        workspace,
        PrdFiles(
            prd_path=prd_path,
            features_dir=workspace / ".specleft" / "specs",
        ),
    )


@pytest.fixture
def feature_1_prd_slug_test(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, PrdFiles]]:
    """PRD with special characters in titles for testing slug derivation."""
    runner, workspace = acceptance_workspace

    prd_path = workspace / "prd.md"
    prd_path.write_text(_PRD_SLUG_TEST)

    # Pre-create an existing feature file to test non-overwrite behaviour
    existing_content = "# Feature: User Authentication & Login\n\nCustom content that should NOT be overwritten.\n"
    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / "feature-user-authentication-login.md").write_text(existing_content)

    yield (
        runner,
        workspace,
        PrdFiles(
            prd_path=prd_path,
            features_dir=workspace / ".specleft" / "specs",
        ),
    )
