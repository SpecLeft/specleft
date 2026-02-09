"""Tests for 'specleft license' command."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.license.repo_identity import RepoIdentity

from tests.license.fixtures import (
    TEST_KEY_ID,
    TEST_PUBLIC_KEY_B64,
    add_trusted_key,
    create_core_policy_data,
    remove_trusted_key,
)


@pytest.fixture(autouse=True)
def setup_test_key():
    """Set up test key for each test."""
    add_trusted_key(TEST_KEY_ID, TEST_PUBLIC_KEY_B64)
    yield
    remove_trusted_key(TEST_KEY_ID)


def write_policy_file(
    base_dir: Path, policy_data: dict, filename: str = "policy.yml"
) -> Path:
    """Write a policy file to .specleft/policies/ directory."""
    license_dir = base_dir / ".specleft" / "policies"
    license_dir.mkdir(parents=True, exist_ok=True)
    policy_path = license_dir / filename

    def convert_dates(obj):
        if isinstance(obj, dict):
            return {k: convert_dates(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_dates(item) for item in obj]
        if isinstance(obj, date):
            return obj.isoformat()
        return obj

    policy_path.write_text(yaml.dump(convert_dates(policy_data)))
    return policy_path


class TestLicenseCommand:
    """Tests for 'specleft license' command."""

    def test_license_status_default_policy(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            policy_data = create_core_policy_data(licensed_to="test-owner/test-repo")
            write_policy_file(Path("."), policy_data)

            with patch(
                "specleft.license.status.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(cli, ["license", "status"])

            assert result.exit_code == 0
            assert "Core License: Apache 2.0" in result.output
            assert "Commercial License: Active" in result.output
            assert "License Type: Core" in result.output
            assert "License ID: lic_test12345678" in result.output
            assert "Validated File: .specleft/policies/policy.yml" in result.output

    def test_license_status_file_override(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            policy_data = create_core_policy_data(licensed_to="test-owner/test-repo")
            write_policy_file(Path("."), policy_data, filename="custom.yml")

            with patch(
                "specleft.license.status.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(
                    cli,
                    [
                        "license",
                        "status",
                        "--file",
                        ".specleft/policies/custom.yml",
                    ],
                )

            assert result.exit_code == 0
            assert "Commercial License: Active" in result.output
            assert "Validated File: .specleft/policies/custom.yml" in result.output

    def test_license_status_multiple_files_negative(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            license_dir = Path(".specleft/policies")
            license_dir.mkdir(parents=True, exist_ok=True)
            (license_dir / "01-invalid.yml").write_text("not: [valid: yaml")

            expired = date.today() - timedelta(days=1)
            policy_data = create_core_policy_data(
                licensed_to="test-owner/test-repo",
                expires_at=expired,
            )
            write_policy_file(Path("."), policy_data, filename="02-expired.yml")

            with patch(
                "specleft.license.status.detect_repo_identity",
                return_value=RepoIdentity(owner="test-owner", name="test-repo"),
            ):
                result = runner.invoke(cli, ["license", "status"])

            assert result.exit_code == 0
            assert "Commercial License: Inactive" in result.output
            assert "Validated File: .specleft/policies/02-expired.yml" in result.output
            assert "Valid Until: N/A" in result.output
