# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for discovery pipeline orchestration."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import specleft.discovery.pipeline as pipeline_module
from specleft.discovery.config import DiscoveryConfig
from specleft.discovery.context import MinerContext
from specleft.discovery.models import (
    DiscoveryReport,
    DiscoveredItem,
    DocstringMeta,
    ItemKind,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
)
from specleft.discovery.pipeline import DiscoveryPipeline, build_default_pipeline


def _doc_item(name: str) -> DiscoveredItem:
    return DiscoveredItem(
        kind=ItemKind.DOCSTRING,
        name=name,
        file_path=Path("README.md"),
        line_number=1,
        language=None,
        raw_text=name,
        metadata=DocstringMeta(
            target_kind="module",
            target_name="README",
            text=name,
        ).model_dump(),
        confidence=0.5,
    )


class _StaticMiner:
    def __init__(
        self,
        miner_id: uuid.UUID,
        name: str,
        languages: frozenset[SupportedLanguage],
        items: list[DiscoveredItem],
    ) -> None:
        self.miner_id = miner_id
        self.name = name
        self.languages = languages
        self._items = items

    def mine(self, ctx: MinerContext) -> MinerResult:
        _ = ctx
        return MinerResult(
            miner_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            miner_name="ignored",
            items=list(self._items),
            duration_ms=0,
        )


class _FailingMiner:
    def __init__(
        self,
        miner_id: uuid.UUID,
        name: str,
        languages: frozenset[SupportedLanguage],
        message: str,
    ) -> None:
        self.miner_id = miner_id
        self.name = name
        self.languages = languages
        self._message = message

    def mine(self, ctx: MinerContext) -> MinerResult:
        _ = ctx
        raise RuntimeError(self._message)


class _RecordingMiner:
    def __init__(
        self, miner_id: uuid.UUID, name: str, contexts: list[MinerContext]
    ) -> None:
        self.miner_id = miner_id
        self.name = name
        self.languages: frozenset[SupportedLanguage] = frozenset()
        self._contexts = contexts

    def mine(self, ctx: MinerContext) -> MinerResult:
        self._contexts.append(ctx)
        return MinerResult(
            miner_id=self.miner_id,
            miner_name=self.name,
            items=[_doc_item(self.name)],
            duration_ms=0,
        )


class _FrameworkDetectorSpy:
    def __init__(self) -> None:
        self.calls = 0

    def detect(
        self,
        root: Path,
        file_index: object,
    ) -> dict[SupportedLanguage, list[str]]:
        _ = file_index
        self.calls += 1
        assert root.is_absolute()
        return {SupportedLanguage.PYTHON: ["pytest"]}


def test_register_raises_for_duplicate_miner_uuid(tmp_path: Path) -> None:
    pipeline = DiscoveryPipeline(tmp_path)

    duplicate_id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    first = _StaticMiner(duplicate_id, "first", frozenset(), [_doc_item("one")])
    second = _StaticMiner(duplicate_id, "second", frozenset(), [_doc_item("two")])

    pipeline.register(first)
    with pytest.raises(ValueError, match="already registered"):
        pipeline.register(second)


def test_pipeline_calls_framework_detector_once_and_shares_context(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Demo\n")

    contexts: list[MinerContext] = []
    detector = _FrameworkDetectorSpy()
    pipeline = DiscoveryPipeline(tmp_path, framework_detector=detector)
    pipeline.register(
        _RecordingMiner(
            uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            "recording_a",
            contexts,
        )
    )
    pipeline.register(
        _RecordingMiner(
            uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            "recording_b",
            contexts,
        )
    )

    report = pipeline.run()

    assert detector.calls == 1
    assert len(contexts) == 2
    assert contexts[0] is contexts[1]
    assert contexts[0].frameworks == {SupportedLanguage.PYTHON: ["pytest"]}
    assert report.total_items == 2


def test_pipeline_captures_miner_exception_and_continues(tmp_path: Path) -> None:
    pipeline = DiscoveryPipeline(tmp_path, languages=[SupportedLanguage.PYTHON])
    pipeline.register(
        _StaticMiner(
            uuid.UUID("11111111-2222-3333-4444-555555555555"),
            "ok_miner",
            frozenset({SupportedLanguage.PYTHON}),
            [_doc_item("one"), _doc_item("two")],
        )
    )
    pipeline.register(
        _FailingMiner(
            uuid.UUID("66666666-7777-8888-9999-000000000000"),
            "bad_miner",
            frozenset({SupportedLanguage.PYTHON}),
            "boom",
        )
    )

    report = pipeline.run()

    assert len(report.miner_results) == 2
    assert report.total_items == 2

    error_result = next(r for r in report.miner_results if r.miner_name == "bad_miner")
    assert error_result.error == "bad_miner: boom"
    assert error_result.error_kind == MinerErrorKind.UNKNOWN
    assert report.errors == ["bad_miner: boom"]


def test_pipeline_language_filter_skips_non_overlapping_miners(tmp_path: Path) -> None:
    pipeline = DiscoveryPipeline(tmp_path, languages=[SupportedLanguage.PYTHON])

    pipeline.register(
        _StaticMiner(
            uuid.UUID("10000000-0000-0000-0000-000000000000"),
            "python_miner",
            frozenset({SupportedLanguage.PYTHON}),
            [_doc_item("python")],
        )
    )
    pipeline.register(
        _StaticMiner(
            uuid.UUID("20000000-0000-0000-0000-000000000000"),
            "agnostic_miner",
            frozenset(),
            [_doc_item("agnostic")],
        )
    )
    pipeline.register(
        _StaticMiner(
            uuid.UUID("30000000-0000-0000-0000-000000000000"),
            "typescript_miner",
            frozenset({SupportedLanguage.TYPESCRIPT}),
            [_doc_item("typescript")],
        )
    )

    report = pipeline.run()

    names = [result.miner_name for result in report.miner_results]
    assert names == ["python_miner", "agnostic_miner"]
    assert report.total_items == 2


def test_pipeline_sets_result_miner_id_and_name_from_miner(tmp_path: Path) -> None:
    expected_id = uuid.UUID("12345678-1234-1234-1234-1234567890ab")
    expected_name = "identity_miner"

    pipeline = DiscoveryPipeline(tmp_path, languages=[SupportedLanguage.PYTHON])
    pipeline.register(
        _StaticMiner(
            expected_id,
            expected_name,
            frozenset({SupportedLanguage.PYTHON}),
            [_doc_item("x")],
        )
    )

    report = pipeline.run()

    result = report.miner_results[0]
    assert result.miner_id == expected_id
    assert result.miner_name == expected_name


def test_build_default_pipeline_returns_report_even_if_all_miners_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.specleft]\n")

    miners = [
        _FailingMiner(
            uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111"),
            "fail_one",
            frozenset(),
            "first",
        ),
        _FailingMiner(
            uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222"),
            "fail_two",
            frozenset(),
            "second",
        ),
    ]
    monkeypatch.setattr(pipeline_module, "_default_miners", lambda: miners)

    pipeline = build_default_pipeline(tmp_path)
    report = pipeline.run()

    assert isinstance(report, DiscoveryReport)
    assert len(report.miner_results) == 2
    assert all(result.error is not None for result in report.miner_results)
    assert report.total_items == 0


def test_build_default_pipeline_uses_config_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("""
[tool.specleft.discovery]
exclude_dirs = [".git", "dist"]
source_dirs = ["src", "service"]
max_git_commits = 42
""".strip())

    pipeline = build_default_pipeline(tmp_path, config=None)

    assert pipeline._config == DiscoveryConfig(  # pyright: ignore[reportPrivateUsage]
        exclude_dirs=frozenset({".git", "dist"}),
        source_dirs=("src", "service"),
        max_git_commits=42,
    )


def test_build_default_pipeline_integration_on_specleft_repo_has_items() -> None:
    root = Path(__file__).resolve().parents[2]

    report = build_default_pipeline(root).run()

    assert report.total_items > 0
