# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Planning command for SpecLeft."""

from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click
from slugify import slugify

from specleft.license.status import resolve_license
from specleft.utils.specs_dir import resolve_specs_dir
from specleft.templates.prd_template import (
    PRDTemplate,
    compile_pattern,
    default_template,
    load_template,
)

SUGGESTED_PRD_LOCATIONS = (Path("prd.md"), Path("docs/prd.md"))


def _read_prd(prd_path: Path) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    if not prd_path.exists():
        warnings.append(f"PRD not found at {prd_path}")
        return None, warnings

    try:
        return prd_path.read_text(), warnings
    except OSError as exc:
        warnings.append(f"Unable to read PRD at {prd_path}: {exc}")
        return None, warnings


def _normalize_heading_levels(levels: int | list[int]) -> set[int]:
    if isinstance(levels, int):
        return {levels}
    return set(levels)


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        base = compile_pattern(pattern)
        compiled.append(re.compile(base.pattern, re.IGNORECASE))
    return compiled


def _compile_contains(terms: list[str]) -> list[str]:
    return [term.casefold() for term in terms if term]


def _matches_mode(
    *, pattern_match: bool, contains_match: bool, match_mode: str
) -> bool:
    if match_mode == "patterns":
        return pattern_match
    if match_mode == "contains":
        return contains_match
    if match_mode == "all":
        return pattern_match and contains_match
    return pattern_match or contains_match


def _parse_heading(line: str) -> tuple[int, str] | None:
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return None
    level = len(stripped) - len(stripped.lstrip("#"))
    if level < 1 or level > 6:
        return None
    if len(stripped) <= level or stripped[level] != " ":
        return None
    return level, stripped[level + 1 :].strip()


def _analyze_prd(
    prd_content: str,
    template: PRDTemplate,
) -> dict[str, Any]:
    feature_levels = _normalize_heading_levels(template.features.heading_level)
    scenario_levels = set(template.scenarios.heading_level)
    feature_patterns = _compile_patterns(template.features.patterns)
    scenario_patterns = _compile_patterns(template.scenarios.patterns)
    feature_contains = _compile_contains(template.features.contains)
    scenario_contains = _compile_contains(template.scenarios.contains)
    exclude = {value.casefold() for value in template.features.exclude}

    headings: list[dict[str, object]] = []
    current_feature: str | None = None
    orphan_blocks = 0
    in_orphan_block = False

    for line in prd_content.splitlines():
        heading = _parse_heading(line)
        if heading:
            level, text = heading
            classification = "other"
            parent_feature = current_feature
            if text.casefold() in exclude:
                classification = "excluded"
            elif level in feature_levels:
                pattern_match = any(pattern.match(text) for pattern in feature_patterns)
                contains_match = any(
                    term in text.casefold() for term in feature_contains
                )
                if _matches_mode(
                    pattern_match=pattern_match,
                    contains_match=contains_match,
                    match_mode=template.features.match_mode,
                ):
                    classification = "feature"
                    current_feature = text
                    parent_feature = current_feature
                else:
                    classification = "ambiguous"
            elif level in scenario_levels:
                pattern_match = any(
                    pattern.match(text) for pattern in scenario_patterns
                )
                contains_match = any(
                    term in text.casefold() for term in scenario_contains
                )
                if _matches_mode(
                    pattern_match=pattern_match,
                    contains_match=contains_match,
                    match_mode=template.scenarios.match_mode,
                ):
                    classification = "scenario"

            headings.append(
                {
                    "level": level,
                    "text": text,
                    "classification": classification,
                    "parent_feature": parent_feature,
                }
            )
            in_orphan_block = False
            continue

        if current_feature is None and line.strip():
            if not in_orphan_block:
                orphan_blocks += 1
                in_orphan_block = True
        else:
            in_orphan_block = False

    summary = {
        "total_headings": len(headings),
        "features": sum(1 for item in headings if item["classification"] == "feature"),
        "scenarios": sum(
            1 for item in headings if item["classification"] == "scenario"
        ),
        "excluded": sum(1 for item in headings if item["classification"] == "excluded"),
        "ambiguous": sum(
            1 for item in headings if item["classification"] == "ambiguous"
        ),
        "orphan_content_blocks": orphan_blocks,
    }

    suggestions: list[str] = []
    if summary["features"] == 0:
        suggestions.append(
            "No feature headings detected; add feature headings or adjust the template."
        )
    if summary["ambiguous"]:
        suggestions.append(
            "Some headings look like features but did not match; update templates or rename headings."
        )
    if orphan_blocks:
        suggestions.append(
            "Orphan content detected; move content under a feature heading."
        )

    return {
        "headings": headings,
        "summary": summary,
        "suggestions": suggestions,
    }


def _extract_feature_titles(
    prd_content: str,
    template: PRDTemplate | None = None,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    template = template or default_template()
    lines = [line.rstrip() for line in prd_content.splitlines()]
    feature_levels = _normalize_heading_levels(template.features.heading_level)
    feature_patterns = _compile_patterns(template.features.patterns)
    feature_contains = _compile_contains(template.features.contains)
    exclude = {value.casefold() for value in template.features.exclude}

    h1_titles = [
        text
        for line in lines
        if (heading := _parse_heading(line)) and heading[0] == 1
        for text in [heading[1]]
        if text
    ]
    feature_titles: list[str] = []
    for line in lines:
        heading = _parse_heading(line)
        if not heading:
            continue
        level, text = heading
        if level not in feature_levels:
            continue
        if text.casefold() in exclude:
            continue
        pattern_match = any(pattern.match(text) for pattern in feature_patterns)
        contains_match = any(term in text.casefold() for term in feature_contains)
        matched = _matches_mode(
            pattern_match=pattern_match,
            contains_match=contains_match,
            match_mode=template.features.match_mode,
        )
        if matched and text:
            feature_titles.append(text)

    if feature_titles:
        return feature_titles, warnings

    if len(h1_titles) == 1 and h1_titles[0]:
        warnings.append("No secondary headings found; using top-level title.")
        return [h1_titles[0]], warnings

    warnings.append("No usable headings found; creating .specleft/specs/prd.md.")
    return [], warnings


def _extract_prd_scenarios(
    prd_content: str,
    *,
    template: PRDTemplate | None = None,
    require_step_keywords: bool = True,
) -> tuple[
    dict[str, list[dict[str, object]]],
    list[dict[str, object]],
    dict[str, str],
    list[str],
]:
    warnings: list[str] = []
    scenarios_by_feature: dict[str, list[dict[str, object]]] = {}
    orphan_scenarios: list[dict[str, object]] = []
    feature_priorities: dict[str, str] = {}

    template = template or default_template()
    feature_levels = _normalize_heading_levels(template.features.heading_level)
    scenario_levels = set(template.scenarios.heading_level)
    feature_patterns = _compile_patterns(template.features.patterns)
    scenario_patterns = _compile_patterns(template.scenarios.patterns)
    priority_patterns = _compile_patterns(template.priorities.patterns)
    feature_contains = _compile_contains(template.features.contains)
    scenario_contains = _compile_contains(template.scenarios.contains)
    exclude = {value.casefold() for value in template.features.exclude}
    step_keywords = tuple(
        keyword.casefold() for keyword in template.scenarios.step_keywords
    )
    priority_mapping = {
        key.casefold(): value for key, value in template.priorities.mapping.items()
    }

    def is_feature_heading(level: int, text: str) -> bool:
        if level not in feature_levels:
            return False
        if text.casefold() in exclude:
            return False
        pattern_match = any(pattern.match(text) for pattern in feature_patterns)
        contains_match = any(term in text.casefold() for term in feature_contains)
        return _matches_mode(
            pattern_match=pattern_match,
            contains_match=contains_match,
            match_mode=template.features.match_mode,
        )

    def extract_scenario_title(level: int, text: str) -> str | None:
        if level not in scenario_levels:
            return None
        contains_match = any(term in text.casefold() for term in scenario_contains)
        if template.scenarios.match_mode == "contains" and not contains_match:
            return None
        if template.scenarios.match_mode == "all" and not contains_match:
            return None
        for pattern in scenario_patterns:
            match = pattern.match(text)
            if not match:
                continue
            title = match.groupdict().get("title", "").strip()
            return title or "Scenario"
        if template.scenarios.match_mode in {"patterns", "all"}:
            return None
        if contains_match:
            return "Scenario"
        return None

    def is_step_line(text: str) -> bool:
        lowered = text.casefold()
        return lowered.startswith(tuple(f"{keyword} " for keyword in step_keywords))

    def normalize_step(text: str) -> str | None:
        stripped = text.strip()
        if not stripped:
            return None
        if require_step_keywords and not is_step_line(stripped):
            return None
        return stripped

    def extract_steps(lines: list[str]) -> list[str]:
        steps: list[str] = []
        for raw in lines:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith(("-", "*", "•")):
                candidate = stripped[1:].strip()
            else:
                candidate = stripped
            normalized = normalize_step(candidate)
            if normalized:
                steps.append(normalized)
        return steps

    def extract_priority(line: str) -> str | None:
        stripped = line.strip()
        if stripped.startswith(("-", "*", "•")):
            stripped = stripped[1:].strip()
        for pattern in priority_patterns:
            match = pattern.match(stripped)
            if not match:
                continue
            value = match.groupdict().get("value", "").strip()
            if not value:
                return None
            mapped = priority_mapping.get(value.casefold())
            return mapped or value
        return None

    lines = prd_content.splitlines()
    current_feature: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        heading = _parse_heading(line)
        if heading:
            level, text = heading
            if is_feature_heading(level, text):
                current_feature = text
            scenario_title = extract_scenario_title(level, text)
            if scenario_title:
                block_lines: list[str] = []
                index += 1
                while index < len(lines):
                    next_heading = _parse_heading(lines[index])
                    if next_heading:
                        break
                    block_lines.append(lines[index])
                    index += 1
                steps = extract_steps(block_lines)
                scenario_priority = None
                for block_line in block_lines:
                    scenario_priority = extract_priority(block_line)
                    if scenario_priority:
                        break
                scenario: dict[str, object] = {
                    "title": scenario_title,
                    "steps": steps,
                }
                if scenario_priority:
                    scenario["priority"] = scenario_priority
                if current_feature is None:
                    warnings.append(
                        f" Scenario found without feature - '{scenario_title}'. "
                    )
                    orphan_scenarios.append(scenario)
                else:
                    scenarios_by_feature.setdefault(current_feature, []).append(
                        scenario
                    )
                continue
        if current_feature is not None and current_feature not in feature_priorities:
            priority_value = extract_priority(line)
            if priority_value:
                feature_priorities[current_feature] = priority_value
        index += 1

    return scenarios_by_feature, orphan_scenarios, feature_priorities, warnings


def _render_scenarios(scenarios: list[dict[str, object]]) -> str:
    blocks: list[str] = []
    for scenario in scenarios:
        title = str(scenario.get("title", "Scenario"))
        priority = scenario.get("priority", "medium")
        steps_value = scenario.get("steps")
        steps: list[str] = []
        if isinstance(steps_value, list):
            steps = [str(step) for step in steps_value]
        step_lines = [f"- {step}" for step in steps]
        block = "\n".join(
            [
                f"### Scenario: {title}",
                f"priority: {priority}" if priority else "",
                *step_lines,
            ]
        ).strip()
        blocks.append(block)
    return "\n\n".join(blocks).strip()


def _feature_template(
    title: str,
    scenarios: list[dict[str, object]] | None = None,
    priority: str | None = None,
) -> str:
    scenario_block = None
    if scenarios:
        rendered = _render_scenarios(scenarios)
        if rendered:
            scenario_block = rendered
    default_block = textwrap.dedent("""
        ### Scenario: Example
        priority: medium

        - Given a precondition
        - When an action occurs
        - Then the expected result
        """).strip()
    block = scenario_block or default_block
    return "\n".join(
        [
            f"# {title}",
            "",
            f"priority: {priority}" if priority else "",
            "" if priority else "",
            "## Scenarios",
            "",
            block,
            "",
        ]
    )


def _feature_path(features_dir: Path, title: str) -> Path:
    slug = "prd" if title == "PRD" else slugify(title)
    return features_dir / f"{slug}.md"


def _feature_paths(features_dir: Path, titles: list[str]) -> list[Path]:
    return [_feature_path(features_dir, title) for title in titles]


def _needs_skip(path: Path) -> bool:
    return path.exists()


def _apply_plan(
    titles: list[str],
    *,
    features_dir: Path,
    dry_run: bool,
    scenarios_by_feature: dict[str, list[dict[str, object]]] | None = None,
    feature_priorities: dict[str, str] | None = None,
) -> tuple[list[Path], list[Path]]:
    created: list[Path] = []
    skipped: list[Path] = []
    for title in titles:
        path = _feature_path(features_dir, title)
        if _needs_skip(path):
            skipped.append(path)
            continue
        if dry_run:
            created.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        scenarios = None
        if scenarios_by_feature:
            scenarios = scenarios_by_feature.get(title)
        priority = None
        if feature_priorities:
            priority = feature_priorities.get(title)
        path.write_text(
            _feature_template(title, scenarios=scenarios, priority=priority)
        )
        created.append(path)
    return created, skipped


def _build_plan_payload(
    *,
    prd_path: Path,
    dry_run: bool,
    feature_count: int,
    created: list[Path],
    skipped: list[Path],
    warnings: list[str],
    orphan_scenarios: list[dict[str, object]] | None = None,
    template_info: dict[str, str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "timestamp": datetime.now().isoformat(),
        "status": "warning" if warnings else "ok",
        "prd_path": str(prd_path),
        "dry_run": dry_run,
        "feature_count": feature_count,
        "warnings": warnings,
        "suggested_locations": [str(path) for path in SUGGESTED_PRD_LOCATIONS],
        "skipped": [str(path) for path in skipped],
    }
    payload["orphan_scenarios"] = orphan_scenarios or []
    if template_info:
        payload["template"] = template_info
    if dry_run:
        payload["would_create"] = [str(path) for path in created]
    else:
        payload["created"] = [str(path) for path in created]
    return payload


def _print_warning(message: str) -> None:
    click.secho(f"Warning: {message}", fg="yellow")


def _print_plan_summary(*, feature_count: int, dry_run: bool) -> None:
    click.echo("Planning feature specs...")
    if dry_run:
        click.echo("Dry run: no files will be created.")
    click.echo(f"Features planned: {feature_count}")


def _print_plan_results(
    *,
    created: list[Path],
    skipped: list[Path],
    dry_run: bool,
) -> None:
    if dry_run:
        click.echo("Would create:")
    else:
        click.echo("Created:")
    for path in created:
        click.echo(f"  - {path}")

    if skipped:
        click.echo("Skipped existing:")
        for path in skipped:
            click.echo(f"  - {path}")


def _print_analyze_summary(summary: dict[str, int]) -> None:
    click.echo("Analyzing PRD structure...")
    click.echo(f"Headings total: {summary['total_headings']}")
    click.echo(f"Features: {summary['features']}")
    click.echo(f"Scenarios: {summary['scenarios']}")
    click.echo(f"Excluded: {summary['excluded']}")
    click.echo(f"Ambiguous: {summary['ambiguous']}")
    click.echo(f"Orphan content blocks: {summary['orphan_content_blocks']}")


@click.command(
    "plan",
    epilog=(
        "Feature files may include optional metadata (confidence, assumptions, tags, "
        "owner, etc). See docs/feature-template.md for details."
    ),
)
@click.option(
    "--from",
    "prd_path",
    default="prd.md",
    help="Path to the PRD file.",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
@click.option("--analyze", is_flag=True, help="Analyze PRD without writing files.")
@click.option(
    "--template",
    "template_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to a PRD template YAML file.",
)
def plan(
    prd_path: str,
    format_type: str,
    dry_run: bool,
    analyze: bool,
    template_path: Path | None,
) -> None:
    """Generate feature specs from a PRD."""
    prd_file = Path(prd_path)
    template = default_template()
    template_info: dict[str, str] | None = None

    default_template_path = Path(".specleft/templates/prd-template.yml")
    if template_path is not None:
        template = load_template(template_path)
        template_info = {
            "path": str(template_path),
            "version": template.version,
        }
    elif default_template_path.exists():
        template = load_template(default_template_path)
        template_path = default_template_path
        template_info = {
            "path": str(default_template_path),
            "version": template.version,
        }

    if template_path is not None and format_type != "json":
        click.echo(f"Using template: {template_path}")
        click.echo("")
    prd_content, warnings = _read_prd(prd_file)
    if prd_content is None:
        if format_type == "json":
            payload = _build_plan_payload(
                prd_path=prd_file,
                dry_run=dry_run,
                feature_count=0,
                created=[],
                skipped=[],
                warnings=warnings,
                template_info=template_info,
            )
            click.echo(json.dumps(payload, indent=2))
            return

        for warning in warnings:
            _print_warning(warning)
        click.echo("Expected locations:")
        for path in SUGGESTED_PRD_LOCATIONS:
            click.echo(f"  - {path}")
        click.echo("Nothing to plan yet.")
        return

    if analyze:
        analysis = _analyze_prd(prd_content, template)
        summary = cast(dict[str, int], analysis["summary"])
        suggestions = cast(list[str], analysis["suggestions"])
        if format_type == "json":
            payload = {
                "timestamp": datetime.now().isoformat(),
                "status": "warning" if warnings else "ok",
                "prd_path": str(prd_file),
                "warnings": warnings,
                **analysis,
            }
            if template_info:
                payload["template"] = template_info
            click.echo(json.dumps(payload, indent=2))
            return

        for warning in warnings:
            _print_warning(warning)
        _print_analyze_summary(summary)
        if suggestions:
            click.echo("Suggestions:")
            for suggestion in suggestions:
                click.echo(f"  - {suggestion}")
        return

    titles, title_warnings = _extract_feature_titles(prd_content, template)
    warnings.extend(title_warnings)
    (
        scenarios_by_feature,
        orphan_scenarios,
        feature_priorities,
        scenario_warnings,
    ) = _extract_prd_scenarios(
        prd_content,
        template=template,
        require_step_keywords=True,
    )
    warnings.extend(scenario_warnings)
    features_dir = resolve_specs_dir(None)

    if not titles:
        titles = ["PRD"]

    created, skipped = _apply_plan(
        titles,
        features_dir=features_dir,
        dry_run=dry_run,
        scenarios_by_feature=scenarios_by_feature,
        feature_priorities=feature_priorities,
    )
    feature_count = len(titles)

    if format_type == "json":
        payload = _build_plan_payload(
            prd_path=prd_file,
            dry_run=dry_run,
            feature_count=feature_count,
            created=created,
            skipped=skipped,
            warnings=warnings,
            orphan_scenarios=orphan_scenarios,
            template_info=template_info,
        )
        click.echo(json.dumps(payload, indent=2))
        return

    for warning in warnings:
        _print_warning(warning)
    _print_plan_summary(feature_count=feature_count, dry_run=dry_run)
    _print_plan_results(created=created, skipped=skipped, dry_run=dry_run)

    license_validation = resolve_license()
    if not license_validation.valid:
        click.echo("")
        click.echo("Notice: Enforcement capabilities require a commercial license.")
        click.echo("")
        click.echo("A valid license key is not registered.")
        click.echo("Obtain a license:")
        click.echo("  https://specleft.dev/enforce")
