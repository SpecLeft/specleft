# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Convention-based traceability inference for discovered test functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specleft.discovery.models import DiscoveredItem, ItemKind
from specleft.schema import FeatureSpec, ScenarioSpec, SpecsConfig


@dataclass(frozen=True)
class TraceabilityLink:
    """Inferred relationship between a test function and a spec scenario."""

    test_file: Path
    test_function: str
    spec_file: Path
    scenario_id: str
    match_kind: str
    confidence: float


@dataclass(frozen=True)
class _FeatureTraceabilityContext:
    spec_file: Path
    file_keys: frozenset[str]
    scenarios: tuple[ScenarioSpec, ...]


def infer_traceability(
    discovered: list[DiscoveredItem],
    specs: SpecsConfig,
) -> list[TraceabilityLink]:
    """Infer test-to-scenario links using conservative naming conventions."""
    if not specs.features:
        return []

    contexts = [_build_feature_context(feature) for feature in specs.features]
    links: list[TraceabilityLink] = []
    seen: set[tuple[str, str, str, str, str, float]] = set()

    for item in discovered:
        if item.kind is not ItemKind.TEST_FUNCTION or item.file_path is None:
            continue

        file_key = _normalize_filename(item.file_path.stem)
        if not file_key:
            continue

        function_key = _normalize_function(item.name)
        for context in contexts:
            if file_key not in context.file_keys:
                continue

            matches = _scenario_matches(function_key, context.scenarios)
            if not matches and len(context.scenarios) == 1:
                scenario = context.scenarios[0]
                scenario_key = _normalize_scenario_id(scenario.scenario_id)
                if scenario_key:
                    matches = [(scenario.scenario_id, "filename", 0.5)]

            for scenario_id, match_kind, confidence in matches:
                dedupe_key = (
                    item.file_path.as_posix(),
                    item.name,
                    context.spec_file.as_posix(),
                    scenario_id,
                    match_kind,
                    confidence,
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                links.append(
                    TraceabilityLink(
                        test_file=item.file_path,
                        test_function=item.name,
                        spec_file=context.spec_file,
                        scenario_id=scenario_id,
                        match_kind=match_kind,
                        confidence=confidence,
                    )
                )

    return sorted(
        links,
        key=lambda link: (
            link.spec_file.as_posix(),
            link.scenario_id,
            link.test_file.as_posix(),
            link.test_function,
        ),
    )


def _build_feature_context(feature: FeatureSpec) -> _FeatureTraceabilityContext:
    if feature.source_file is not None:
        spec_file = feature.source_file
    elif feature.source_dir is not None:
        spec_file = feature.source_dir / "_feature.md"
    else:
        spec_file = Path(f"{feature.feature_id}.md")

    file_keys = {
        _normalize_filename(feature.feature_id),
        _normalize_filename(spec_file.stem),
    }
    if feature.source_dir is not None:
        file_keys.add(_normalize_filename(feature.source_dir.name))

    scenarios = tuple(
        scenario
        for story in feature.stories
        for scenario in story.scenarios
        if scenario.scenario_id
    )
    return _FeatureTraceabilityContext(
        spec_file=spec_file,
        file_keys=frozenset(value for value in file_keys if value),
        scenarios=scenarios,
    )


def _scenario_matches(
    function_key: str,
    scenarios: tuple[ScenarioSpec, ...],
) -> list[tuple[str, str, float]]:
    if not function_key:
        return []

    matches: list[tuple[str, str, float]] = []
    for scenario in scenarios:
        scenario_key = _normalize_scenario_id(scenario.scenario_id)
        if not scenario_key:
            continue

        if function_key == scenario_key:
            matches.append((scenario.scenario_id, "both", 0.9))
            continue

        if _common_prefix_ratio(function_key, scenario_key) >= 0.6:
            matches.append((scenario.scenario_id, "function", 0.6))

    return matches


def _common_prefix_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0

    left_tokens = left.split()
    right_tokens = right.split()
    if not left_tokens or not right_tokens:
        return 0.0

    common_tokens = 0
    for left_token, right_token in zip(left_tokens, right_tokens, strict=False):
        if left_token != right_token:
            break
        common_tokens += 1

    if common_tokens == 0:
        return 0.0

    prefix = " ".join(left_tokens[:common_tokens]).strip()
    if not prefix:
        return 0.0

    shorter = min(len(left), len(right))
    if shorter == 0:
        return 0.0
    return len(prefix) / shorter


def _normalize_filename(stem: str) -> str:
    return _normalize_label(stem, strip_test_prefix=True)


def _normalize_function(function_name: str) -> str:
    return _normalize_label(function_name, strip_test_prefix=True)


def _normalize_scenario_id(scenario_id: str) -> str:
    return _normalize_label(scenario_id, strip_test_prefix=False)


def _normalize_label(value: str, *, strip_test_prefix: bool) -> str:
    normalized = value.strip().lower().replace("-", " ").replace("_", " ")
    if strip_test_prefix:
        if normalized.startswith("test "):
            normalized = normalized[len("test ") :]
        elif normalized.startswith("test"):
            normalized = normalized[len("test") :]
    return " ".join(normalized.split())
