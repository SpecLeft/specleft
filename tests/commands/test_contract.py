"""Tests for 'specleft contract' commands."""

from __future__ import annotations

import json

from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.commands.constants import CLI_VERSION


class TestContractCommand:
    """Tests for 'specleft contract' commands."""

    def test_contract_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["contract", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["contract_version"] == "1.1"
        assert payload["specleft_version"] == CLI_VERSION
        assert "guarantees" not in payload
        assert payload["skill_file_integrity_check"] is True
        assert payload["skill_file_commands_are_simple"] is True
        assert payload["cli_rejects_shell_metacharacters"] is True
        assert payload["init_refuses_symlinks"] is True

    def test_contract_test_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["contract", "test", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["contract_version"] == "1.1"
        assert payload["specleft_version"] == CLI_VERSION
        assert payload["passed"] is True
        assert payload["checks"]
