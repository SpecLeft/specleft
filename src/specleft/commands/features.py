# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Features command group."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click

from specleft.commands.output import json_dumps, resolve_output_format
from specleft.commands.test import generate_test_stub
from specleft.schema import (
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecStep,
    SpecsConfig,
    StepType,
)
from specleft.utils.feature_writer import (
    add_scenario_to_feature,
    create_feature_file,
    generate_feature_id,
    generate_scenario_id,
    validate_feature_id,
    validate_scenario_id,
    validate_step_keywords,
)
from specleft.utils.history import log_feature_event
from specleft.utils.messaging import print_support_footer
from specleft.utils.specs_dir import resolve_specs_dir
from specleft.utils.structure import warn_if_nested_structure
from specleft.utils.test_discovery import TestDiscoveryResult, discover_pytest_tests
from specleft.utils.text import to_snake_case
from specleft.validator import SpecStats


def _build_features_list_json(config: SpecsConfig) -> dict[str, object]:
    from specleft.commands.formatters import build_feature_json

    features_payload: list[dict[str, object]] = []
    story_count = 0
    scenario_count = 0

    for feature in config.features:
        story_count += len(feature.stories)
        scenario_count += len(feature.all_scenarios)
        features_payload.append(build_feature_json(feature))

    return {
        "timestamp": datetime.now().isoformat(),
        "features": features_payload,
        "summary": {
            "features": len(config.features),
            "stories": story_count,
            "scenarios": scenario_count,
        },
    }


def _build_features_stats_json(
    *,
    features_dir: Path,
    tests_dir: str,
    stats: SpecStats | None,
    spec_scenario_ids: set[str],
    test_discovery: TestDiscoveryResult,
) -> dict[str, object]:
    coverage_payload: dict[str, object] = {
        "scenarios_with_tests": 0,
        "scenarios_without_tests": 0,
        "coverage_percent": None,
        "uncovered_scenarios": [],
    }
    specs_payload: dict[str, object] | None
    if stats is None:
        specs_payload = None
    else:
        spec_stats = cast(Any, stats)
        specs_payload = {
            "features": spec_stats.feature_count,
            "stories": spec_stats.story_count,
            "scenarios": spec_stats.scenario_count,
            "steps": spec_stats.step_count,
            "parameterized_scenarios": spec_stats.parameterized_scenario_count,
            "tags": sorted(spec_stats.tags) if spec_stats.tags else [],
        }
        if spec_stats.scenario_count > 0:
            scenarios_with_tests = spec_scenario_ids.intersection(
                test_discovery.specleft_scenario_ids
            )
            scenarios_without_tests = (
                spec_scenario_ids - test_discovery.specleft_scenario_ids
            )
            coverage_percent = (
                len(scenarios_with_tests) / spec_stats.scenario_count * 100
            )
            coverage_payload = {
                "scenarios_with_tests": len(scenarios_with_tests),
                "scenarios_without_tests": len(scenarios_without_tests),
                "coverage_percent": round(coverage_percent, 1),
                "uncovered_scenarios": sorted(scenarios_without_tests),
            }

    return {
        "timestamp": datetime.now().isoformat(),
        "directories": {
            "features": f"{features_dir}/",
            "tests": f"{tests_dir}/",
        },
        "pytest": {
            "total_tests": test_discovery.total_tests,
            "specleft_tests": test_discovery.specleft_tests,
            "error": test_discovery.error,
        },
        "specs": specs_payload,
        "coverage": coverage_payload,
    }


def _ensure_interactive(interactive: bool) -> None:
    if interactive and not sys.stdin.isatty():
        click.secho(
            "Interactive mode requires a terminal. Use explicit options instead.",
            fg="red",
            err=True,
        )
        print_support_footer()
        sys.exit(1)


def _parse_tags(tags: str | None) -> list[str] | None:
    if not tags:
        return None
    cleaned = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return cleaned or None


def _normalize_priority(value: str | None) -> Priority | None:
    if not value:
        return None
    try:
        return Priority(value.lower())
    except ValueError:
        return None


def _build_feature_test_path(feature_id: str, tests_dir: Path | None = None) -> Path:
    base_dir = tests_dir or Path("tests")
    return base_dir / f"test_{to_snake_case(feature_id)}.py"


def _parse_tests_dir(tests_dir: str | Path | None) -> Path | None:
    if not tests_dir:
        return None
    path = tests_dir if isinstance(tests_dir, Path) else Path(tests_dir)
    if path.suffix == ".py":
        raise click.BadParameter(
            "Tests directory must be a directory path, not a file path."
        )
    return path


def _normalize_tests_dir(
    _ctx: click.Context | None, _param: click.Parameter | None, value: Path | None
) -> Path | None:
    return _parse_tests_dir(value)


def _build_stub_test_method(feature_id: str, scenario: ScenarioSpec) -> str:
    feature = FeatureSpec(feature_id=feature_id, name=feature_id)
    return generate_test_stub(feature=feature, scenario=scenario).rstrip()


def _build_skeleton_test_method(feature_id: str, scenario: ScenarioSpec) -> str:
    priority = scenario.priority or Priority.MEDIUM
    doc_lines = [scenario.name, "", f"Priority: {priority.value}"]
    if scenario.tags:
        doc_lines.append(f"Tags: {', '.join(scenario.tags)}")
    docstring = "\n".join(doc_lines)

    lines = [
        "@specleft(",
        f'    feature_id="{feature_id}",',
        f'    scenario_id="{scenario.scenario_id}",',
        "    skip=True,",
        '    reason="Skeleton test - not yet implemented",',
        ")",
        f"def test_{to_snake_case(scenario.scenario_id)}():",
        f'    """{docstring}\n    """',
    ]

    for step in scenario.steps:
        description = f"{step.type.value.capitalize()} {step.description}"
        prefix = "f" if "{" in description or "}" in description else ""
        lines.append(f"    with specleft.step({prefix}{description!r}):")
        lines.append("        pass # TODO: Implement step")
        lines.append("")

    if not scenario.steps:
        lines.append("    pass  # TODO: Implement test")

    return "\n".join(lines).rstrip()


def _write_or_append_test(
    *,
    test_path: Path,
    method_content: str,
    header: str,
    scenario_id: str,
    dry_run: bool,
) -> tuple[bool, str | None]:
    if test_path.exists():
        content = test_path.read_text()
        if f'scenario_id="{scenario_id}"' in content:
            return False, "Test already exists for this scenario"
        if dry_run:
            return True, None
        updated = content.rstrip() + "\n\n" + method_content.rstrip() + "\n"
        test_path.write_text(updated)
        return True, None

    if dry_run:
        return True, None

    test_path.parent.mkdir(parents=True, exist_ok=True)
    content = header.rstrip() + "\n\n" + method_content.rstrip() + "\n"
    test_path.write_text(content)
    return True, None


def _build_test_header(kind: str) -> str:
    if kind == "skeleton":
        title = "skeleton"
        regen = "specleft test skeleton"
    else:
        title = "stub"
        regen = "specleft test stub"
    return (
        '"""\n'
        f"Auto-generated {title} tests from Markdown specs.\n"
        f"Regenerate using: {regen}\n\n"
        "Generated by SpecLeft - https://github.com/SpecLeft/specleft\n"
        '"""\n\n'
        "import pytest\n\n"
        "from specleft import specleft\n"
    )


def _parse_steps(steps: tuple[str, ...]) -> list[str]:
    return [step for step in steps if step.strip()]


def _build_scenario_spec(
    *,
    scenario_id: str,
    title: str,
    priority: Priority | None,
    tags: list[str] | None,
    steps: list[str],
) -> ScenarioSpec:
    parsed_steps: list[SpecStep] = []
    pattern = r"^[-*]?\s*(?:\*\*)?(Given|When|Then|And|But)(?:\*\*)?\s+(.+)$"
    for raw in steps:
        cleaned = raw.strip()
        match = re.match(pattern, cleaned, re.IGNORECASE)
        if match:
            step_type = StepType(match.group(1).lower())
            description = match.group(2).strip()
        else:
            step_type = StepType.GIVEN
            description = cleaned.lstrip("-").strip()
        parsed_steps.append(SpecStep(type=step_type, description=description))

    scenario_priority = priority or Priority.MEDIUM
    return ScenarioSpec(
        scenario_id=scenario_id,
        name=title,
        priority=scenario_priority,
        priority_raw=priority,
        tags=tags or [],
        steps=parsed_steps,
    )


def _print_feature_add_result(
    *,
    result: dict[str, object],
    format_type: str,
    dry_run: bool,
    pretty: bool,
) -> None:
    if format_type == "json":
        if result.get("success") is False:
            click.echo(json_dumps(result, pretty=pretty))
            return

        if dry_run:
            payload = {
                "dry_run": True,
                "feature_id": result.get("feature_id"),
                "file": result.get("file_path"),
            }
        else:
            payload = {
                "created": True,
                "feature_id": result.get("feature_id"),
                "file": result.get("file_path"),
            }
        click.echo(json_dumps(payload, pretty=pretty))
        return

    if result.get("success") is False:
        click.secho(f"Error: {result.get('error')}", fg="red", err=True)
        print_support_footer()
        return

    status = "Would create" if dry_run else "Created"
    click.secho(f"{status} feature file:", fg="green")
    click.echo(f"  {result.get('file_path')}")
    if result.get("feature_id"):
        click.echo(f"  Feature ID: {result.get('feature_id')}")
    if result.get("title"):
        click.echo(f"  Title: {result.get('title')}")
    if result.get("priority"):
        click.echo(f"  Priority: {result.get('priority')}")
    click.echo("")


def _print_scenario_add_result(
    *,
    result: dict[str, object],
    format_type: str,
    dry_run: bool,
    warnings: list[str],
    pretty: bool,
) -> None:
    if format_type == "json":
        if result.get("success") is False:
            click.echo(json_dumps(result, pretty=pretty))
            return

        if dry_run:
            payload = {
                "dry_run": True,
                "feature_id": result.get("feature_id"),
                "scenario_id": result.get("scenario_id"),
                "file": result.get("file_path"),
            }
        else:
            payload = {
                "created": True,
                "feature_id": result.get("feature_id"),
                "scenario_id": result.get("scenario_id"),
                "file": result.get("file_path"),
            }
        if result.get("test_preview"):
            payload["test_preview"] = result.get("test_preview")
        if warnings:
            payload["warnings"] = warnings
        click.echo(json_dumps(payload, pretty=pretty))
        return

    if result.get("success") is False:
        click.secho(f"Error: {result.get('error')}", fg="red", err=True)
        print_support_footer()
        return

    status = "Would append" if dry_run else "Appended"
    click.secho(f"{status} scenario:", fg="green")
    click.echo(f"  {result.get('file_path')}")
    click.echo(f"  Feature ID: {result.get('feature_id')}")
    click.echo(f"  Scenario ID: {result.get('scenario_id')}")
    if result.get("title"):
        click.echo(f"  Title: {result.get('title')}")
    if result.get("priority"):
        click.echo(f"  Priority: {result.get('priority')}")
    if result.get("steps_count") is not None:
        click.echo(f"  Steps: {result.get('steps_count')}")
    if warnings:
        click.echo("")
        click.secho("Warnings:", fg="yellow")
        for warning in warnings:
            click.echo(f"  - {warning}")
    click.echo("")


@click.group()
def features() -> None:
    """Feature definition management."""
    pass


@features.command("validate")
@click.option(
    "--dir",
    "features_dir",
    default=None,
    help="Path to features directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def features_validate(
    features_dir: str | None, format_type: str | None, strict: bool, pretty: bool
) -> None:
    """Validate Markdown specs in a features directory."""
    from specleft.validator import collect_spec_stats, load_specs_directory

    selected_format = resolve_output_format(format_type)
    warnings: list[dict[str, object]] = []
    resolved_features_dir = resolve_specs_dir(features_dir)
    try:
        config = load_specs_directory(resolved_features_dir)
        stats = collect_spec_stats(config)

        # Gentle nudge for nested structures (table output only)
        if selected_format != "json":
            warn_if_nested_structure(resolved_features_dir)

        if selected_format == "json":
            click.echo(json_dumps({"valid": True}, pretty=pretty))
        else:
            click.secho(
                f"✅ Features directory '{resolved_features_dir}/' is valid", bold=True
            )
            click.echo("")
            click.secho("Summary:", fg="cyan")
            click.echo(f"  Features: {stats.feature_count}")
            click.echo(f"  Stories: {stats.story_count}")
            click.echo(f"  Scenarios: {stats.scenario_count}")
            click.echo(f"  Steps: {stats.step_count}")
        if strict and warnings:
            sys.exit(2)
        sys.exit(0)
    except FileNotFoundError:
        if selected_format == "json":
            payload = {
                "valid": False,
                "errors": [
                    {
                        "file": str(resolved_features_dir),
                        "message": f"Directory not found: {resolved_features_dir}",
                        "fix_command": f"mkdir -p {resolved_features_dir}",
                    }
                ],
            }
            click.echo(json_dumps(payload, pretty=pretty))
        else:
            click.secho(
                f"✗ Directory not found: {resolved_features_dir}",
                fg="red",
                err=True,
            )
            print_support_footer()
        sys.exit(1)
    except ValueError as e:
        if selected_format == "json":
            payload = {
                "valid": False,
                "errors": [
                    {
                        "message": str(e),
                    }
                ],
            }
            click.echo(json_dumps(payload, pretty=pretty))
        else:
            click.secho(f"✗ Validation failed: {e}", fg="red", err=True)
            print_support_footer()
        sys.exit(1)
    except Exception as e:
        if selected_format == "json":
            payload = {
                "valid": False,
                "errors": [
                    {
                        "message": f"Unexpected validation failure: {e}",
                    }
                ],
            }
            click.echo(json_dumps(payload, pretty=pretty))
        else:
            click.secho(f"✗ Unexpected validation failure: {e}", fg="red", err=True)
            print_support_footer()
        sys.exit(1)


@features.command("list")
@click.option(
    "--dir",
    "features_dir",
    default=None,
    help="Path to features directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def features_list(
    features_dir: str | None, format_type: str | None, pretty: bool
) -> None:
    """List features, stories, and scenarios."""
    from specleft.validator import load_specs_directory

    selected_format = resolve_output_format(format_type)
    resolved_features_dir = resolve_specs_dir(features_dir)
    try:
        config = load_specs_directory(resolved_features_dir)
    except FileNotFoundError:
        if selected_format == "json":
            error_payload = {
                "status": "error",
                "message": f"Directory not found: {resolved_features_dir}",
            }
            click.echo(json_dumps(error_payload, pretty=pretty))
        else:
            click.secho(
                f"✗ Directory not found: {resolved_features_dir}",
                fg="red",
                err=True,
            )
            print_support_footer()
        sys.exit(1)
    except ValueError as e:
        if selected_format == "json":
            error_payload = {
                "status": "error",
                "message": f"Unable to load specs: {e}",
            }
            click.echo(json_dumps(error_payload, pretty=pretty))
        else:
            click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
            print_support_footer()
        sys.exit(1)
    except Exception as e:
        if selected_format == "json":
            error_payload = {
                "status": "error",
                "message": f"Unexpected error loading specs: {e}",
            }
            click.echo(json_dumps(error_payload, pretty=pretty))
        else:
            click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
            print_support_footer()
        sys.exit(1)

    if selected_format == "json":
        payload = _build_features_list_json(config)
        click.echo(json_dumps(payload, pretty=pretty))
        return

    # Gentle nudge for nested structures
    warn_if_nested_structure(resolved_features_dir)

    click.echo(f"Features ({len(config.features)}):")
    for feature in config.features:
        click.echo(f"- {feature.feature_id}: {feature.name}")
        for story in feature.stories:
            click.echo(f"  - {story.story_id}: {story.name}")
            for scenario in story.scenarios:
                click.echo(f"    - {scenario.scenario_id}: {scenario.name}")


@features.command("stats")
@click.option(
    "--dir",
    "features_dir",
    default=None,
    help="Path to features directory.",
)
@click.option(
    "--tests-dir",
    "-t",
    default="tests",
    help="Path to tests directory.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def features_stats(
    features_dir: str | None,
    tests_dir: str,
    format_type: str | None,
    pretty: bool,
) -> None:
    """Show aggregate statistics for specs and test coverage."""
    from specleft.validator import collect_spec_stats, load_specs_directory

    selected_format = resolve_output_format(format_type)
    config = None
    stats = None
    spec_scenario_ids: set[str] = set()
    resolved_features_dir = resolve_specs_dir(features_dir)

    try:
        config = load_specs_directory(resolved_features_dir)
        stats = collect_spec_stats(config)
        for feature in config.features:
            for story in feature.stories:
                for scenario in story.scenarios:
                    spec_scenario_ids.add(scenario.scenario_id)
    except FileNotFoundError:
        if selected_format == "json":
            error_payload = {
                "status": "error",
                "message": f"Directory not found: {resolved_features_dir}",
            }
            click.echo(json_dumps(error_payload, pretty=pretty))
        else:
            click.secho(
                f"✗ Directory not found: {resolved_features_dir}",
                fg="red",
                err=True,
            )
            print_support_footer()
        sys.exit(1)
    except ValueError as e:
        if "No feature specs found" in str(e):
            if selected_format == "json":
                stats = None
            else:
                click.secho(f"No specs found in {resolved_features_dir}.", fg="yellow")
            stats = None
        else:
            if selected_format == "json":
                error_payload = {
                    "status": "error",
                    "message": f"Unable to load specs: {e}",
                }
                click.echo(json_dumps(error_payload, pretty=pretty))
            else:
                click.secho(f"✗ Unable to load specs: {e}", fg="red", err=True)
                print_support_footer()
            sys.exit(1)
    except Exception as e:
        if selected_format == "json":
            error_payload = {
                "status": "error",
                "message": f"Unexpected error loading specs: {e}",
            }
            click.echo(json_dumps(error_payload, pretty=pretty))
        else:
            click.secho(f"✗ Unexpected error loading specs: {e}", fg="red", err=True)
            print_support_footer()
        sys.exit(1)

    # Gentle nudge for nested structures (table output only)
    if selected_format == "table":
        warn_if_nested_structure(resolved_features_dir)

    test_discovery = discover_pytest_tests(tests_dir)

    if selected_format == "json":
        payload = _build_features_stats_json(
            features_dir=resolved_features_dir,
            tests_dir=tests_dir,
            stats=stats,
            spec_scenario_ids=spec_scenario_ids,
            test_discovery=test_discovery,
        )
        click.echo(json_dumps(payload, pretty=pretty))
        return

    click.echo("")
    click.secho("Test Coverage Stats", fg="cyan", bold=True)
    click.echo("")

    click.secho("Target Directories:", fg="cyan")
    click.echo(f"  Features Directory: {resolved_features_dir}/")
    click.secho(f"  Tests Directory: {tests_dir}/")
    click.echo("")

    click.secho("Pytest Tests:", fg="cyan")
    if test_discovery.error:
        click.secho(f"  Warning: {test_discovery.error}", fg="yellow")
    click.echo(f"  Total pytest tests discovered: {test_discovery.total_tests}")
    click.echo(f"  Tests with @specleft: {test_discovery.specleft_tests}")
    click.echo("")

    click.secho("Specifications:", fg="cyan")
    if stats:
        click.echo(f"  Features: {stats.feature_count}")
        click.echo(f"  Stories: {stats.story_count}")
        click.echo(f"  Scenarios: {stats.scenario_count}")
        click.echo(f"  Steps: {stats.step_count}")
        click.echo(f"  Parameterized scenarios: {stats.parameterized_scenario_count}")
        if stats.tags:
            click.echo(f"  Tags: {', '.join(sorted(stats.tags))}")
    else:
        click.echo("  No specs found.")
    click.echo("")

    click.secho("Coverage:", fg="cyan")
    if stats and stats.scenario_count > 0:
        scenarios_with_tests = spec_scenario_ids.intersection(
            test_discovery.specleft_scenario_ids
        )
        scenarios_without_tests = (
            spec_scenario_ids - test_discovery.specleft_scenario_ids
        )
        coverage_pct = (
            len(scenarios_with_tests) / stats.scenario_count * 100
            if stats.scenario_count > 0
            else 0
        )
        colour = (
            "green" if coverage_pct >= 80 else "yellow" if coverage_pct >= 50 else "red"
        )
        click.echo(f"  Scenarios with tests: {len(scenarios_with_tests)}")
        click.echo(f"  Scenarios without tests: {len(scenarios_without_tests)}")
        click.secho(f"  Coverage: {coverage_pct:.1f}%", fg=colour)

        if scenarios_without_tests:
            click.echo("")
            click.secho("Scenarios without tests:", fg="cyan")
            for scenario_id in sorted(scenarios_without_tests):
                click.echo(f"  - {scenario_id}")
    elif stats:
        click.echo("  No scenarios defined in specs.")
    else:
        click.echo("  Cannot calculate coverage without specs.")
    click.echo("")
    click.echo("To enforce intent coverage in CI, see: https://specleft.dev/enforce")


@features.command("add")
@click.option(
    "--id",
    "feature_id",
    help="Feature ID (optional; defaults to a slug from the title).",
)
@click.option("--title", "title", help="Feature title (required).")
@click.option(
    "--priority",
    "priority",
    type=click.Choice([p.value for p in Priority], case_sensitive=False),
    default="medium",
    show_default=True,
    help="Feature priority.",
)
@click.option("--description", "description", help="Feature description.")
@click.option(
    "--dir",
    "features_dir",
    default=None,
    help="Path to features directory.",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--interactive", is_flag=True, help="Use guided prompts.")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def features_add(
    feature_id: str | None,
    title: str | None,
    priority: str,
    description: str | None,
    features_dir: str | None,
    dry_run: bool,
    format_type: str | None,
    interactive: bool,
    pretty: bool,
) -> None:
    """Create a new feature markdown file."""
    selected_format = resolve_output_format(format_type)
    _ensure_interactive(interactive)

    if interactive:
        title_input = click.prompt("Feature title", type=str).strip()
        title = title_input
        default_feature_id = generate_feature_id(title_input)
        feature_id_input = click.prompt(
            "Feature ID",
            default=default_feature_id,
            show_default=True,
        )
        feature_id = feature_id_input.strip()
        priority = click.prompt(
            "Priority",
            type=click.Choice([p.value for p in Priority], case_sensitive=False),
            default=priority,
            show_default=True,
        )
        description = click.prompt("Description", default="", show_default=False)
        description = description.strip() if description else None

    if not title:
        click.secho(
            "Feature title is required unless --interactive is used.",
            fg="red",
            err=True,
        )
        print_support_footer()
        sys.exit(1)

    assert title is not None

    feature_id = feature_id or generate_feature_id(title)
    if not feature_id:
        click.secho(
            "Feature ID could not be generated from the title.",
            fg="red",
            err=True,
        )
        print_support_footer()
        sys.exit(1)

    try:
        validate_feature_id(feature_id)
    except ValueError as exc:
        payload = {
            "success": False,
            "action": "add",
            "error": str(exc),
        }
        _print_feature_add_result(
            result=payload,
            format_type=selected_format,
            dry_run=dry_run,
            pretty=pretty,
        )
        sys.exit(1)

    resolved_features_dir = resolve_specs_dir(features_dir)
    result = create_feature_file(
        features_dir=resolved_features_dir,
        feature_id=feature_id,
        title=title,
        priority=priority,
        description=description,
        dry_run=dry_run,
    )

    payload = {
        "success": result.success,
        "action": "add",
        "feature_id": feature_id,
        "title": title,
        "priority": priority,
        "file_path": str(result.file_path),
        "dry_run": dry_run,
        "error": result.error,
    }

    if result.success and not dry_run:
        log_feature_event(
            feature_id,
            "feature-created",
            {"title": title, "priority": priority, "description": description},
        )

    _print_feature_add_result(
        result=payload,
        format_type=selected_format,
        dry_run=dry_run,
        pretty=pretty,
    )
    if not result.success:
        sys.exit(1)


@features.command("add-scenario")
@click.option(
    "--feature",
    "feature_id",
    help="Feature ID to append scenario to.",
)
@click.option("--title", "title", help="Scenario title.")
@click.option("--id", "scenario_id", help="Scenario ID (optional).")
@click.option(
    "--step",
    "steps",
    multiple=True,
    help="Scenario step (repeatable).",
)
@click.option(
    "--priority",
    "priority",
    type=click.Choice([p.value for p in Priority], case_sensitive=False),
    help="Scenario priority.",
)
@click.option("--tags", "tags", help="Comma-separated tags.")
@click.option(
    "--dir",
    "features_dir",
    default=None,
    help="Path to features directory.",
)
@click.option(
    "--tests-dir",
    "tests_dir",
    default=None,
    type=click.Path(path_type=Path),
    callback=_normalize_tests_dir,
    help="Directory for generated test files (default: tests).",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--interactive", is_flag=True, help="Use guided prompts.")
@click.option(
    "--add-test",
    "add_test",
    type=click.Choice(["stub", "skeleton"], case_sensitive=False),
    help="Generate a test stub or skeleton.",
)
@click.option(
    "--preview-test",
    is_flag=True,
    help="Print the generated test content.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def features_add_scenario(
    feature_id: str | None,
    title: str | None,
    scenario_id: str | None,
    steps: tuple[str, ...],
    priority: str | None,
    tags: str | None,
    features_dir: str | None,
    tests_dir: Path | None,
    dry_run: bool,
    format_type: str | None,
    interactive: bool,
    add_test: str | None,
    preview_test: bool,
    pretty: bool,
) -> None:
    """Append a scenario to an existing feature file."""
    selected_format = resolve_output_format(format_type)
    _ensure_interactive(interactive)

    if interactive:
        feature_id = click.prompt("Feature ID", type=str).strip()
        title_input = click.prompt("Scenario title", type=str).strip()
        title = title_input
        default_scenario_id = generate_scenario_id(title_input)
        scenario_id_input = click.prompt(
            "Scenario ID",
            default=default_scenario_id,
            show_default=True,
        )
        scenario_id = scenario_id_input.strip() or None
        priority = click.prompt(
            "Priority",
            type=click.Choice([p.value for p in Priority], case_sensitive=False),
            default=priority or "medium",
            show_default=True,
        )
        tags_input = click.prompt("Tags", default="", show_default=False)
        tags = tags_input.strip() or None
        steps_list: list[str] = []
        click.echo("Enter steps (blank line to finish):")
        while True:
            step = click.prompt("Step", default="", show_default=False)
            if not step.strip():
                break
            steps_list.append(step)
        steps = tuple(steps_list)

    if not feature_id or not title:
        click.secho(
            "Feature ID and scenario title are required unless --interactive is used.",
            fg="red",
            err=True,
        )
        print_support_footer()
        sys.exit(1)

    assert title is not None

    try:
        validate_feature_id(feature_id)
    except ValueError as exc:
        payload = {
            "success": False,
            "action": "add_scenario",
            "feature_id": feature_id,
            "error": str(exc),
        }
        _print_scenario_add_result(
            result=payload,
            format_type=selected_format,
            dry_run=dry_run,
            warnings=[],
            pretty=pretty,
        )
        sys.exit(1)

    steps_list = _parse_steps(steps)
    warnings = validate_step_keywords(steps_list) if steps_list else []
    scenario_id = scenario_id or generate_scenario_id(title)

    try:
        validate_scenario_id(scenario_id)
    except ValueError as exc:
        payload = {
            "success": False,
            "action": "add_scenario",
            "feature_id": feature_id,
            "scenario_id": scenario_id,
            "error": str(exc),
        }
        _print_scenario_add_result(
            result=payload,
            format_type=selected_format,
            dry_run=dry_run,
            warnings=warnings,
            pretty=pretty,
        )
        sys.exit(1)

    if add_test and add_test.lower() == "skeleton" and not steps_list:
        payload = {
            "success": False,
            "action": "add_scenario",
            "feature_id": feature_id,
            "scenario_id": scenario_id,
            "error": (
                "No steps found for test skeleton. Add steps to scenario or select "
                "'--add-test stub'"
            ),
        }
        _print_scenario_add_result(
            result=payload,
            format_type=selected_format,
            dry_run=dry_run,
            warnings=warnings,
            pretty=pretty,
        )
        sys.exit(1)

    tags_list = _parse_tags(tags)
    priority_value = _normalize_priority(priority)
    resolved_features_dir = resolve_specs_dir(features_dir)
    result = add_scenario_to_feature(
        features_dir=resolved_features_dir,
        feature_id=feature_id,
        title=title,
        scenario_id=scenario_id,
        priority=priority,
        tags=tags_list,
        steps=steps_list,
        dry_run=dry_run,
    )

    payload = {
        "success": result.success,
        "action": "add_scenario",
        "feature_id": feature_id,
        "scenario_id": scenario_id,
        "title": title,
        "priority": priority_value.value if priority_value else None,
        "file_path": str(result.file_path),
        "steps_count": len(steps_list),
        "dry_run": dry_run,
        "error": result.error,
    }

    if not result.success:
        payload["suggestion"] = (
            f"Run 'specleft features add --id {feature_id} --title "
            f"\"{feature_id.replace('-', ' ').title()}\"' first"
        )
        _print_scenario_add_result(
            result=payload,
            format_type=selected_format,
            dry_run=dry_run,
            warnings=warnings,
            pretty=pretty,
        )
        sys.exit(1)

    if result.success and not dry_run:
        log_feature_event(
            feature_id,
            "scenario-added",
            {
                "scenario_id": scenario_id,
                "title": title,
                "priority": priority_value.value if priority_value else None,
                "tags": tags_list or [],
                "steps": steps_list,
            },
        )

    scenario_spec = _build_scenario_spec(
        scenario_id=scenario_id,
        title=title,
        priority=priority_value,
        tags=tags_list,
        steps=steps_list,
    )

    generated_test = None
    preview_kind: str | None = None
    if preview_test:
        if add_test:
            preview_kind = add_test.lower()
        elif steps_list:
            preview_kind = "skeleton"
        else:
            preview_kind = "stub"

    if preview_kind:
        if preview_kind == "stub":
            generated_test = _build_stub_test_method(feature_id, scenario_spec)
        else:
            generated_test = _build_skeleton_test_method(feature_id, scenario_spec)

    if add_test:
        test_path = _build_feature_test_path(feature_id, tests_dir)
        if not generated_test:
            if add_test.lower() == "stub":
                generated_test = _build_stub_test_method(feature_id, scenario_spec)
            else:
                generated_test = _build_skeleton_test_method(feature_id, scenario_spec)
        header = _build_test_header(add_test.lower())
        created, error = _write_or_append_test(
            test_path=test_path,
            method_content=generated_test,
            header=header,
            scenario_id=scenario_id,
            dry_run=dry_run,
        )
        if not created and error:
            click.secho(f"Warning: {error}", fg="yellow")
    elif selected_format == "table" and not dry_run and not preview_test:
        if click.confirm("Generate test skeleton?", default=True):
            default_tests_dir = tests_dir or Path("tests")
            try:
                selected_tests_dir = _parse_tests_dir(
                    click.prompt(
                        "Test output directory",
                        default=default_tests_dir,
                        type=click.Path(path_type=Path),
                    )
                )
            except click.BadParameter as exc:
                click.secho(str(exc), fg="red", err=True)
                print_support_footer()
                sys.exit(1)
            test_path = _build_feature_test_path(feature_id, selected_tests_dir)
            generated_test = _build_skeleton_test_method(feature_id, scenario_spec)
            header = _build_test_header("skeleton")
            created, error = _write_or_append_test(
                test_path=test_path,
                method_content=generated_test,
                header=header,
                scenario_id=scenario_id,
                dry_run=False,
            )
            if not created and error:
                click.secho(f"Warning: {error}", fg="yellow")

    if preview_test and generated_test:
        if selected_format == "json":
            payload["test_preview"] = generated_test
        else:
            click.echo("\nTest preview:\n")
            click.echo(generated_test)

    _print_scenario_add_result(
        result=payload,
        format_type=selected_format,
        dry_run=dry_run,
        warnings=warnings,
        pretty=pretty,
    )
