"""Tests for 'specleft skill' commands."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.decorators import specleft


def _hash_for(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class TestSkillCommand:
    """Tests for 'specleft skill' commands."""

    @specleft(
        feature_id="feature-skill-integrity",
        scenario_id="skill-command-group-is-discoverable",
    )
    def test_skill_group_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["skill", "--help"])
        assert result.exit_code == 0
        assert "verify" in result.output
        assert "update" in result.output

    @specleft(
        feature_id="feature-skill-integrity",
        scenario_id="verify-reports-pass-after-init",
    )
    def test_skill_verify_pass_after_init(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            init_result = runner.invoke(cli, ["init"], input="1\n")
            assert init_result.exit_code == 0

            result = runner.invoke(cli, ["skill", "verify", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["integrity"] == "pass"
            assert payload["commands_simple"] is True
            assert payload["expected_hash"] == payload["actual_hash"]

    @specleft(
        feature_id="feature-skill-integrity",
        scenario_id="verify-reports-modified-on-hash-mismatch",
    )
    def test_skill_verify_modified_when_hash_mismatch(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            init_result = runner.invoke(cli, ["init"], input="1\n")
            assert init_result.exit_code == 0

            skill_path = Path(".specleft/SKILL.md")
            os.chmod(skill_path, 0o644)
            skill_path.write_text("# tampered\n")

            result = runner.invoke(cli, ["skill", "verify", "--format", "json"])
            assert result.exit_code == 1
            payload = json.loads(result.output)
            assert payload["integrity"] == "modified"

    @specleft(
        feature_id="feature-skill-integrity",
        scenario_id="verify-reports-outdated-for-non-canonical-but-checksum-valid-content",
    )
    def test_skill_verify_outdated_when_hash_matches_noncanonical(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft").mkdir(parents=True, exist_ok=True)
            outdated_content = (
                "# SpecLeft CLI Reference\n\n"
                "## Workflow\n"
                "1. `specleft status --format json`\n"
            )
            Path(".specleft/SKILL.md").write_text(outdated_content)
            Path(".specleft/SKILL.md.sha256").write_text(
                f"{_hash_for(outdated_content)}\n"
            )

            result = runner.invoke(cli, ["skill", "verify", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["integrity"] == "outdated"

    @specleft(
        feature_id="feature-skill-integrity",
        scenario_id="skill-update-repairs-modified-integrity-state",
    )
    def test_skill_update_repairs_modified_integrity(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".specleft").mkdir(parents=True, exist_ok=True)
            Path(".specleft/SKILL.md").write_text("# tampered\n")
            Path(".specleft/SKILL.md.sha256").write_text(
                f"{_hash_for('# different')} \n"
            )

            update_result = runner.invoke(cli, ["skill", "update", "--format", "json"])
            assert update_result.exit_code == 0
            update_payload = json.loads(update_result.output)
            assert ".specleft/SKILL.md" in (
                update_payload["updated"] + update_payload["created"]
            )

            verify_result = runner.invoke(cli, ["skill", "verify", "--format", "json"])
            assert verify_result.exit_code == 0
            verify_payload = json.loads(verify_result.output)
            assert verify_payload["integrity"] == "pass"
