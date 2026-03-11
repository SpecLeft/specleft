# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Start command for zero-to-value discovery onboarding."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from specleft.commands.doctor import _build_doctor_checks, _build_doctor_output
from specleft.commands.output import json_dumps, resolve_output_format
from specleft.discovery.file_index import FileIndex
from specleft.discovery.framework_detector import FrameworkDetector
from specleft.discovery.grouping import group_items
from specleft.discovery.models import (
    DEFAULT_DISCOVERY_OUTPUT_DIR,
    DraftFeature,
    ItemKind,
)
from specleft.discovery.pipeline import build_default_pipeline
from specleft.discovery.spec_writer import generate_draft_specs
from specleft.schema import SpecsConfig
from specleft.utils.specs_dir import DEFAULT_SPECS_DIR, FALLBACK_SPECS_DIR


@dataclass(frozen=True)
class _ComparisonRow:
    feature_id: str
    name: str
    code_scenarios: int
    spec_scenarios: int


def _run_health_check() -> dict[str, Any]:
    checks = _build_doctor_checks(verify_skill=False)
    return _build_doctor_output(checks)


def _resolve_specs_dir_for_root(
    root: Path,
    preferred: str | Path | None,
) -> Path:
    if preferred:
        preferred_path = Path(preferred)
        if preferred_path.is_absolute():
            return preferred_path
        return root / preferred_path

    project_default = root / DEFAULT_SPECS_DIR
    if project_default.exists():
        return project_default

    project_fallback = root / FALLBACK_SPECS_DIR
    if project_fallback.exists():
        return project_fallback

    return project_default


def _normalize_feature_id(feature_id: str) -> str:
    return feature_id.strip().lower().replace("_", "-")


def _load_specs_counts(specs_dir: Path) -> tuple[dict[str, int], list[str]]:
    if not specs_dir.exists():
        return {}, []

    try:
        config = SpecsConfig.from_directory(specs_dir)
    except Exception as exc:
        return {}, [f"specs_parse: {exc}"]

    counts: dict[str, int] = {}
    for feature in config.features:
        normalized = _normalize_feature_id(feature.feature_id)
        counts[normalized] = len(feature.all_scenarios)
    return counts, []


def _build_comparison_rows(
    features: list[DraftFeature],
    specs_counts: dict[str, int],
) -> list[_ComparisonRow]:
    rows: list[_ComparisonRow] = []
    for feature in sorted(features, key=lambda item: item.feature_id):
        code_scenarios = len(feature.scenarios)
        spec_scenarios = specs_counts.get(_normalize_feature_id(feature.feature_id), 0)
        rows.append(
            _ComparisonRow(
                feature_id=feature.feature_id,
                name=feature.name,
                code_scenarios=code_scenarios,
                spec_scenarios=spec_scenarios,
            )
        )
    return rows


def _missing_scenarios(rows: list[_ComparisonRow]) -> int:
    return sum(max(row.code_scenarios - row.spec_scenarios, 0) for row in rows)


def _items_by_kind_counts(report: Any) -> dict[str, int]:
    return {kind.value: len(report.items_by_kind.get(kind, [])) for kind in ItemKind}


def _frameworks_list(
    frameworks: dict[Any, list[str]],
) -> list[str]:
    flattened: list[str] = []
    seen: set[str] = set()
    for names in frameworks.values():
        for name in names:
            lowered = name.strip().lower()
            if not lowered or lowered in seen:
                continue
            seen.add(lowered)
            flattened.append(lowered)
    return flattened


def _render_detection_summary(
    *,
    languages: list[str],
    frameworks: list[str],
    files_scanned: int,
    test_functions: int,
) -> str:
    if not languages:
        language_label = "unknown"
    else:
        language_label = ", ".join(language.title() for language in languages)

    if frameworks:
        framework_label = ", ".join(frameworks)
        return (
            f"Detected: {language_label} ({framework_label}), "
            f"{files_scanned} files, {test_functions} test functions"
        )
    return f"Detected: {language_label}, {files_scanned} files, {test_functions} test functions"


def _build_table_lines(rows: list[_ComparisonRow]) -> list[str]:
    header_feature = "Feature"
    header_code = "Code"
    header_specs = "Specs"

    table_rows = [
        (
            row.feature_id,
            f"{row.code_scenarios} tests",
            "none" if row.spec_scenarios == 0 else f"{row.spec_scenarios} specs",
        )
        for row in rows
    ]

    feature_width = max(
        [len(header_feature), *[len(row[0]) for row in table_rows]], default=0
    )
    code_width = max(
        [len(header_code), *[len(row[1]) for row in table_rows]], default=0
    )
    specs_width = max(
        [len(header_specs), *[len(row[2]) for row in table_rows]], default=0
    )

    top = f"┌{'─' * (feature_width + 2)}┬{'─' * (code_width + 2)}┬{'─' * (specs_width + 2)}┐"
    divider = f"├{'─' * (feature_width + 2)}┼{'─' * (code_width + 2)}┼{'─' * (specs_width + 2)}┤"
    bottom = f"└{'─' * (feature_width + 2)}┴{'─' * (code_width + 2)}┴{'─' * (specs_width + 2)}┘"

    lines = [
        top,
        f"│ {header_feature.ljust(feature_width)} │ {header_code.ljust(code_width)} │ {header_specs.ljust(specs_width)} │",
        divider,
    ]
    for feature, code, specs in table_rows:
        lines.append(
            f"│ {feature.ljust(feature_width)} │ {code.ljust(code_width)} │ {specs.ljust(specs_width)} │"
        )
    lines.append(bottom)
    return lines


def _print_table_output(
    *,
    root: Path,
    rows: list[_ComparisonRow],
    languages: list[str],
    frameworks: list[str],
    files_scanned: int,
    items_by_kind: dict[str, int],
    feature_count: int,
    scenario_count: int,
    saved_paths: list[Path],
    errors: list[str],
) -> None:
    test_functions = items_by_kind.get(ItemKind.TEST_FUNCTION.value, 0)
    click.echo("Scanning project...")
    click.echo(
        f"✓ {_render_detection_summary(languages=languages, frameworks=frameworks, files_scanned=files_scanned, test_functions=test_functions)}"
    )
    click.echo("")
    click.echo("Discovering features...")
    click.echo(f"✓ Found {feature_count} features, {scenario_count} scenarios")
    click.echo("")
    click.echo("Your project vs your specs:")
    if rows:
        for line in _build_table_lines(rows):
            click.echo(line)
    else:
        click.echo("(no discovered features)")
    click.echo("")
    click.echo(
        f"You have {_missing_scenarios(rows)} test scenarios with no specifications."
    )
    click.echo("")
    click.echo("→ Run `specleft discover` to generate specs")
    click.echo("→ Run `specleft start --save` to save these results")

    if saved_paths:
        click.echo("")
        click.echo("Saved draft specs:")
        for path in saved_paths:
            click.echo(f"- {path}")

    if errors:
        click.echo("")
        click.echo("Errors:")
        for error in errors:
            click.echo(f"- {error}")
    click.echo(f"Project root: {root}")


@click.command("start")
@click.argument(
    "project_root",
    required=False,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option(
    "--save",
    is_flag=True,
    help="Persist draft specs to .specleft/specs/_discovered/.",
)
@click.option(
    "--specs-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Existing specs dir to compare against.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def start(
    project_root: Path | None,
    format_type: str | None,
    save: bool,
    specs_dir: Path | None,
    pretty: bool,
) -> None:
    """Run a discovery-first onboarding flow for existing codebases."""
    selected_format = resolve_output_format(format_type)
    root = (project_root or Path.cwd()).resolve()

    health = _run_health_check()
    if not health.get("healthy"):
        message = (
            "Health check failed. Run `specleft doctor` to diagnose your environment."
        )
        if selected_format == "json":
            payload = {
                "error": message,
                "checks": health.get("checks", {}),
                "errors": health.get("errors", []),
            }
            click.echo(json_dumps(payload, pretty=pretty))
        else:
            click.secho(message, fg="red", err=True)
        sys.exit(1)

    file_index = FileIndex(root)
    frameworks = FrameworkDetector().detect(root, file_index)
    report = build_default_pipeline(root).run()
    features = group_items(report.all_items)

    comparison_specs_dir = _resolve_specs_dir_for_root(root, specs_dir)
    specs_counts, specs_errors = _load_specs_counts(comparison_specs_dir)
    comparison_rows = _build_comparison_rows(features, specs_counts)

    saved_paths: list[Path] = []
    if save:
        output_dir = root / DEFAULT_DISCOVERY_OUTPUT_DIR
        saved_paths = generate_draft_specs(features, output_dir, dry_run=False)

    scenario_count = sum(len(feature.scenarios) for feature in features)
    languages = [language.value for language in report.languages_detected]
    framework_names = _frameworks_list(frameworks)
    items_by_kind = _items_by_kind_counts(report)
    errors = [*report.errors, *specs_errors]

    if selected_format == "json":
        payload = {
            "project": {
                "root": str(root),
                "languages": languages,
                "test_frameworks": framework_names,
                "files_scanned": file_index.total_files,
            },
            "discovery": {
                "features": len(features),
                "scenarios": scenario_count,
                "items_by_kind": items_by_kind,
            },
            "comparison": [
                {
                    "feature_id": row.feature_id,
                    "name": row.name,
                    "code_scenarios": row.code_scenarios,
                    "spec_scenarios": row.spec_scenarios,
                }
                for row in comparison_rows
            ],
            "saved": bool(saved_paths),
            "errors": errors,
        }
        click.echo(json_dumps(payload, pretty=pretty))
        return

    _print_table_output(
        root=root,
        rows=comparison_rows,
        languages=languages,
        frameworks=framework_names,
        files_scanned=file_index.total_files,
        items_by_kind=items_by_kind,
        feature_count=len(features),
        scenario_count=scenario_count,
        saved_paths=saved_paths,
        errors=errors,
    )
