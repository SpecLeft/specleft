"""Tests for 'specleft init' command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli


class TestInitCommand:
    """Tests for 'specleft init' command."""

    def test_init_creates_single_file_example(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init"], input="1\n")
            assert result.exit_code == 0
            assert Path(".specleft/SKILL.md").exists()
            assert Path(".specleft/specs/example-feature.md").exists()
            assert Path(".specleft/templates/prd-template.yml").exists()

    def test_init_json_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--dry-run", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["dry_run"] is True
            assert payload["summary"]["directories"] == 5
            assert ".specleft/SKILL.md" in payload["would_create"]
            assert ".specleft/specs/example-feature.md" in payload["would_create"]
            assert ".specleft/templates/prd-template.yml" in payload["would_create"]

    def test_init_json_requires_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--format", "json"])
            assert result.exit_code == 1
            payload = json.loads(result.output)
            assert payload["status"] == "error"

    def test_init_blank_creates_directories(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--blank"])
            assert result.exit_code == 0
            assert Path(".specleft/specs").exists()
            assert Path("tests").exists()
            assert Path(".specleft").exists()
            assert Path(".specleft/policies").exists()
            assert Path(".specleft/templates").exists()
            assert Path(".specleft/templates/prd-template.yml").exists()
            assert "Creating SpecLeft directory structure" in result.output

    def test_init_example_and_blank_conflict(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--example", "--blank"])
            assert result.exit_code == 1
            assert "Choose either --example or --blank" in result.output

    def test_init_existing_features_skip(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft/specs").mkdir(parents=True)
            result = runner.invoke(cli, ["init"], input="1\n")
            assert result.exit_code == 0
            assert "Skipping initialization" in result.output
            assert Path(".specleft/specs").exists()
            assert not Path("tests").exists()

    def test_init_existing_features_merge(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft/specs").mkdir(parents=True)
            result = runner.invoke(cli, ["init"], input="2\n")
            assert result.exit_code == 0
            assert Path(".specleft/specs/example-feature.md").exists()

    def test_init_existing_features_cancel(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft/specs").mkdir(parents=True)
            result = runner.invoke(cli, ["init"], input="3\n")
            assert result.exit_code == 2
            assert "Cancelled" in result.output

    def test_init_existing_skill_file_warns_and_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft").mkdir(parents=True)
            Path(".specleft/SKILL.md").write_text("# existing\n")
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 2
            assert (
                "Warning: Skipped creation. Specleft SKILL.md exists already."
                in result.output
            )

    def test_init_existing_skill_file_json_cancelled(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft").mkdir(parents=True)
            Path(".specleft/SKILL.md").write_text("# existing\n")
            result = runner.invoke(cli, ["init", "--format", "json"])
            assert result.exit_code == 2
            payload = json.loads(result.output)
            assert payload["status"] == "cancelled"
            assert (
                payload["message"]
                == "Skipped creation. Specleft SKILL.md exists already."
            )
