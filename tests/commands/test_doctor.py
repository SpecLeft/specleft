"""Tests for 'specleft doctor' command."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.commands.constants import CLI_VERSION
from specleft.commands.doctor import _load_dependency_names


class TestDoctorCommand:
    """Tests for 'specleft doctor' command."""

    def test_dependency_parsing(self, tmp_path: Path) -> None:
        """Test parsing of various dependency formats in pyproject.toml."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            pyproject_content = """
[project]
name = "test-project"
dependencies = [
    "simple>=1.0.0",
    "with-extras[standard]>=0.1.0",
    "compatible~=2.0",
    "exclusion!=1.5",
    "markers; python_version<'3.9'",
    "direct @ https://example.com/pkg.zip"
]
"""
            Path("pyproject.toml").write_text(pyproject_content)

            deps = _load_dependency_names()

            expected = [
                "simple",
                "with-extras",
                "compatible",
                "exclusion",
                "markers",
                "direct",
            ]

            assert deps == expected
        finally:
            os.chdir(original_cwd)

    def test_doctor_json_includes_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--format", "json"])
        assert result.exit_code in {0, 1}
        payload = json.loads(result.output)
        assert payload["version"] == CLI_VERSION
        assert "healthy" in payload
        assert "checks" in payload

    def test_doctor_table_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code in {0, 1}
        assert "Checking SpecLeft installation" in result.output
        assert "specleft CLI available" in result.output
        assert "feature directory" in result.output

    def test_doctor_verbose_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--verbose"])
        assert result.exit_code in {0, 1}
        assert "pytest plugin" in result.output
        assert "feature directory" in result.output
