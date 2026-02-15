"""Tests for CLI base commands (version, help)."""

from __future__ import annotations

from click.testing import CliRunner

from specleft import __version__
from specleft.cli.main import cli


class TestCLIBase:
    """Tests for CLI base commands."""

    def test_cli_version(self) -> None:
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert result.output == f"specleft version: v{__version__}\n"

    def test_cli_help(self) -> None:
        """Test --help flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "SpecLeft" in result.output
        assert "test" in result.output
        assert "features" in result.output
        assert "contract" in result.output
