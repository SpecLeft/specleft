# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for convention-based discovery traceability inference."""

from __future__ import annotations

from pathlib import Path

from specleft.discovery.models import (
    DiscoveredItem,
    ItemKind,
    SupportedLanguage,
    TestFunctionMeta as DiscoveryTestFunctionMeta,
)
from specleft.discovery.traceability import infer_traceability
from specleft.schema import SpecsConfig


def _write_feature_spec(
    specs_dir: Path, *, feature_id: str, scenario_title: str
) -> Path:
    path = specs_dir / f"{feature_id}.md"
    path.write_text(
        "\n".join(
            [
                f"# Feature: {feature_id.replace('-', ' ').title()}",
                "",
                "## Scenarios",
                "",
                f"### Scenario: {scenario_title}",
                "priority: medium",
                "",
                "- Given a precondition",
                "- When an action happens",
                "- Then an outcome occurs",
                "",
            ]
        )
    )
    return path


def _discovered_test_item(*, file_path: str, function_name: str) -> DiscoveredItem:
    return DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name=function_name,
        file_path=Path(file_path),
        line_number=10,
        language=SupportedLanguage.PYTHON,
        raw_text=None,
        metadata=DiscoveryTestFunctionMeta(framework="pytest").model_dump(),
        confidence=0.9,
    )


def test_infer_traceability_links_matching_file_and_function(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".specleft" / "specs"
    specs_dir.mkdir(parents=True)
    spec_file = _write_feature_spec(
        specs_dir,
        feature_id="user-authentication",
        scenario_title="valid-credentials",
    )
    config = SpecsConfig.from_directory(specs_dir)

    links = infer_traceability(
        [
            _discovered_test_item(
                file_path="tests/test_user_authentication.py",
                function_name="test_valid_credentials",
            )
        ],
        config,
    )

    assert len(links) == 1
    link = links[0]
    assert link.test_file == Path("tests/test_user_authentication.py")
    assert link.test_function == "test_valid_credentials"
    assert link.spec_file == spec_file
    assert link.scenario_id == "valid-credentials"
    assert link.match_kind == "both"
    assert link.confidence == 0.9


def test_infer_traceability_avoids_false_positive_for_payment_file(
    tmp_path: Path,
) -> None:
    specs_dir = tmp_path / ".specleft" / "specs"
    specs_dir.mkdir(parents=True)
    _write_feature_spec(
        specs_dir,
        feature_id="user-authentication",
        scenario_title="valid-credentials",
    )
    config = SpecsConfig.from_directory(specs_dir)

    links = infer_traceability(
        [
            _discovered_test_item(
                file_path="tests/test_payment.py",
                function_name="test_valid_credentials",
            )
        ],
        config,
    )

    assert links == []


def test_infer_traceability_returns_empty_for_empty_specs() -> None:
    links = infer_traceability(
        [
            _discovered_test_item(
                file_path="tests/test_user_authentication.py",
                function_name="test_valid_credentials",
            )
        ],
        SpecsConfig(features=[]),
    )

    assert links == []


def test_infer_traceability_prefix_match_uses_function_kind(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".specleft" / "specs"
    specs_dir.mkdir(parents=True)
    _write_feature_spec(
        specs_dir,
        feature_id="user-authentication",
        scenario_title="valid-credentials",
    )
    config = SpecsConfig.from_directory(specs_dir)

    links = infer_traceability(
        [
            _discovered_test_item(
                file_path="tests/test_user_authentication.py",
                function_name="test_valid_credentials_with_mfa",
            )
        ],
        config,
    )

    assert len(links) == 1
    assert links[0].match_kind == "function"
    assert links[0].confidence == 0.6


def test_infer_traceability_uses_filename_match_for_single_scenario(
    tmp_path: Path,
) -> None:
    specs_dir = tmp_path / ".specleft" / "specs"
    specs_dir.mkdir(parents=True)
    _write_feature_spec(
        specs_dir,
        feature_id="user-authentication",
        scenario_title="valid-credentials",
    )
    config = SpecsConfig.from_directory(specs_dir)

    links = infer_traceability(
        [
            _discovered_test_item(
                file_path="tests/test_user_authentication.py",
                function_name="test_unrelated_case",
            )
        ],
        config,
    )

    assert len(links) == 1
    assert links[0].match_kind == "filename"
    assert links[0].confidence == 0.5
