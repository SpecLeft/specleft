"""Tests for 'specleft features add' and 'specleft features add-scenario'."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from specleft.cli.main import cli
from specleft.utils.history import load_feature_history


class TestFeaturesAddCommand:
    """Tests for the features add command."""

    def test_add_creates_feature_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--title",
                    "CLI Authoring",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0
            feature_path = Path(".specleft/specs/cli-authoring.md")
            assert feature_path.exists()
            content = feature_path.read_text()
            assert "# Feature: CLI Authoring" in content

    def test_add_invalid_id(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "Invalid ID",
                    "--title",
                    "Bad",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 1
            assert "Feature ID must match" in result.output

    def test_add_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "dry-run",
                    "--title",
                    "Dry Run",
                    "--dry-run",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0
            assert not Path(".specleft/specs/dry-run.md").exists()

    def test_add_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "json-feature",
                    "--title",
                    "JSON Feature",
                    "--format",
                    "json",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["created"] is True
            assert payload["feature_id"] == "json-feature"


class TestFeaturesAddScenarioCommand:
    """Tests for the features add-scenario command."""

    def test_add_scenario_creates_history(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Add scenario",
                    "--step",
                    "Given a scenario",
                    "--dir",
                    ".specleft/specs",
                ],
                input="n\n",
            )
            assert result.exit_code == 0, result.output
            entries = load_feature_history("cli-history")
            assert entries
            assert entries[-1]["action"] == "scenario-added"

    def test_add_scenario_skeleton_requires_steps(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "No steps",
                    "--add-test",
                    "skeleton",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 1
            assert "No steps found for test skeleton" in result.output

    def test_add_scenario_preview_test(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Preview",
                    "--step",
                    "Given a preview",
                    "--preview-test",
                    "--format",
                    "table",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0, result.output
            assert "Test preview:" in result.output

    def test_add_scenario_json_preview(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "JSON preview",
                    "--step",
                    "Given a preview",
                    "--preview-test",
                    "--format",
                    "json",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0, result.output
            assert '"test_preview"' in result.output

    def test_add_scenario_missing_feature_json_error(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "missing-feature",
                    "--title",
                    "Missing feature",
                    "--format",
                    "json",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 1
            payload = json.loads(result.output)
            assert payload["success"] is False
            assert "suggestion" in payload

    def test_add_scenario_invalid_id(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Bad scenario",
                    "--id",
                    "Bad ID",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 1
            assert "Scenario ID must match" in result.output

    def test_add_scenario_add_test_stub_creates_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Stub scenario",
                    "--add-test",
                    "stub",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0, result.output
            test_path = Path("tests/test_cli_history.py")
            assert test_path.exists()

    def test_add_scenario_add_test_stub_respects_tests_dir(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Stub scenario",
                    "--add-test",
                    "stub",
                    "--tests-dir",
                    "custom_tests",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 0, result.output
            test_path = Path("custom_tests/test_cli_history.py")
            assert test_path.exists()

    def test_add_scenario_add_test_stub_rejects_tests_file_path(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Stub scenario",
                    "--add-test",
                    "stub",
                    "--tests-dir",
                    "tests/test_cli_history.py",
                    "--dir",
                    ".specleft/specs",
                ],
            )
            assert result.exit_code == 2, result.output
            assert "Tests directory must be a directory path" in result.output

    def test_add_scenario_interactive_accepts_tests_dir_prompt(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Add scenario",
                    "--step",
                    "Given a scenario",
                    "--format",
                    "table",
                    "--dir",
                    ".specleft/specs",
                ],
                input="y\nmy_tests\n",
            )
            assert result.exit_code == 0, result.output
            test_path = Path("my_tests/test_cli_history.py")
            assert test_path.exists()

    def test_add_scenario_interactive_accepts_default_tests_dir(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "features",
                    "add",
                    "--id",
                    "cli-history",
                    "--title",
                    "CLI History",
                    "--dir",
                    ".specleft/specs",
                ],
            )

            result = runner.invoke(
                cli,
                [
                    "features",
                    "add-scenario",
                    "--feature",
                    "cli-history",
                    "--title",
                    "Add scenario",
                    "--step",
                    "Given a scenario",
                    "--format",
                    "table",
                    "--dir",
                    ".specleft/specs",
                ],
                input="y\n\n",
            )
            assert result.exit_code == 0, result.output
            test_path = Path("tests/test_cli_history.py")
            assert test_path.exists()
