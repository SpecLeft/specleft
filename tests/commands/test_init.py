"""Tests for 'specleft init' command."""

from __future__ import annotations

import json
import hashlib
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
            skill_path = Path(".specleft/SKILL.md")
            checksum_path = Path(".specleft/SKILL.md.sha256")
            assert skill_path.exists()
            assert checksum_path.exists()
            assert Path(".specleft/specs/example-feature.md").exists()
            assert Path(".specleft/templates/prd-template.yml").exists()
            expected_hash = hashlib.sha256(
                skill_path.read_text().encode("utf-8")
            ).hexdigest()
            assert checksum_path.read_text().strip() == expected_hash

    def test_init_json_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--dry-run", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["dry_run"] is True
            assert payload["directories_planned"] == 5
            assert payload["files_planned"] == 6
            assert ".specleft/SKILL.md" in payload["files"]
            assert ".specleft/SKILL.md.sha256" in payload["files"]
            assert ".specleft/specs/example-feature.md" in payload["files"]
            assert ".specleft/templates/prd-template.yml" in payload["files"]
            assert len(payload["skill_file_hash"]) == 64

    def test_init_json_supports_non_dry_run(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["success"] is True
            assert payload["skill_file_regenerated"] is True
            assert payload["warnings"] == []

    def test_init_blank_creates_directories(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--blank", "--format", "table"])
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
            result = runner.invoke(cli, ["init", "--format", "table"], input="1\n")
            assert result.exit_code == 0
            assert "Skipping initialization" in result.output
            assert Path(".specleft/specs").exists()
            assert not Path("tests").exists()

    def test_init_existing_features_merge(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft/specs").mkdir(parents=True)
            result = runner.invoke(cli, ["init", "--format", "table"], input="2\n")
            assert result.exit_code == 0
            assert Path(".specleft/specs/example-feature.md").exists()

    def test_init_existing_features_cancel(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft/specs").mkdir(parents=True)
            result = runner.invoke(cli, ["init", "--format", "table"], input="3\n")
            assert result.exit_code == 2
            assert "Cancelled" in result.output

    def test_init_existing_skill_file_warns_and_continues(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft").mkdir(parents=True)
            Path(".specleft/SKILL.md").write_text("# existing\n")
            result = runner.invoke(cli, ["init", "--format", "table"])
            assert result.exit_code == 0
            assert (
                "Existing SKILL.md has been modified from template "
                "(checksum mismatch). Use --force to regenerate." in result.output
            )
            assert Path(".specleft/specs/example-feature.md").exists()
            assert Path(".specleft/SKILL.md").read_text() == "# existing\n"
            assert not Path(".specleft/SKILL.md.sha256").exists()

    def test_init_force_regenerates_modified_skill_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft").mkdir(parents=True)
            Path(".specleft/SKILL.md").write_text("# existing\n")

            result = runner.invoke(cli, ["init", "--force", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["success"] is True
            assert payload["skill_file_regenerated"] is True
            assert payload["warnings"] == []
            assert Path(".specleft/SKILL.md.sha256").exists()
