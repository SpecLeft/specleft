"""Tests for 'specleft plan' command."""

from __future__ import annotations

import json
import importlib
from pathlib import Path
from types import ModuleType

from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.templates.prd_template import (
    PRDFeaturesConfig,
    PRDPrioritiesConfig,
    PRDScenariosConfig,
    PRDTemplate,
)


class TestPlanCommand:
    """Tests for 'specleft plan' command."""

    def test_plan_missing_prd_warns(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["plan", "--format", "table"])
            assert result.exit_code == 0
            assert "PRD not found" in result.output
            assert "Expected locations" in result.output

    def test_plan_creates_features_from_h2(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text(
                "# PRD\n\n## Feature: User Authentication\n## Feature: Payments\n"
            )
            result = runner.invoke(cli, ["plan", "--format", "table"])

            assert result.exit_code == 0
            assert Path(".specleft/specs/feature-user-authentication.md").exists()
            assert Path(".specleft/specs/feature-payments.md").exists()
            assert "Features planned: 2" in result.output
            content = Path(".specleft/specs/feature-user-authentication.md").read_text()
            # breakpoint()
            assert "# Feature: User Authentication" in content
            assert "priority: medium" in content
            assert "## Scenario:" in content
            assert "### Scenario: Example" in content

    def test_plan_uses_h1_when_no_h2(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--format", "table"])
            assert result.exit_code == 0
            assert Path(".specleft/specs/user-authentication.md").exists()
            assert "using top-level title" in result.output

    def test_plan_defaults_to_prd_file_when_no_headings(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("No headings here")
            result = runner.invoke(cli, ["plan", "--format", "table"])
            assert result.exit_code == 0
            assert Path(".specleft/specs/prd.md").exists()
            assert "creating .specleft/specs/prd.md" in result.output

    def test_plan_dry_run_creates_nothing(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--dry-run", "--format", "table"])
            assert result.exit_code == 0
            assert not Path(".specleft/specs").exists()
            assert "Dry run" in result.output
            assert "Would create:" in result.output

    def test_plan_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["feature_count"] == 1
            assert payload["created"]

    def test_plan_json_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--format", "json", "--dry-run"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["dry_run"] is True
            assert payload["would_create"]
            assert "created" not in payload

    def test_plan_skips_existing_feature(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = Path(".specleft/specs")
            features_dir.mkdir(parents=True)
            feature_file = features_dir / "user-authentication.md"
            feature_file.write_text("# Feature: User Authentication\n")

            Path("prd.md").write_text("# User Authentication\n")
            result = runner.invoke(cli, ["plan", "--format", "table"])
            assert result.exit_code == 0
            assert "Skipped existing" in result.output
            assert feature_file.read_text() == "# Feature: User Authentication\n"


class TestPlanTemplateExtraction:
    def test_extract_feature_titles_with_template_patterns(self) -> None:
        plan_module: ModuleType = importlib.import_module("specleft.commands.plan")
        prd_content = """
        # PRD
        ## Overview
        ## Epic: Billing
        """.strip()
        template = PRDTemplate(
            features=PRDFeaturesConfig(
                heading_level=2,
                patterns=["Epic: {title}"],
                exclude=["Overview"],
            )
        )

        titles, warnings = plan_module._extract_feature_titles(
            prd_content,
            template,
        )

        assert warnings == []
        assert titles == ["Epic: Billing"]

    def test_extract_feature_titles_with_contains(self) -> None:
        plan_module: ModuleType = importlib.import_module("specleft.commands.plan")
        prd_content = """
        # PRD
        ## Feature Overview
        ## Platform Capability
        """.strip()
        template = PRDTemplate(
            features=PRDFeaturesConfig(
                heading_level=2,
                patterns=["Epic: {title}"],
                contains=["capability"],
                match_mode="contains",
            )
        )

        titles, warnings = plan_module._extract_feature_titles(
            prd_content,
            template,
        )

        assert warnings == []
        assert titles == ["Platform Capability"]

    def test_extract_prd_scenarios_with_template_patterns(self) -> None:
        plan_module: ModuleType = importlib.import_module("specleft.commands.plan")
        prd_content = """
        ## Feature: Billing
        - Priority = p1

        ### AC: Refund requested
        - Priority = p0
        - Given a customer
        - When they request a refund
        - Then we mark it pending
        """.strip()
        template = PRDTemplate(
            features=PRDFeaturesConfig(heading_level=2),
            scenarios=PRDScenariosConfig(
                heading_level=[3],
                patterns=["AC: {title}"],
                step_keywords=["Given", "When", "Then"],
            ),
            priorities=PRDPrioritiesConfig(
                patterns=["Priority = {value}"],
                mapping={"p0": "critical", "p1": "high"},
            ),
        )

        scenarios_by_feature, orphan_scenarios, feature_priorities, warnings = (
            plan_module._extract_prd_scenarios(
                prd_content,
                template=template,
                require_step_keywords=True,
            )
        )

        assert warnings == []
        assert orphan_scenarios == []
        assert feature_priorities == {"Feature: Billing": "high"}
        assert scenarios_by_feature == {
            "Feature: Billing": [
                {
                    "title": "Refund requested",
                    "steps": [
                        "Given a customer",
                        "When they request a refund",
                        "Then we mark it pending",
                    ],
                    "priority": "critical",
                }
            ]
        }

    def test_extract_prd_scenarios_with_contains_only(self) -> None:
        plan_module: ModuleType = importlib.import_module("specleft.commands.plan")
        prd_content = """
        ## Feature: Billing
        ### Refund Acceptance
        - Given a customer
        - When they request a refund
        - Then we mark it pending
        """.strip()
        template = PRDTemplate(
            features=PRDFeaturesConfig(heading_level=2),
            scenarios=PRDScenariosConfig(
                heading_level=[3],
                patterns=["Scenario: {title}"],
                contains=["acceptance"],
                match_mode="contains",
                step_keywords=["Given", "When", "Then"],
            ),
        )

        scenarios_by_feature, orphan_scenarios, feature_priorities, warnings = (
            plan_module._extract_prd_scenarios(
                prd_content,
                template=template,
                require_step_keywords=True,
            )
        )

        assert warnings == []
        assert orphan_scenarios == []
        assert feature_priorities == {}
        assert scenarios_by_feature == {
            "Feature: Billing": [
                {
                    "title": "Scenario",
                    "steps": [
                        "Given a customer",
                        "When they request a refund",
                        "Then we mark it pending",
                    ],
                }
            ]
        }

    def test_render_scenarios_defaults_priority_to_medium(self) -> None:
        plan_module: ModuleType = importlib.import_module("specleft.commands.plan")
        scenarios: list[dict[str, object]] = [
            {
                "title": "No explicit priority",
                "steps": ["Given something", "When action", "Then result"],
            },
        ]
        rendered = plan_module._render_scenarios(scenarios)
        assert "priority: medium" in rendered

    def test_plan_scenario_without_priority_gets_medium(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text(
                "# PRD\n\n## Feature: Billing\n\n"
                "### Scenario: Refund requested\n"
                "- Given a customer\n"
                "- When they request a refund\n"
                "- Then we mark it pending\n"
            )
            result = runner.invoke(cli, ["plan", "--format", "table"])

            assert result.exit_code == 0
            feature_file = Path(".specleft/specs/feature-billing.md")
            assert feature_file.exists()
            content = feature_file.read_text()
            assert "### Scenario: Refund requested" in content
            assert "priority: medium" in content


class TestPlanAnalyzeMode:
    def test_analyze_flag_is_recognized(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text(
                "# PRD\n\n## Overview\n\n## Feature: Billing\n\n## Notes\n\n## Payments\n"
            )
            result = runner.invoke(cli, ["plan", "--analyze", "--format", "table"])

            assert result.exit_code == 0
            assert not Path("features").exists()
            assert "Analyzing PRD structure" in result.output
            assert "Ambiguous:" in result.output

    def test_analyze_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## Feature: Billing\n")
            result = runner.invoke(cli, ["plan", "--analyze", "--format", "json"])

            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["summary"]["features"] == 1
            assert payload["headings"]

    def test_analyze_respects_contains_matching(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text(
                "# PRD\n\n## Capability: Billing\n\n### Acceptance Criteria\n"
            )
            Path("template.yml").write_text("""
version: "1.0"
features:
  heading_level: 2
  patterns:
    - "Feature: {title}"
  contains: ["capability"]
  match_mode: "contains"
scenarios:
  heading_level: [3]
  patterns:
    - "Scenario: {title}"
  contains: ["acceptance"]
  match_mode: "contains"
""".lstrip())

            result = runner.invoke(
                cli,
                ["plan", "--analyze", "--format", "json", "--template", "template.yml"],
            )

            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["summary"]["features"] == 1
            assert payload["summary"]["scenarios"] == 1


class TestPlanTemplateMode:
    def test_plan_uses_custom_template_patterns(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text(
                "# PRD\n\n## Epic: Billing\n\n### AC: Refund requested\n- Priority = p0\n"
            )
            Path("template.yml").write_text("""
version: "1.0"

features:
  heading_level: 2
  patterns:
    - "Epic: {title}"

scenarios:
  heading_level: [3]
  patterns:
    - "AC: {title}"
  step_keywords: ["Given", "When", "Then"]

priorities:
  patterns:
    - "Priority = {value}"
  mapping:
    p0: critical
""".lstrip())

            result = runner.invoke(
                cli, ["plan", "--template", "template.yml", "--format", "table"]
            )

            assert result.exit_code == 0
            feature_file = Path(".specleft/specs/epic-billing.md")
            assert feature_file.exists()
            content = feature_file.read_text()
            assert "priority: critical" in content

    def test_plan_template_json_includes_metadata(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## Epic: Billing\n")
            Path("template.yml").write_text("""
version: "1.0"

features:
  heading_level: 2
  patterns:
    - "Epic: {title}"
""".lstrip())

            result = runner.invoke(
                cli,
                ["plan", "--template", "template.yml", "--format", "json"],
            )

            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["template"]["path"] == "template.yml"
            assert payload["template"]["version"] == "1.0"


class TestPlanTemplateAutoDetect:
    def _write_default_template(self) -> None:
        template_dir = Path(".specleft/templates")
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "prd-template.yml").write_text(
            'version: "1.0"\n'
            "features:\n"
            "  heading_level: 2\n"
            "  patterns:\n"
            '    - "Feature: {title}"\n'
        )

    def test_auto_detects_template_when_present(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## Feature: Billing\n")
            self._write_default_template()
            result = runner.invoke(cli, ["plan", "--format", "table"])

            assert result.exit_code == 0
            assert (
                "Using template: .specleft/templates/prd-template.yml" in result.output
            )

    def test_auto_detect_template_json_includes_metadata(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## Feature: Billing\n")
            self._write_default_template()
            result = runner.invoke(cli, ["plan", "--format", "json"])

            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["template"]["path"] == ".specleft/templates/prd-template.yml"
            assert payload["template"]["version"] == "1.0"

    def test_no_template_message_when_file_absent(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## Feature: Billing\n")
            result = runner.invoke(cli, ["plan", "--format", "table"])

            assert result.exit_code == 0
            assert "Using template:" not in result.output

    def test_explicit_template_overrides_auto_detect(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("prd.md").write_text("# PRD\n\n## Epic: Billing\n")
            self._write_default_template()
            Path("custom.yml").write_text(
                'version: "2.0"\n'
                "features:\n"
                "  heading_level: 2\n"
                "  patterns:\n"
                '    - "Epic: {title}"\n'
            )
            result = runner.invoke(
                cli, ["plan", "--template", "custom.yml", "--format", "table"]
            )

            assert result.exit_code == 0
            assert "Using template: custom.yml" in result.output
            assert Path(".specleft/specs/epic-billing.md").exists()
