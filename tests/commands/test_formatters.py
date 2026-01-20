"""Tests for SpecLeft formatter helpers."""

from __future__ import annotations

from specleft.commands.formatters import (
    badge_color,
    build_feature_json,
    format_coverage_percent,
    format_execution_time_key,
    format_execution_time_value,
    format_status_marker,
    get_priority_value,
    render_badge_svg,
)
from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecStep,
    StepType,
)


class TestFormatterHelpers:
    """Tests for format helper functions."""

    def test_get_priority_value_prefers_raw(self) -> None:
        scenario = ScenarioSpec(
            scenario_id="scenario",
            name="Scenario",
            priority=Priority.LOW,
            priority_raw=Priority.HIGH,
        )
        assert get_priority_value(scenario) == "high"

    def test_get_priority_value_defaults(self) -> None:
        scenario = ScenarioSpec(scenario_id="scenario", name="Scenario")
        assert get_priority_value(scenario) == "medium"

    def test_format_status_marker(self) -> None:
        assert format_status_marker("implemented") == "✓"
        assert format_status_marker("skipped") == "⚠"
        assert format_status_marker("missing") == "✗"

    def test_format_coverage_percent(self) -> None:
        assert format_coverage_percent(0, 0) is None
        assert format_coverage_percent(1, 2) == 50.0

    def test_format_execution_time_value(self) -> None:
        assert format_execution_time_value(ExecutionTime.FAST) == "Fast"
        assert format_execution_time_value("slow") == "Slow"

    def test_format_execution_time_key(self) -> None:
        assert format_execution_time_key(ExecutionTime.MEDIUM) == "medium"
        assert format_execution_time_key("fast") == "fast"

    def test_badge_color(self) -> None:
        assert badge_color(None) == "#9f9f9f"
        assert badge_color(95.0) == "#4cce5e"
        assert badge_color(70.0) == "#f0c648"
        assert badge_color(40.0) == "#e05d44"

    def test_render_badge_svg(self) -> None:
        svg = render_badge_svg("coverage", "95%", "#4cce5e")
        assert "coverage" in svg
        assert "95%" in svg
        assert "#4cce5e" in svg

    def test_build_feature_json_payload(self) -> None:
        feature = FeatureSpec(feature_id="auth", name="Auth Feature")
        scenario = ScenarioSpec(
            scenario_id="login",
            name="Login",
            priority_raw=Priority.HIGH,
            tags=["smoke"],
            steps=[SpecStep(type=StepType.GIVEN, description="a user")],
        )
        payload = build_feature_json(
            feature,
            scenarios=[scenario],
            include_status={"login": {"status": "implemented"}},
        )
        assert payload["feature_id"] == "auth"
        assert payload["title"] == "Auth Feature"
        assert payload["scenarios"][0]["id"] == "login"
        assert payload["scenarios"][0]["status"] == "implemented"
        assert payload["scenarios"][0]["priority"] == "high"

    def test_build_feature_json_without_status(self) -> None:
        feature = FeatureSpec(feature_id="checkout", name="Checkout")
        scenario = ScenarioSpec(
            scenario_id="pay",
            name="Pay",
            steps=[SpecStep(type=StepType.WHEN, description="pay")],
        )
        payload = build_feature_json(feature, scenarios=[scenario])
        assert payload["scenarios"][0].get("status") is None
        assert payload["scenarios"][0]["tags"] is None
