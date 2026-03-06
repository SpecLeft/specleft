# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for discovery data models."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from specleft.discovery import models
from specleft.discovery.models import (
    ApiRouteMeta,
    DiscoveryReport,
    DiscoveredItem,
    ItemKind,
    MinerErrorKind,
    MinerResult,
    SupportedLanguage,
    TestFunctionMeta,
)
from specleft.schema import SpecStep, StepType


def test_all_models_importable() -> None:
    """Issue models are importable from specleft.discovery.models."""
    import_module("specleft.discovery.models")
    module = models

    assert module.SupportedLanguage
    assert module.ItemKind
    assert module.TestFunctionMeta
    assert module.ApiRouteMeta
    assert module.DraftScenario
    assert module.DraftFeature
    assert module.DraftSpec


def test_supported_language_members() -> None:
    """SupportedLanguage enum includes all required languages."""
    assert SupportedLanguage.PYTHON == "python"
    assert SupportedLanguage.TYPESCRIPT == "typescript"
    assert SupportedLanguage.JAVASCRIPT == "javascript"


def test_discovered_item_accepts_supported_language_and_none() -> None:
    """DiscoveredItem accepts enum values and None for language."""
    item = DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name="test_example",
        file_path=Path("test.py"),
        language=SupportedLanguage.PYTHON,
        metadata=TestFunctionMeta(framework="pytest").model_dump(),
        confidence=0.9,
    )
    assert item.language == SupportedLanguage.PYTHON

    item_none = DiscoveredItem(
        kind=ItemKind.GIT_COMMIT,
        name="add feature",
        file_path=None,
        language=None,
        metadata={"commit_hash": "abc1234", "subject": "add feature"},
        confidence=1.0,
    )
    assert item_none.language is None


def test_discovered_item_invalid_metadata_keys_raise_validation_error() -> None:
    """Invalid metadata keys should fail model validation."""
    with pytest.raises(ValidationError):
        DiscoveredItem(
            kind=ItemKind.TEST_FUNCTION,
            name="test_missing",
            file_path=Path("test.py"),
            language=SupportedLanguage.PYTHON,
            metadata={"class_name": "TestClass"},
            confidence=0.9,
        )


def test_discovered_item_typed_meta() -> None:
    """typed_meta() returns the matching metadata model."""
    item = DiscoveredItem(
        kind=ItemKind.API_ROUTE,
        name="create_user",
        file_path=Path("api.py"),
        language=SupportedLanguage.PYTHON,
        metadata={
            "http_method": "POST",
            "path": "/users",
            "framework": "fastapi",
        },
        confidence=0.8,
    )
    typed = item.typed_meta()
    assert isinstance(typed, ApiRouteMeta)
    assert typed.path == "/users"


def test_miner_result_field_types() -> None:
    """MinerResult carries typed IDs, names, and optional errors."""
    miner_id = UUID("a7b21db5-0d22-41be-9902-7c725e63892e")
    result = MinerResult(
        miner_id=miner_id,
        miner_name="python_test_functions",
        items=[],
        duration_ms=15,
        error="boom",
        error_kind=MinerErrorKind.UNKNOWN,
    )

    assert isinstance(result.miner_id, UUID)
    assert isinstance(result.miner_name, str)
    assert result.error_kind == MinerErrorKind.UNKNOWN
    assert result.items == []


def test_discovery_report_serializes_uuid_and_paths() -> None:
    """model_dump emits UUID and path values as JSON-safe primitives."""
    result = MinerResult(
        miner_id=UUID("a7b21db5-0d22-41be-9902-7c725e63892e"),
        miner_name="python_test_functions",
        items=[
            DiscoveredItem(
                kind=ItemKind.TEST_FUNCTION,
                name="test_ok",
                file_path=Path("/tmp/test.py"),
                language=SupportedLanguage.PYTHON,
                metadata=TestFunctionMeta(framework="pytest").model_dump(),
                confidence=0.9,
            )
        ],
        duration_ms=5,
    )

    report = DiscoveryReport(
        project_root=Path("/tmp"),
        languages_detected=[SupportedLanguage.PYTHON],
        miner_results=[result],
        total_items=1,
        errors=[],
        duration_ms=16,
    )

    dumped = report.model_dump()
    assert (
        str(dumped["miner_results"][0]["miner_id"])
        == "a7b21db5-0d22-41be-9902-7c725e63892e"
    )
    assert str(dumped["project_root"]) == "/tmp"
    assert str(dumped["miner_results"][0]["items"][0]["file_path"]) == "/tmp/test.py"


def test_discovery_report_cached_items_are_reusable() -> None:
    """all_items cached_property returns the same object each access."""
    report = DiscoveryReport(
        project_root=Path("/tmp"),
        languages_detected=[SupportedLanguage.PYTHON],
        miner_results=[],
        total_items=0,
        errors=[],
        duration_ms=0,
    )

    first = report.all_items
    second = report.all_items
    assert first is second


def test_discovery_report_items_by_kind() -> None:
    """items_by_kind groups flattened items by ItemKind."""
    test_item = DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name="test_ok",
        file_path=Path("test.py"),
        language=SupportedLanguage.PYTHON,
        metadata=TestFunctionMeta(framework="pytest").model_dump(),
        confidence=0.9,
    )
    route_item = DiscoveredItem(
        kind=ItemKind.API_ROUTE,
        name="/users",
        file_path=Path("api.py"),
        language=SupportedLanguage.PYTHON,
        metadata={
            "http_method": "GET",
            "path": "/users",
            "framework": "fastapi",
        },
        confidence=0.8,
    )

    report = DiscoveryReport(
        project_root=Path("/tmp"),
        languages_detected=[SupportedLanguage.PYTHON],
        miner_results=[
            MinerResult(
                miner_id=UUID("a7b21db5-0d22-41be-9902-7c725e63892e"),
                miner_name="python_test_functions",
                items=[test_item],
                duration_ms=10,
            ),
            MinerResult(
                miner_id=UUID("aa5151b6-3805-419c-a726-a56755300dda"),
                miner_name="api_route_miner",
                items=[route_item],
                duration_ms=10,
            ),
        ],
        total_items=2,
        errors=[],
        duration_ms=20,
    )

    groups = report.items_by_kind
    assert len(groups[ItemKind.TEST_FUNCTION]) == 1
    assert len(groups[ItemKind.API_ROUTE]) == 1


def test_discovery_report_round_trip_and_empty_miners() -> None:
    """DiscoveryReport can round-trip with empty miners and error miners."""
    good_item = DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name="test_ok",
        file_path=Path("test.py"),
        language=SupportedLanguage.PYTHON,
        metadata=TestFunctionMeta(framework="pytest").model_dump(),
        confidence=0.9,
    )

    error_result = MinerResult(
        miner_id=UUID("11111111-1111-1111-1111-111111111111"),
        miner_name="failing_miner",
        items=[],
        duration_ms=5,
        error="parse failed",
        error_kind=MinerErrorKind.PARSE_ERROR,
    )
    good_result = MinerResult(
        miner_id=UUID("22222222-2222-2222-2222-222222222222"),
        miner_name="test_miner",
        items=[good_item],
        duration_ms=10,
    )

    report = DiscoveryReport(
        project_root=Path("/tmp"),
        languages_detected=[SupportedLanguage.PYTHON],
        miner_results=[good_result, error_result],
        total_items=1,
        errors=[],
        duration_ms=30,
    )

    serialized = report.model_dump_json()
    reloaded = DiscoveryReport.model_validate_json(serialized)

    assert reloaded == report
    assert len(reloaded.all_items) == 1


def test_discovered_item_typed_meta_for_test_functions() -> None:
    """typed_meta() for test-function returns TestFunctionMeta."""
    item = DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name="test_path",
        file_path=Path("test_path.py"),
        language=SupportedLanguage.PYTHON,
        metadata=TestFunctionMeta(
            framework="pytest",
            decorators=["pytest.mark.parametrize"],
            is_parametrized=True,
        ).model_dump(),
        confidence=0.7,
    )
    assert isinstance(item.typed_meta(), TestFunctionMeta)


def test_draft_scenario_accepts_spec_steps() -> None:
    """DraftScenario accepts a list of existing SpecStep models."""
    draft = models.DraftScenario(
        title="login",
        priority="high",
        steps=[
            SpecStep(type=StepType.GIVEN, description="user is logged out"),
            SpecStep(type=StepType.WHEN, description="user submits credentials"),
            SpecStep(type=StepType.THEN, description="user sees dashboard"),
        ],
        source_items=[],
    )

    assert draft.steps[0].type == StepType.GIVEN
    assert draft.title == "login"
