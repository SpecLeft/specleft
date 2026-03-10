"""Tests for discover command."""

from __future__ import annotations

import json
import uuid
from importlib import import_module
from pathlib import Path

import pytest
from click.testing import CliRunner

from specleft.cli.main import cli
from specleft.discovery.models import (
    DiscoveryReport,
    DraftFeature,
    DraftScenario,
    MinerResult,
    SupportedLanguage,
)
from specleft.schema import SpecStep, StepType

discover_module = import_module("specleft.commands.discover")


class _FakePipeline:
    def __init__(self, report: DiscoveryReport) -> None:
        self._report = report

    def run(self) -> DiscoveryReport:
        return self._report


def _report(
    root: Path,
    *,
    errors: list[str] | None = None,
    languages: list[SupportedLanguage] | None = None,
) -> DiscoveryReport:
    return DiscoveryReport(
        project_root=root,
        languages_detected=(
            languages if languages is not None else [SupportedLanguage.PYTHON]
        ),
        miner_results=[
            MinerResult(
                miner_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                miner_name="stub",
                items=[],
                error=errors[0] if errors else None,
                duration_ms=1,
            )
        ],
        total_items=0,
        errors=errors or [],
        duration_ms=4,
    )


def _draft_feature(feature_id: str, scenario_count: int = 1) -> DraftFeature:
    steps = [
        SpecStep(type=StepType.GIVEN, description="a precondition"),
        SpecStep(type=StepType.WHEN, description="an action happens"),
        SpecStep(type=StepType.THEN, description="an outcome is observed"),
    ]
    scenarios = [
        DraftScenario(
            title=f"{feature_id} scenario {index}",
            steps=steps,
            source_items=[],
        )
        for index in range(1, scenario_count + 1)
    ]
    return DraftFeature(
        feature_id=feature_id,
        name=feature_id.replace("-", " ").title(),
        scenarios=scenarios,
        source_items=[],
        confidence=0.8,
    )


class TestDiscoverCommand:
    def test_discover_dry_run_writes_no_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        monkeypatch.setattr(
            discover_module,
            "build_default_pipeline",
            lambda root, languages=None: _FakePipeline(_report(root)),
        )
        monkeypatch.setattr(
            discover_module,
            "group_items",
            lambda items: [_draft_feature("user-authentication", 2)],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["discover", "--dry-run", "--format", "json"])
            assert result.exit_code == 0

            payload = json.loads(result.output)
            assert payload["dry_run"] is True
            assert payload["total_features"] == 1
            assert payload["total_scenarios"] == 2
            assert Path(".specleft/specs/_discovered").exists() is False

    def test_discover_json_output_schema(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        monkeypatch.setattr(
            discover_module,
            "build_default_pipeline",
            lambda root, languages=None: _FakePipeline(_report(root)),
        )
        monkeypatch.setattr(
            discover_module,
            "group_items",
            lambda items: [_draft_feature("payment-processing", 3)],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["discover", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)

            assert payload["total_features"] == 1
            assert payload["total_scenarios"] == 3
            assert payload["output_dir"] == ".specleft/specs/_discovered"
            assert isinstance(payload["features"], list)
            assert payload["features"][0]["feature_id"] == "payment-processing"
            assert payload["features"][0]["output_file"].endswith(
                "payment-processing.md"
            )
            assert payload["errors"] == []

    def test_discover_writes_to_default_output_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        monkeypatch.setattr(
            discover_module,
            "build_default_pipeline",
            lambda root, languages=None: _FakePipeline(_report(root)),
        )
        monkeypatch.setattr(
            discover_module,
            "group_items",
            lambda items: [_draft_feature("user-authentication", 1)],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["discover", "--format", "json"])
            assert result.exit_code == 0
            assert Path(".specleft/specs/_discovered/user-authentication.md").exists()

    def test_discover_respects_output_dir_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        monkeypatch.setattr(
            discover_module,
            "build_default_pipeline",
            lambda root, languages=None: _FakePipeline(_report(root)),
        )
        monkeypatch.setattr(
            discover_module,
            "group_items",
            lambda items: [_draft_feature("user-authentication", 1)],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                ["discover", "--format", "json", "--output-dir", "tmp/out"],
            )
            assert result.exit_code == 0
            assert Path("tmp/out/user-authentication.md").exists()

    def test_discover_promote_all(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            source_dir = Path(".specleft/specs/_discovered")
            destination_dir = Path(".specleft/specs")
            source_dir.mkdir(parents=True, exist_ok=True)
            destination_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "user-authentication.md").write_text("# Feature: User Auth\n")
            (source_dir / "payments.md").write_text("# Feature: Payments\n")

            result = runner.invoke(
                cli,
                ["discover", "promote", "--all", "--format", "json"],
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert len(payload["promoted"]) == 2
            assert (destination_dir / "user-authentication.md").exists()
            assert (destination_dir / "payments.md").exists()

    def test_discover_promote_selected_feature(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            source_dir = Path(".specleft/specs/_discovered")
            destination_dir = Path(".specleft/specs")
            source_dir.mkdir(parents=True, exist_ok=True)
            destination_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "user-authentication.md").write_text("# Feature: User Auth\n")
            (source_dir / "payments.md").write_text("# Feature: Payments\n")

            result = runner.invoke(
                cli,
                ["discover", "promote", "user-authentication", "--format", "json"],
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert len(payload["promoted"]) == 1
            assert (destination_dir / "user-authentication.md").exists()
            assert (destination_dir / "payments.md").exists() is False

    def test_discover_promote_skips_existing_unless_overwrite(
        self, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            source_dir = Path(".specleft/specs/_discovered")
            destination_dir = Path(".specleft/specs")
            source_dir.mkdir(parents=True, exist_ok=True)
            destination_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "user-authentication.md").write_text("# Feature: New\n")
            existing = destination_dir / "user-authentication.md"
            existing.write_text("# Feature: Existing\n")

            result = runner.invoke(
                cli,
                ["discover", "promote", "user-authentication", "--format", "json"],
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["promoted"] == []
            assert len(payload["skipped"]) == 1
            assert existing.read_text() == "# Feature: Existing\n"

            overwrite_result = runner.invoke(
                cli,
                [
                    "discover",
                    "promote",
                    "user-authentication",
                    "--overwrite",
                    "--format",
                    "json",
                ],
            )
            overwrite_payload = json.loads(overwrite_result.output)
            assert overwrite_result.exit_code == 0
            assert len(overwrite_payload["promoted"]) == 1
            assert existing.read_text() == "# Feature: New\n"

    def test_discover_json_contains_errors_when_miner_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        monkeypatch.setattr(
            discover_module,
            "build_default_pipeline",
            lambda root, languages=None: _FakePipeline(
                _report(root, errors=["git_history: git binary missing"])
            ),
        )
        monkeypatch.setattr(discover_module, "group_items", lambda items: [])

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["discover", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["errors"] == ["git_history: git binary missing"]

    def test_discover_json_valid_when_all_miners_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        monkeypatch.setattr(
            discover_module,
            "build_default_pipeline",
            lambda root, languages=None: _FakePipeline(
                _report(root, errors=["miner_a: boom", "miner_b: boom"], languages=[])
            ),
        )
        monkeypatch.setattr(discover_module, "group_items", lambda items: [])

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["discover", "--format", "json"])
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["features"] == []
            assert payload["total_features"] == 0
            assert payload["total_scenarios"] == 0
            assert payload["errors"] == ["miner_a: boom", "miner_b: boom"]
