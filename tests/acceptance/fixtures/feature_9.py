"""Feature 9: CLI Feature Authoring fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixtures.common import FeatureFiles

_FEATURE_9_AUTHORING = """\
# Feature: CLI Feature Authoring
priority: high

## Scenarios

### Scenario: Create feature file from CLI
priority: critical
- Given no feature file exists for the requested feature id
- When specleft features add is executed with an id and title
- Then a new feature markdown file is created with a scenario tag window

### Scenario: Reject invalid feature ids
priority: high
- Given a feature id that contains uppercase or spaces
- When specleft features add is executed
- Then the command exits with a validation error and no file is written

### Scenario: Append scenario to feature file
priority: critical
- Given a feature markdown file exists with a scenario tag window
- When specleft features add-scenario is executed with a title and steps
- Then the scenario is appended within the tag window

### Scenario: Reject add-scenario when feature missing
priority: high
- Given no feature markdown file exists for the requested id
- When specleft features add-scenario is executed
- Then the command exits with an error and no file is written

### Scenario: Reject interactive mode without a TTY
priority: medium
- Given interactive mode is requested without a terminal
- When specleft features add or add-scenario is executed
- Then the command exits with a helpful error message

### Scenario: Reject skeleton generation without steps
priority: medium
- Given a scenario is created without steps
- When specleft features add-scenario is executed with --add-test skeleton
- Then the command reports that steps are required for skeleton generation

### Scenario: Preview test content for a scenario
priority: low
- Given a scenario is added with steps
- When specleft features add-scenario is executed with --preview-test
- Then the generated test preview is printed to stdout
"""


@pytest.fixture
def feature_9_cli_authoring(
    acceptance_workspace: tuple[CliRunner, Path],
) -> Iterator[tuple[CliRunner, Path, FeatureFiles]]:
    """Feature for CLI authoring acceptance tests."""
    runner, workspace = acceptance_workspace

    features_dir = workspace / ".specleft" / "specs"
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = workspace / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    feature_path = features_dir / "feature-9-cli-feature-authoring.md"
    test_path = tests_dir / "test_feature_9_cli_feature_authoring.py"

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
