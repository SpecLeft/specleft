"""Tests for `specleft start` command."""

from __future__ import annotations

from importlib import import_module
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from specleft.cli.main import cli
from specleft.discovery.models import (
    DiscoveryReport,
    DraftFeature,
    DraftScenario,
    SupportedLanguage,
)
from specleft.schema import SpecStep, StepType

start_module = import_module("specleft.commands.start")


@pytest.fixture
def fake_python_project(tmp_path: Path) -> Path:
    """Create a minimal Python project that discovery can scan."""
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "auth").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "service.py").write_text("""
def add(a: int, b: int) -> int:
    return a + b
""".strip() + "\n")
    (tmp_path / "tests" / "auth" / "test_login.py").write_text("""
def test_valid_login() -> None:
    assert True
""".strip() + "\n")
    return tmp_path


def _patch_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        start_module,
        "_run_health_check",
        lambda: {"healthy": True, "checks": {}},
    )


def _patch_discovery_with_feature(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    feature_id: str = "authentication",
) -> None:
    feature = DraftFeature(
        feature_id=feature_id,
        name="Authentication",
        scenarios=[
            DraftScenario(
                title="valid-login",
                priority="medium",
                steps=[
                    SpecStep(type=StepType.GIVEN, description="context"),
                    SpecStep(type=StepType.WHEN, description="action"),
                    SpecStep(type=StepType.THEN, description="result"),
                ],
                source_items=[],
            )
        ],
        source_items=[],
        confidence=0.8,
    )

    class _FakePipeline:
        def run(self) -> DiscoveryReport:
            return DiscoveryReport(
                project_root=root,
                languages_detected=[SupportedLanguage.PYTHON],
                miner_results=[],
                total_items=1,
                errors=[],
                duration_ms=1,
            )

    monkeypatch.setattr(
        start_module, "build_default_pipeline", lambda _root: _FakePipeline()
    )
    monkeypatch.setattr(start_module, "group_items", lambda _items: [feature])


def test_start_exits_zero_and_returns_json_shape(
    fake_python_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_healthy(monkeypatch)
    monkeypatch.chdir(fake_python_project)
    runner = CliRunner()

    result = runner.invoke(cli, ["start", "--format", "json", "."])

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert set(payload) == {"project", "discovery", "comparison", "saved", "errors"}
    assert set(payload["project"]) == {
        "root",
        "languages",
        "test_frameworks",
        "files_scanned",
    }
    assert set(payload["discovery"]) == {"features", "scenarios", "items_by_kind"}
    assert set(payload["discovery"]["items_by_kind"]) == {
        "test_function",
        "api_route",
        "docstring",
        "git_commit",
    }
    assert payload["project"]["root"] == str(fake_python_project.resolve())
    assert "python" in payload["project"]["languages"]
    assert payload["saved"] is False


def test_start_without_save_does_not_write_discovered_specs(
    fake_python_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_healthy(monkeypatch)
    monkeypatch.chdir(fake_python_project)
    runner = CliRunner()

    result = runner.invoke(cli, ["start", "--format", "table", "."])

    assert result.exit_code == 0
    assert not (fake_python_project / ".specleft" / "specs" / "_discovered").exists()


def test_start_save_writes_draft_specs_and_prints_paths(
    fake_python_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_healthy(monkeypatch)
    monkeypatch.chdir(fake_python_project)
    _patch_discovery_with_feature(monkeypatch, fake_python_project.resolve())
    runner = CliRunner()

    result = runner.invoke(cli, ["start", "--save", "--format", "table", "."])

    assert result.exit_code == 0
    output_dir = fake_python_project / ".specleft" / "specs" / "_discovered"
    saved_files = sorted(output_dir.glob("*.md"))
    assert saved_files
    assert "Saved draft specs:" in result.output
    assert str(saved_files[0]) in result.output


def test_start_shows_non_zero_specs_count_when_existing_specs_found(
    fake_python_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_healthy(monkeypatch)
    monkeypatch.chdir(fake_python_project)
    _patch_discovery_with_feature(monkeypatch, fake_python_project.resolve())
    specs_dir = fake_python_project / ".specleft" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "authentication.md").write_text("""
# Feature: Authentication

## Scenarios

### Scenario: valid-login
priority: medium

- Given an existing account
- When valid credentials are provided
- Then access is granted
""".strip() + "\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["start", "--format", "table", "."])

    assert result.exit_code == 0
    assert "authentication" in result.output
    assert "1 specs" in result.output


def test_start_reports_git_errors_but_exits_zero(
    fake_python_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_healthy(monkeypatch)
    monkeypatch.chdir(fake_python_project)
    runner = CliRunner()

    result = runner.invoke(cli, ["start", "--format", "json", "."])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert any("git" in error.lower() for error in payload["errors"])


def test_start_uses_framework_detector_for_project_detection(
    fake_python_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_healthy(monkeypatch)
    monkeypatch.chdir(fake_python_project)

    calls: list[Path] = []

    class _FrameworkDetectorSpy:
        def detect(
            self,
            root: Path,
            file_index: object,
        ) -> dict[SupportedLanguage, list[str]]:
            _ = file_index
            calls.append(root)
            return {SupportedLanguage.PYTHON: ["pytest"]}

    class _FakePipeline:
        def __init__(self, root: Path) -> None:
            self._root = root

        def run(self) -> DiscoveryReport:
            return DiscoveryReport(
                project_root=self._root,
                languages_detected=[SupportedLanguage.PYTHON],
                miner_results=[],
                total_items=0,
                errors=[],
                duration_ms=1,
            )

    monkeypatch.setattr(start_module, "FrameworkDetector", _FrameworkDetectorSpy)
    monkeypatch.setattr(
        start_module, "build_default_pipeline", lambda root: _FakePipeline(root)
    )
    monkeypatch.setattr(start_module, "group_items", lambda _items: [])

    runner = CliRunner()
    result = runner.invoke(cli, ["start", "--format", "json", "."])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["project"]["test_frameworks"] == ["pytest"]
    assert calls == [fake_python_project.resolve()]
