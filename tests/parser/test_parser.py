"""Tests for specleft.parser module."""

from __future__ import annotations

from pathlib import Path

import pytest
from specleft.parser import SpecParser
from specleft.schema import ExecutionTime, Priority, SpecsConfig, StepType
from specleft.validator import collect_spec_stats, load_specs_directory


def _write_file(path: Path, content: str) -> None:
    path.write_text(content)


def test_parse_directory_missing(tmp_path: Path) -> None:
    parser = SpecParser()

    missing = tmp_path / "features"
    with pytest.raises(FileNotFoundError):
        parser.parse_directory(missing)


def test_parse_minimal_tree(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
priority: critical
tags: [smoke]
execution_time: fast
---

# Scenario: Basic addition

Adds two numbers together.

## Steps
- **Given** calculator is initialized
- **When** adding `2` and `3`
- **Then** result should be `5`
""".strip(),
    )

    config = parser.parse_directory(tmp_path)

    assert len(config.features) == 1
    feature = config.features[0]
    assert feature.feature_id == "calculator"
    assert feature.name == "Calculator"
    assert feature.stories[0].story_id == "addition"

    scenario = feature.stories[0].scenarios[0]
    assert scenario.scenario_id == "basic-addition"
    assert scenario.priority == Priority.CRITICAL
    assert scenario.execution_time == ExecutionTime.FAST
    assert scenario.steps[0].type == StepType.GIVEN
    assert scenario.steps[1].description == "adding 2 and 3"


def test_parse_feature_story_files(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "string_utils"
    story_dir = feature_dir / "uppercase"
    story_dir.mkdir(parents=True)

    _write_file(
        feature_dir / "_feature.md",
        """
---
feature_id: string-utils
component: text
owner: core-team
priority: high
tags: [core]
---

# Feature: String Utilities

Feature description text.
""".strip(),
    )

    _write_file(
        story_dir / "_story.md",
        """
---
story_id: uppercase
priority: medium
tags: [smoke, text]
---

# Story: Uppercase conversion

Converts input to uppercase.
""".strip(),
    )

    _write_file(
        story_dir / "convert_to_uppercase.md",
        """
---
scenario_id: convert-to-uppercase
priority: low
tags: [text]
execution_time: medium
---

# Scenario: Convert to uppercase

## Steps
- **Given** input is `hello`
- **When** converting to uppercase
- **Then** result is `HELLO`
""".strip(),
    )

    config = parser.parse_directory(tmp_path)
    feature = config.features[0]
    story = feature.stories[0]
    scenario = story.scenarios[0]

    assert feature.feature_id == "string-utils"
    assert feature.component == "text"
    assert feature.owner == "core-team"
    assert feature.priority == Priority.HIGH
    assert feature.tags == ["core"]

    assert story.story_id == "uppercase"
    assert story.priority == Priority.MEDIUM
    assert story.tags == ["smoke", "text"]

    assert scenario.execution_time == ExecutionTime.MEDIUM


def test_parse_test_data_table(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
priority: critical
---

# Scenario: Basic addition

## Test Data
| a | b | expected | description |
|---|---|----------|-------------|
| 2 | 3 | 5 | Small numbers |
| 10 | 15 | 25 | Medium numbers |

## Steps
- **When** adding `{a}` and `{b}`
- **Then** result should be `{expected}`
""".strip(),
    )

    config = parser.parse_directory(tmp_path)
    scenario = config.features[0].stories[0].scenarios[0]

    assert scenario.is_parameterized is True
    assert scenario.test_data[0].params["a"] == 2
    assert scenario.test_data[0].params["b"] == 3
    assert scenario.test_data[1].description == "Medium numbers"


def test_parse_description_block(tmp_path: Path) -> None:
    parser = SpecParser()

    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
---

# Scenario: Basic addition

This scenario adds two numbers.
It should support multiple lines.

## Steps
- **Given** calculator is ready
""".strip(),
    )

    config = parser.parse_directory(tmp_path)
    scenario = config.features[0].stories[0].scenarios[0]

    assert (
        scenario.description
        == "This scenario adds two numbers. It should support multiple lines."
    )


def test_load_specs_directory_and_stats(tmp_path: Path) -> None:
    feature_dir = tmp_path / "calculator"
    story_dir = feature_dir / "addition"
    story_dir.mkdir(parents=True)

    _write_file(
        feature_dir / "_feature.md",
        """
---
feature_id: calculator
priority: high
---

# Feature: Calculator
""".strip(),
    )

    _write_file(
        story_dir / "_story.md",
        """
---
story_id: addition
priority: low
tags: [math]
---

# Story: Addition
""".strip(),
    )

    _write_file(
        story_dir / "basic_addition.md",
        """
---
scenario_id: basic-addition
priority: critical
tags: [smoke]
---

# Scenario: Basic addition

## Steps
- **Given** calculator is ready
- **When** adding numbers
- **Then** result is shown
""".strip(),
    )

    config = load_specs_directory(tmp_path)
    stats = collect_spec_stats(config)

    assert stats.feature_count == 1
    assert stats.story_count == 1
    assert stats.scenario_count == 1
    assert stats.step_count == 3
    assert stats.tags == {"math", "smoke"}


# ---------------------------------------------------------------------------
# Template-aware heading extraction tests (issue #85)
# ---------------------------------------------------------------------------


def test_parse_single_file_with_feature_prefix(tmp_path: Path) -> None:
    """Parser handles the standard '# Feature: Title' heading."""
    parser = SpecParser()
    features_dir = tmp_path / "specs"
    features_dir.mkdir()

    (features_dir / "auth.md").write_text(
        "# Feature: User Authentication\n"
        "\n"
        "## Scenarios\n"
        "\n"
        "### Scenario: Login\n"
        "priority: high\n"
        "\n"
        "- Given a user exists\n"
        "- When the user logs in\n"
        "- Then access is granted\n"
    )

    config = parser.parse_directory(features_dir)
    assert len(config.features) == 1
    assert config.features[0].name == "User Authentication"
    assert config.features[0].feature_id == "auth"


def test_parse_single_file_bare_title_falls_back(tmp_path: Path) -> None:
    """Parser falls back to the raw H1 text when no template pattern matches.

    This is the exact bug from issue #85: ``specleft plan`` generated
    headings like ``# Document Lifecycle`` (no ``Feature:`` prefix).
    """
    parser = SpecParser()
    features_dir = tmp_path / "specs"
    features_dir.mkdir()

    (features_dir / "document-lifecycle.md").write_text(
        "# Document Lifecycle\n"
        "\n"
        "## Scenarios\n"
        "\n"
        "### Scenario: Create document\n"
        "priority: medium\n"
        "\n"
        "- Given the system is ready\n"
        "- When a document is created\n"
        "- Then it should be stored\n"
    )

    config = parser.parse_directory(features_dir)
    assert len(config.features) == 1
    feature = config.features[0]
    assert feature.name == "Document Lifecycle"
    assert feature.feature_id == "document-lifecycle"
    assert len(feature.stories) == 1
    assert len(feature.stories[0].scenarios) == 1


def test_parse_single_file_custom_template_pattern(tmp_path: Path) -> None:
    """Parser matches a custom PRD template pattern like '{title}'."""
    from specleft.templates.prd_template import PRDFeaturesConfig, PRDTemplate

    custom_template = PRDTemplate(
        features=PRDFeaturesConfig(
            patterns=["{title}"],
        )
    )
    parser = SpecParser(template=custom_template)
    features_dir = tmp_path / "specs"
    features_dir.mkdir()

    (features_dir / "billing.md").write_text(
        "# Billing Module\n"
        "\n"
        "## Scenarios\n"
        "\n"
        "### Scenario: Charge card\n"
        "priority: high\n"
        "\n"
        "- Given a valid card\n"
        "- When charging\n"
        "- Then payment succeeds\n"
    )

    config = parser.parse_directory(features_dir)
    assert len(config.features) == 1
    assert config.features[0].name == "Billing Module"


def test_parse_single_file_feature_word_no_colon(tmp_path: Path) -> None:
    """Parser matches the default 'Feature {title}' pattern (no colon)."""
    parser = SpecParser()
    features_dir = tmp_path / "specs"
    features_dir.mkdir()

    (features_dir / "search.md").write_text(
        "# Feature Search Engine\n"
        "\n"
        "## Scenarios\n"
        "\n"
        "### Scenario: Basic search\n"
        "priority: medium\n"
        "\n"
        "- Given indexed documents\n"
        "- When searching\n"
        "- Then results appear\n"
    )

    config = parser.parse_directory(features_dir)
    assert len(config.features) == 1
    assert config.features[0].name == "Search Engine"


def test_from_directory_loads_template(tmp_path: Path) -> None:
    """SpecsConfig.from_directory loads a PRD template from the conventional path."""
    specs_dir = tmp_path / ".specleft" / "specs"
    specs_dir.mkdir(parents=True)
    templates_dir = tmp_path / ".specleft" / "templates"
    templates_dir.mkdir()

    # Write a custom template that matches bare titles.
    (templates_dir / "prd-template.yml").write_text(
        "version: '1.0'\n"
        "features:\n"
        "  heading_level: 2\n"
        "  patterns:\n"
        "    - '{title}'\n"
        "scenarios:\n"
        "  heading_level: [3, 4]\n"
        "  patterns:\n"
        "    - 'Scenario: {title}'\n"
        "priorities:\n"
        "  patterns:\n"
        "    - 'priority: {value}'\n"
    )

    (specs_dir / "notifications.md").write_text(
        "# Push Notifications\n"
        "\n"
        "## Scenarios\n"
        "\n"
        "### Scenario: Send notification\n"
        "priority: medium\n"
        "\n"
        "- Given a user is subscribed\n"
        "- When an event occurs\n"
        "- Then a notification is sent\n"
    )

    config = SpecsConfig.from_directory(specs_dir)
    assert len(config.features) == 1
    assert config.features[0].name == "Push Notifications"


def test_from_directory_falls_back_without_template(tmp_path: Path) -> None:
    """Without a template file, parser still uses default patterns + fallback."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()

    # No .specleft/templates directory at all.
    (specs_dir / "dashboard.md").write_text(
        "# Feature: Admin Dashboard\n"
        "\n"
        "## Scenarios\n"
        "\n"
        "### Scenario: View metrics\n"
        "priority: low\n"
        "\n"
        "- Given an admin user\n"
        "- When viewing the dashboard\n"
        "- Then metrics are displayed\n"
    )

    config = SpecsConfig.from_directory(specs_dir)
    assert len(config.features) == 1
    assert config.features[0].name == "Admin Dashboard"
