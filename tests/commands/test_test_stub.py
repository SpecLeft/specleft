"""Tests for 'specleft test stub' command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from specleft.cli.main import cli
from specleft.commands.test import generate_test_stub
from specleft.schema import FeatureSpec, Priority, ScenarioSpec, SpecDataRow

from tests.helpers.specs import create_feature_specs, create_single_file_feature_spec


class TestStubCommand:
    """Tests for 'specleft test stub' command."""

    def test_stub_missing_features_dir(self) -> None:
        """Test stub command when features directory is missing."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["test", "stub"])
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_stub_generates_single_file(self) -> None:
        """Test stub command with --single-file flag."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(
                cli,
                ["test", "stub", "--single-file"],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("tests/test_generated.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content
            assert 'feature_id="auth"' in content
            assert 'scenario_id="login-success"' in content
            assert "skip=True" in content
            assert "Stub test - not yet implemented" in content
            assert "def test_login_success" in content
            assert "with specleft.step" not in content
            assert "pass  # TODO: Implement test" in content
            assert "Preview:" in result.output

    def test_stub_auto_detects_single_file_layout(self) -> None:
        """Test stub command auto-detects single-file layout."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="payments",
                scenario_id="card-charge",
            )

            result = runner.invoke(cli, ["test", "stub"], input="y\n")
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("tests/test_payments.py")
            assert generated_file.exists()

            content = generated_file.read_text()
            assert "from specleft import specleft" in content
            assert 'feature_id="payments"' in content
            assert 'scenario_id="card-charge"' in content

    def test_stub_auto_detects_nested_layout(self) -> None:
        """Test stub command auto-detects nested layout."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="legacy",
                story_id="billing",
                scenario_id="legacy-charge",
            )

            result = runner.invoke(cli, ["test", "stub"], input="y\n")
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("tests/legacy/test_billing.py")
            assert generated_file.exists()

    def test_stub_custom_output_dir(self) -> None:
        """Test stub command with custom output directory (single-file layout)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="inventory",
                scenario_id="check-stock",
            )

            result = runner.invoke(
                cli,
                [
                    "test",
                    "stub",
                    "--output-dir",
                    "custom_tests",
                ],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            generated_file = Path("custom_tests/test_inventory.py")
            assert generated_file.exists()

    def test_stub_custom_features_dir(self) -> None:
        """Test stub command with custom features directory (single-file layout)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            features_dir = create_single_file_feature_spec(
                Path("."),
                feature_id="support",
                scenario_id="open-ticket",
                features_dir_name="specs",
            )

            result = runner.invoke(
                cli, ["test", "stub", "-f", str(features_dir)], input="y\n"
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output
            assert Path("tests/test_support.py").exists()

    def test_stub_dry_run(self) -> None:
        """Test stub command dry-run mode."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(cli, ["test", "stub", "--dry-run"])
            assert result.exit_code == 0
            assert "Dry run: no files will be created." in result.output
            assert "Would create tests:" in result.output
            assert not Path("tests/test_auth.py").exists()

    def test_stub_json_format(self) -> None:
        """Test stub command JSON output format."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(
                cli,
                [
                    "test",
                    "stub",
                    "--format",
                    "json",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0
            assert '"would_create"' in result.output
            assert '"preview"' in result.output

    def test_stub_force_overwrites(self) -> None:
        """Test stub command force overwrites existing files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            first_run = runner.invoke(cli, ["test", "stub"], input="y\n")
            assert first_run.exit_code == 0
            generated_file = Path("tests/test_auth.py")
            assert generated_file.exists()
            initial_content = generated_file.read_text()

            second_run = runner.invoke(
                cli,
                ["test", "stub", "--force"],
                input="y\n",
            )
            assert second_run.exit_code == 0
            assert generated_file.read_text() == initial_content

    def test_stub_does_not_include_steps(self) -> None:
        """Test stub command does not include step blocks."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(
                cli,
                ["test", "stub", "--single-file"],
                input="y\n",
            )
            assert result.exit_code == 0

            content = Path("tests/test_generated.py").read_text()
            assert "with specleft.step" not in content

    def test_stub_includes_decorator(self) -> None:
        """Test stub command includes specleft decorator."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_single_file_feature_spec(
                Path("."),
                feature_id="auth",
                scenario_id="login-success",
            )

            result = runner.invoke(
                cli,
                ["test", "stub", "--single-file"],
                input="y\n",
            )
            assert result.exit_code == 0

            content = Path("tests/test_generated.py").read_text()
            assert "@specleft(" in content

    def test_stub_includes_parametrize(self) -> None:
        """Test stub command generates parameterized tests correctly."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            create_feature_specs(
                Path("."),
                feature_id="params",
                story_id="format",
                scenario_id="formatting",
                include_test_data=True,
            )

            result = runner.invoke(
                cli,
                ["test", "stub", "--single-file"],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "Confirm creation?" in result.output
            assert "✓ Created 1 test files" in result.output

            content = Path("tests/test_generated.py").read_text()
            assert "@pytest.mark.parametrize" in content
            assert "input, expected" in content
            assert "'a'" in content
            assert "'A'" in content
            assert "skip=True" in content

    def test_generate_test_stub_renders_single_method(self) -> None:
        """Test stub generator renders a single test method."""
        feature = FeatureSpec(feature_id="auth", name="Auth")
        scenario = ScenarioSpec(
            scenario_id="login-success",
            name="Login Success",
            description="User logs in successfully.",
            priority=Priority.HIGH,
            tags=["smoke"],
        )

        content = generate_test_stub(feature=feature, scenario=scenario)

        assert "@specleft(" in content
        assert 'feature_id="auth"' in content
        assert 'scenario_id="login-success"' in content
        assert "def test_login_success" in content
        assert "pass  # TODO: Implement test" in content
        assert "with specleft.step" not in content

    def test_generate_test_stub_includes_parametrize(self) -> None:
        """Test stub generator includes parametrize for data rows."""
        feature = FeatureSpec(feature_id="params", name="Params")
        scenario = ScenarioSpec(
            scenario_id="formatting",
            name="Formatting",
            priority=Priority.MEDIUM,
            test_data=[
                SpecDataRow(
                    params={"input": "a", "expected": "A"},
                    description="lowercase a",
                )
            ],
        )

        content = generate_test_stub(feature=feature, scenario=scenario)

        assert "@pytest.mark.parametrize" in content
        assert "input, expected" in content
        assert "'a'" in content
        assert "'A'" in content
