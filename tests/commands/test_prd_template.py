"""Tests for PRD template models and loader."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from specleft.templates.prd_template import (
    PRDTemplate,
    compile_pattern,
    default_template,
    load_template,
)


class TestPRDTemplate:
    def test_default_template_matches_expected_defaults(self) -> None:
        template = default_template()

        assert template.version == "1.0"
        assert template.features.heading_level == 2
        assert template.features.patterns == [
            "Feature: {title}",
            "Feature {title}",
        ]
        assert template.features.contains == []
        assert template.features.match_mode == "any"
        assert template.features.exclude == [
            "Overview",
            "Goals",
            "Non-Goals",
            "Open Questions",
            "Notes",
        ]
        assert template.scenarios.heading_level == [3, 4]
        assert template.scenarios.patterns == ["Scenario: {title}"]
        assert template.scenarios.contains == []
        assert template.scenarios.match_mode == "any"
        assert template.scenarios.step_keywords == [
            "Given",
            "When",
            "Then",
            "And",
            "But",
        ]
        assert template.priorities.patterns == [
            "priority: {value}",
            "Priority: {value}",
        ]
        assert template.priorities.mapping == {}

    def test_compile_pattern_converts_title_placeholder(self) -> None:
        pattern = compile_pattern("Feature: {title}")
        match = pattern.match("Feature: User Authentication")

        assert match is not None
        assert match.group("title") == "User Authentication"

    def test_compile_pattern_converts_value_placeholder(self) -> None:
        pattern = compile_pattern("Priority: {value}")
        match = pattern.match("Priority: critical")

        assert match is not None
        assert match.group("value") == "critical"

    def test_load_template_reads_yaml(self, tmp_path: Path) -> None:
        template_path = tmp_path / "template.yml"
        template_path.write_text("""
version: "1.0"
features:
  heading_level: 2
  patterns:
    - "Feature: {title}"
  contains: ["Capability"]
  match_mode: "contains"
  exclude:
    - "Overview"
scenarios:
  heading_level: [3]
  patterns:
    - "Scenario: {title}"
  contains: ["Acceptance"]
  match_mode: "any"
  step_keywords:
    - "Given"
priorities:
  patterns:
    - "priority: {value}"
  mapping:
    p0: critical
""".lstrip())

        template = load_template(template_path)

        assert isinstance(template, PRDTemplate)
        assert template.features.heading_level == 2
        assert template.scenarios.heading_level == [3]
        assert template.priorities.mapping == {"p0": "critical"}
        assert template.features.contains == ["Capability"]
        assert template.features.match_mode == "contains"
        assert template.scenarios.contains == ["Acceptance"]
        assert template.scenarios.match_mode == "any"

    def test_load_template_rejects_invalid_yaml(self, tmp_path: Path) -> None:
        template_path = tmp_path / "template.yml"
        template_path.write_text("features: [unbalanced")

        with pytest.raises(click.ClickException) as excinfo:
            load_template(template_path)

        assert "template" in str(excinfo.value).lower()

    def test_load_template_rejects_invalid_heading_level(self, tmp_path: Path) -> None:
        template_path = tmp_path / "template.yml"
        template_path.write_text("""
features:
  heading_level: 7
""".lstrip())

        with pytest.raises(click.ClickException) as excinfo:
            load_template(template_path)

        assert "heading" in str(excinfo.value).lower()

    def test_load_template_rejects_invalid_patterns(self, tmp_path: Path) -> None:
        template_path = tmp_path / "template.yml"
        template_path.write_text("""
features:
  heading_level: 2
  patterns:
    - "Feature: {name}"
scenarios:
  heading_level: [3]
  patterns:
    - "Scenario: {title}"
priorities:
  patterns:
    - "Priority: {value}"
  mapping: {}
""".lstrip())

        with pytest.raises(click.ClickException) as excinfo:
            load_template(template_path)

        assert (
            "pattern" in str(excinfo.value).lower()
            or "template" in str(excinfo.value).lower()
        )

    def test_load_template_rejects_invalid_match_mode(self, tmp_path: Path) -> None:
        template_path = tmp_path / "template.yml"
        template_path.write_text("""
features:
  heading_level: 2
  match_mode: "either"
""".lstrip())

        with pytest.raises(click.ClickException) as excinfo:
            load_template(template_path)

        assert "match" in str(excinfo.value).lower()

    def test_heading_level_accepts_int_or_list(self) -> None:
        features = PRDTemplate().features.model_copy(update={"heading_level": 2})
        scenarios = PRDTemplate().scenarios.model_copy(update={"heading_level": [3, 4]})
        template = PRDTemplate(features=features, scenarios=scenarios)

        assert template.features.heading_level == 2
        assert template.scenarios.heading_level == [3, 4]
