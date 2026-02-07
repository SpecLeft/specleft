"""Tests for 'specleft guide' command."""

from __future__ import annotations

import json

from click.testing import CliRunner

from specleft import __version__
from specleft.cli.main import cli


class TestGuideCommand:
    """Tests for 'specleft guide' command."""

    def test_guide_table_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["guide"])

        assert result.exit_code == 0
        assert "SpecLeft Workflow Guide" in result.output
        assert "When to use each workflow" in result.output
        assert "direct_test" in result.output
        assert "spec_first" in result.output
        assert "Quick start" in result.output

    def test_guide_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["guide", "--format", "json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["guide_version"] == "1.0"
        assert payload["specleft_version"] == __version__
        assert "workflows" in payload
        assert "task_mapping" in payload
        assert "commands" in payload
        assert "quick_start" in payload
        assert "notes" in payload

    def test_guide_json_workflows(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["guide", "--format", "json"])

        payload = json.loads(result.output)
        workflows = payload["workflows"]

        assert "direct_test" in workflows
        assert "spec_first" in workflows
        assert "description" in workflows["direct_test"]
        assert "use_when" in workflows["direct_test"]

    def test_guide_json_task_mappings(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["guide", "--format", "json"])

        payload = json.loads(result.output)
        mappings = payload["task_mapping"]
        assert len(mappings) >= 5
        for mapping in mappings:
            assert "task" in mapping
            assert "workflow" in mapping
            assert "action" in mapping
            assert mapping["workflow"] in {"direct_test", "spec_first"}

    def test_guide_json_commands(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["guide", "--format", "json"])

        payload = json.loads(result.output)
        commands = payload["commands"]
        expected = {
            "status",
            "next",
            "coverage",
            "features_add",
            "features_add_scenario",
            "test_skeleton",
            "test_stub",
            "features_validate",
        }
        assert expected.issubset(commands.keys())
        for key in expected:
            assert "usage" in commands[key]
            assert "description" in commands[key]
