# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Formatting helpers for CLI output."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from specleft.schema import ExecutionTime, FeatureSpec, Priority, ScenarioSpec, SpecStep


def get_priority_value(scenario: ScenarioSpec) -> str:
    """Get priority value string, defaulting to 'medium' if not set."""
    if scenario.priority_raw is not None:
        return scenario.priority_raw.value
    if scenario.priority is not None:
        return scenario.priority.value
    return Priority.MEDIUM.value


def format_status_marker(status: str) -> str:
    if status == "implemented":
        return "✓"
    if status == "skipped":
        return "⚠"
    return "✗"


def format_coverage_percent(implemented: int, total: int) -> float | None:
    if total == 0:
        return None
    return round((implemented / total) * 100, 1)


def format_execution_time_value(execution_time: str | ExecutionTime) -> str:
    value = (
        execution_time.value
        if isinstance(execution_time, ExecutionTime)
        else execution_time
    )
    return value.capitalize()


def format_execution_time_key(execution_time: str | ExecutionTime) -> str:
    return (
        execution_time.value
        if isinstance(execution_time, ExecutionTime)
        else str(execution_time)
    )


def badge_color(coverage: float | None) -> str:
    if coverage is None:
        return "#9f9f9f"
    if coverage >= 80:
        return "#4cce5e"
    if coverage >= 60:
        return "#f0c648"
    return "#e05d44"


def render_badge_svg(label: str, message: str, color: str) -> str:
    def _text_width(text: str) -> int:
        return max(1, len(text)) * 7

    label_width = _text_width(label) + 10
    message_width = _text_width(message) + 10
    total_width = label_width + message_width
    label_x = label_width / 2
    message_x = label_width + message_width / 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="'
        f'{total_width}" height="20" role="img" aria-label="{label}: {message}">'
        '<linearGradient id="s" x2="0" y2="100%">'
        '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        '<stop offset="1" stop-opacity=".1"/>'
        "</linearGradient>"
        f'<rect width="{label_width}" height="20" fill="#555"/>'
        f'<rect x="{label_width}" width="{message_width}" height="20" fill="{color}"/>'
        '<rect width="' + str(total_width) + '" height="20" fill="url(#s)"/>'
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana" font-size="11">'
        f'<text x="{label_x}" y="14">{label}</text>'
        f'<text x="{message_x}" y="14">{message}</text>'
        "</g>"
        "</svg>"
    )


def build_feature_json(
    feature: FeatureSpec,
    *,
    scenarios: Iterable[ScenarioSpec] | None = None,
    include_status: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scenario_items = list(scenarios) if scenarios is not None else feature.all_scenarios
    scenario_payloads: list[dict[str, Any]] = []

    for scenario in scenario_items:
        payload: dict[str, Any] = {
            "id": scenario.scenario_id,
            "title": scenario.name,
            "priority": scenario.priority_raw.value if scenario.priority_raw else None,
            "tags": scenario.tags or None,
            "steps": _build_steps_payload(scenario.steps),
        }
        if include_status and scenario.scenario_id in include_status:
            payload.update(include_status[scenario.scenario_id])
        scenario_payloads.append(payload)

    return {
        "feature_id": feature.feature_id,
        "title": feature.name,
        "confidence": feature.confidence,
        "source": feature.source,
        "assumptions": feature.assumptions,
        "open_questions": feature.open_questions,
        "tags": feature.tags or None,
        "owner": feature.owner,
        "component": feature.component,
        "scenarios": scenario_payloads,
    }


def _build_steps_payload(steps: list[SpecStep]) -> list[dict[str, str]]:
    return [
        {
            "type": step.type.value,
            "description": step.description,
        }
        for step in steps
    ]
