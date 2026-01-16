"""SpecLeft Pytest Plugin."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pytest

from specleft.decorators import get_current_steps


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "specleft_features_dir",
        "Directory containing SpecLeft specs",
        default="features",
    )
    parser.addini(
        "specleft_output_dir",
        "Output directory for SpecLeft results",
        default=".specleft",
    )
    parser.addini(
        "specleft_tag",
        "Default SpecLeft tag filters",
        default=[],
        type="args",
    )
    parser.addini(
        "specleft_priority",
        "Default SpecLeft priority filters",
        default=[],
        type="args",
    )
    parser.addini(
        "specleft_feature",
        "Default SpecLeft feature filters",
        default=[],
        type="args",
    )
    parser.addini(
        "specleft_scenario",
        "Default SpecLeft scenario filters",
        default=[],
        type="args",
    )
    parser.addoption(
        "--specleft-tag",
        action="append",
        default=[],
        dest="specleft_tags",
        help="Filter SpecLeft tests by scenario tag (repeatable)",
    )
    parser.addoption(
        "--specleft-priority",
        action="append",
        default=[],
        dest="specleft_priorities",
        help="Filter SpecLeft tests by scenario priority (repeatable)",
    )
    parser.addoption(
        "--specleft-feature",
        action="append",
        default=[],
        dest="specleft_features",
        help="Filter SpecLeft tests by feature_id (repeatable)",
    )
    parser.addoption(
        "--specleft-scenario",
        action="append",
        default=[],
        dest="specleft_scenarios",
        help="Filter SpecLeft tests by scenario_id (repeatable)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config._specleft_results: list[dict[str, Any]] = []
    config._specleft_start_time = datetime.now()
    config._specleft_specs_config: Optional[Any] = None

    config.addinivalue_line(
        "markers",
        "specleft(feature_id, scenario_id): Mark test with SpecLeft metadata",
    )

    features_dir = config.getini("specleft_features_dir") or "features"
    features_path = Path(features_dir)
    if not features_path.is_absolute():
        features_path = config.rootpath / features_path

    if features_path.exists():
        try:
            from specleft.schema import SpecsConfig

            config._specleft_specs_config = SpecsConfig.from_directory(features_path)
        except Exception:
            pass


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    specs_config = getattr(config, "_specleft_specs_config", None)
    tag_filters = {
        tag.strip()
        for tag in (config.getini("specleft_tag") or [])
        + (config.getoption("specleft_tags") or [])
    }
    priority_filters = {
        priority.strip().lower()
        for priority in (config.getini("specleft_priority") or [])
        + (config.getoption("specleft_priorities") or [])
    }
    feature_filters = {
        feature.strip()
        for feature in (config.getini("specleft_feature") or [])
        + (config.getoption("specleft_features") or [])
    }
    scenario_filters = {
        scenario.strip()
        for scenario in (config.getini("specleft_scenario") or [])
        + (config.getoption("specleft_scenarios") or [])
    }
    use_filters = any(
        (tag_filters, priority_filters, feature_filters, scenario_filters)
    )

    for item in items:
        func = getattr(item, "function", None)
        if func is None:
            continue

        feature_id = getattr(func, "_specleft_feature_id", None)
        scenario_id = getattr(func, "_specleft_scenario_id", None)

        if feature_id is None or scenario_id is None:
            continue

        item._specleft_metadata = {
            "feature_id": feature_id,
            "scenario_id": scenario_id,
            "test_name": item.name,
            "original_name": getattr(item, "originalname", item.name),
            "nodeid": item.nodeid,
            "is_parameterized": hasattr(item, "callspec"),
            "parameters": dict(item.callspec.params)
            if hasattr(item, "callspec")
            else {},
        }

        scenario = None
        if specs_config:
            scenario = specs_config.get_scenario(scenario_id)
            if scenario:
                for tag in scenario.tags:
                    marker_name = _sanitize_marker_name(tag)
                    item.add_marker(getattr(pytest.mark, marker_name))
                priority_marker = f"priority_{scenario.priority.value}"
                item.add_marker(getattr(pytest.mark, priority_marker))

        if use_filters:
            if not _matches_filters(
                feature_id=feature_id,
                scenario_id=scenario_id,
                scenario=scenario,
                tag_filters=tag_filters,
                priority_filters=priority_filters,
                feature_filters=feature_filters,
                scenario_filters=scenario_filters,
            ):
                item.add_marker(
                    pytest.mark.skip(reason="Filtered by SpecLeft selection")
                )


def _sanitize_marker_name(tag: str) -> str:
    """Sanitize a tag name to be a valid pytest marker."""
    return tag.replace("-", "_")


def _matches_filters(
    feature_id: str,
    scenario_id: str,
    scenario: Optional[Any],
    tag_filters: set[str],
    priority_filters: set[str],
    feature_filters: set[str],
    scenario_filters: set[str],
) -> bool:
    if feature_filters and feature_id not in feature_filters:
        return False
    if scenario_filters and scenario_id not in scenario_filters:
        return False

    if scenario is None:
        return not tag_filters and not priority_filters

    scenario_tags = {_sanitize_marker_name(tag) for tag in scenario.tags}
    scenario_priority = scenario.priority.value.lower()

    if tag_filters and not scenario_tags.intersection(tag_filters):
        return False
    if priority_filters and scenario_priority not in priority_filters:
        return False

    return True


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Any:
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    metadata = getattr(item, "_specleft_metadata", None)
    if metadata is None:
        return

    steps = get_current_steps()

    result = {
        **metadata,
        "status": report.outcome,
        "duration": report.duration,
        "error": str(report.longrepr) if report.failed else None,
        "steps": [
            {
                "description": step.description,
                "status": step.status,
                "duration": step.duration,
                "error": step.error,
                "skipped_reason": step.skipped_reason,
            }
            for step in steps
        ],
    }
    item.config._specleft_results.append(result)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    results = getattr(config, "_specleft_results", [])

    if not results:
        return

    from specleft.collector import ResultCollector

    output_dir = config.getini("specleft_output_dir") or ".specleft"
    collector = ResultCollector(output_dir=f"{output_dir}/results")

    results_data = collector.collect(results)
    filepath = collector.write(results_data)

    summary = results_data["summary"]
    print(f"\n{'═' * 60}")
    print("SpecLeft Test Results")
    print(f"{'═' * 60}")
    print(f"Total Executions: {summary['total_executions']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Duration: {summary['duration']:.2f}s")
    print(f"\nResults saved to: {filepath}")
    print(f"{'═' * 60}\n")
