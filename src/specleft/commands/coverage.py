"""Coverage command."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from specleft.commands.formatters import (
    badge_color,
    format_coverage_percent,
    format_execution_time_key,
    render_badge_svg,
)
from specleft.commands.status import build_status_entries
from specleft.commands.types import (
    CoverageMetrics,
    CoverageOverall,
    CoverageTally,
    ScenarioStatusEntry,
)
from specleft.schema import ExecutionTime, Priority
from specleft.utils.structure import warn_if_nested_structure


def _coverage_summary(implemented: int, total: int) -> str:
    if total == 0:
        return "N/A"
    percent = format_coverage_percent(implemented, total)
    if percent is None:
        return "N/A"
    return f"{percent:.1f}% ({implemented}/{total})"


def _summary_row(label: str, summary: CoverageTally) -> str:
    if summary.total == 0:
        return f"  {label:<10} N/A (0/0)"
    percent = format_coverage_percent(summary.implemented, summary.total) or 0.0
    return f"  {label:<10} {percent:.1f}% ({summary.implemented}/{summary.total})"


def _format_priority_key(priority: Priority | None) -> str:
    if priority is None:
        return Priority.MEDIUM.value
    return priority.value


def _format_execution_key(execution_time: ExecutionTime) -> str:
    return format_execution_time_key(execution_time)


def _build_coverage_metrics(entries: list[ScenarioStatusEntry]) -> CoverageMetrics:
    total = len(entries)
    implemented = sum(1 for entry in entries if entry.status == "implemented")
    skipped = total - implemented

    features: dict[str, CoverageTally] = {}
    priorities: dict[str, CoverageTally] = {}
    execution_times: dict[str, CoverageTally] = {}

    for entry in entries:
        feature_key = entry.feature.feature_id
        features.setdefault(feature_key, CoverageTally())
        feature_tally = features[feature_key]
        features[feature_key] = CoverageTally(
            total=feature_tally.total + 1,
            implemented=feature_tally.implemented
            + (1 if entry.status == "implemented" else 0),
        )

        priority_key = _format_priority_key(entry.scenario.priority)
        priorities.setdefault(priority_key, CoverageTally())
        priority_tally = priorities[priority_key]
        priorities[priority_key] = CoverageTally(
            total=priority_tally.total + 1,
            implemented=priority_tally.implemented
            + (1 if entry.status == "implemented" else 0),
        )

        execution_key = _format_execution_key(entry.scenario.execution_time)
        execution_times.setdefault(execution_key, CoverageTally())
        execution_tally = execution_times[execution_key]
        execution_times[execution_key] = CoverageTally(
            total=execution_tally.total + 1,
            implemented=execution_tally.implemented
            + (1 if entry.status == "implemented" else 0),
        )

    overall = CoverageOverall(
        total=total,
        implemented=implemented,
        skipped=skipped,
        percent=format_coverage_percent(implemented, total),
    )

    return CoverageMetrics(
        overall=overall,
        by_feature=features,
        by_priority=priorities,
        by_execution_time=execution_times,
    )


def _build_coverage_json(entries: list[ScenarioStatusEntry]) -> dict[str, object]:
    metrics = _build_coverage_metrics(entries)
    feature_payload = []
    for feature_id, data in metrics.by_feature.items():
        feature_payload.append(
            {
                "feature_id": feature_id,
                "total": data.total,
                "implemented": data.implemented,
                "percent": format_coverage_percent(data.implemented, data.total),
            }
        )

    def _build_group_payload(
        values: dict[str, CoverageTally],
    ) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        for key, data in values.items():
            payload[key] = {
                "total": data.total,
                "implemented": data.implemented,
                "percent": format_coverage_percent(data.implemented, data.total),
            }
        return payload

    return {
        "timestamp": datetime.now().isoformat(),
        "coverage": {
            "overall": {
                "total_scenarios": metrics.overall.total,
                "implemented": metrics.overall.implemented,
                "skipped": metrics.overall.skipped,
                "percent": metrics.overall.percent,
            },
            "by_feature": feature_payload,
            "by_priority": _build_group_payload(metrics.by_priority),
            "by_execution_time": _build_group_payload(metrics.by_execution_time),
        },
    }


def _print_coverage_table(entries: list[ScenarioStatusEntry]) -> None:
    metrics = _build_coverage_metrics(entries)

    click.echo("Coverage Report")
    click.echo("━" * 58)
    click.echo(
        f"Overall Coverage: {_coverage_summary(metrics.overall.implemented, metrics.overall.total)}"
    )
    click.echo("")

    click.echo("By Feature:")
    feature_items = sorted(metrics.by_feature.items())
    for feature_id, data in feature_items:
        coverage = format_coverage_percent(data.implemented, data.total)
        coverage_label = "N/A" if coverage is None else f"{coverage:.1f}%"
        click.echo(
            f"  {feature_id:<12} {coverage_label} ({data.implemented}/{data.total})"
        )
    if not feature_items:
        click.echo("  None")

    click.echo("")
    click.echo("By Priority:")
    for priority in Priority:
        data = metrics.by_priority.get(priority.value, CoverageTally())
        click.echo(_summary_row(priority.value, data))

    click.echo("")
    click.echo("By Execution Time:")
    for execution_time in ExecutionTime:
        data = metrics.by_execution_time.get(execution_time.value, CoverageTally())
        click.echo(_summary_row(execution_time.value, data))
    click.echo("━" * 58)


@click.command("coverage")
@click.option(
    "--dir",
    "features_dir",
    default="features",
    help="Path to features directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json", "badge"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table', 'json', or 'badge'.",
)
@click.option(
    "--threshold",
    type=int,
    default=None,
    help="Exit non-zero if coverage below this percentage.",
)
@click.option(
    "--output",
    "output_path",
    type=str,
    default=None,
    help="Output file for badge format.",
)
def coverage(
    features_dir: str,
    format_type: str,
    threshold: int | None,
    output_path: str | None,
) -> None:
    """Show high-level coverage metrics."""
    from specleft.validator import load_specs_directory

    try:
        config = load_specs_directory(features_dir)
    except FileNotFoundError:
        click.secho(f"Directory not found: {features_dir}", fg="red", err=True)
        sys.exit(1)
    except ValueError as exc:
        click.secho(f"Unable to load specs: {exc}", fg="red", err=True)
        sys.exit(1)

    # Gentle nudge for nested structures (table output only)
    if format_type == "table":
        warn_if_nested_structure(Path(features_dir))

    entries = build_status_entries(config, Path("tests"))
    metrics = _build_coverage_metrics(entries)

    if format_type == "json":
        payload = _build_coverage_json(entries)
        click.echo(json.dumps(payload, indent=2))
    elif format_type == "badge":
        if not output_path:
            click.secho("Badge format requires --output.", fg="red", err=True)
            sys.exit(1)
        percent = metrics.overall.percent
        message = "n/a" if percent is None else f"{percent:.0f}%"
        svg = render_badge_svg("coverage", message, badge_color(percent))
        Path(output_path).write_text(svg)
        click.echo(f"Badge written to {output_path}")
    else:
        _print_coverage_table(entries)

    if threshold is not None:
        coverage_value = metrics.overall.percent
        if coverage_value is None or coverage_value < threshold:
            sys.exit(1)
