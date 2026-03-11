# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Discovery command group."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from specleft.commands.output import json_dumps, resolve_output_format
from specleft.discovery.grouping import group_items
from specleft.discovery.models import (
    DEFAULT_DISCOVERY_OUTPUT_DIR,
    DiscoveryReport,
    DraftFeature,
    ItemKind,
    SupportedLanguage,
)
from specleft.discovery.pipeline import build_default_pipeline
from specleft.discovery.spec_writer import generate_draft_specs
from specleft.discovery.traceability import infer_traceability
from specleft.schema import SpecsConfig
from specleft.utils.specs_dir import (
    DEFAULT_SPECS_DIR,
    FALLBACK_SPECS_DIR,
)


@dataclass(frozen=True)
class _DiscoverSummary:
    features: list[DraftFeature]
    written_paths: list[Path]
    errors: list[str]
    output_dir: Path
    report: DiscoveryReport


@click.group(
    "discover",
    invoke_without_command=True,
    context_settings={"allow_extra_args": True},
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--dry-run", is_flag=True, help="Preview without writing any files.")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Override output dir (default: .specleft/specs/_discovered/).",
)
@click.option(
    "--language",
    "languages",
    type=click.Choice(["python", "typescript"], case_sensitive=False),
    multiple=True,
    help="Limit discovery to a language (repeatable).",
)
@click.option(
    "--specs-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Existing specs dir for traceability matching.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
@click.pass_context
def discover(
    ctx: click.Context,
    format_type: str | None,
    dry_run: bool,
    output_dir: Path | None,
    languages: tuple[str, ...],
    specs_dir: Path | None,
    pretty: bool,
) -> None:
    """Run discovery and generate draft specs."""
    if ctx.invoked_subcommand is not None:
        return

    project_root = _parse_project_root_arg(ctx.args)
    root = _resolve_project_root(project_root)
    selected_format = resolve_output_format(format_type)
    language_filter = _resolve_language_filter(languages)
    resolved_output_dir = _resolve_output_dir(root, output_dir)
    resolved_specs_dir = _resolve_specs_dir(root, specs_dir)

    summary = _run_discovery(
        root=root,
        output_dir=resolved_output_dir,
        specs_dir=resolved_specs_dir,
        dry_run=dry_run,
        language_filter=language_filter,
    )

    if selected_format == "json":
        payload = _build_discover_json(summary, dry_run=dry_run, root=root)
        click.echo(json_dumps(payload, pretty=pretty))
        return

    _print_discover_table(summary, dry_run=dry_run, root=root)


@discover.command("promote")
@click.argument("feature_ids", nargs=-1)
@click.option("--all", "promote_all", is_flag=True, help="Promote all draft files.")
@click.option(
    "--specs-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Destination specs dir (default: resolved via resolve_specs_dir()).",
)
@click.option("--overwrite", is_flag=True, help="Replace existing destination files.")
@click.option("--dry-run", is_flag=True, help="Preview without writing files.")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def discover_promote(
    feature_ids: tuple[str, ...],
    promote_all: bool,
    specs_dir: Path | None,
    overwrite: bool,
    dry_run: bool,
    format_type: str | None,
    pretty: bool,
) -> None:
    """Promote draft specs into the active specs directory."""
    if not promote_all and not feature_ids:
        click.secho("Use --all or provide one or more FEATURE_ID values.", fg="red")
        sys.exit(1)

    root = Path.cwd().resolve()
    source_dir = _resolve_output_dir(root, None)
    destination_dir = _resolve_specs_dir(root, specs_dir)
    selected_format = resolve_output_format(format_type)

    payload = _promote_specs(
        source_dir=source_dir,
        destination_dir=destination_dir,
        feature_ids=feature_ids,
        promote_all=promote_all,
        overwrite=overwrite,
        dry_run=dry_run,
        root=root,
    )

    if selected_format == "json":
        click.echo(json_dumps(payload, pretty=pretty))
        return
    _print_promote_table(payload)


def _resolve_project_root(project_root: Path | None) -> Path:
    candidate = project_root if project_root is not None else Path(".")
    return candidate.resolve()


def _parse_project_root_arg(args: list[str]) -> Path | None:
    if not args:
        return None
    if len(args) > 1:
        raise click.UsageError("Too many arguments. Expected at most one PROJECT_ROOT.")
    return Path(args[0])


def _resolve_output_dir(root: Path, output_dir: Path | None) -> Path:
    candidate = output_dir if output_dir is not None else DEFAULT_DISCOVERY_OUTPUT_DIR
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


def _resolve_specs_dir(root: Path, specs_dir: Path | None) -> Path:
    if specs_dir is not None:
        if specs_dir.is_absolute():
            return specs_dir
        return (root / specs_dir).resolve()

    preferred = root / DEFAULT_SPECS_DIR
    if preferred.exists():
        return preferred

    fallback = root / FALLBACK_SPECS_DIR
    if fallback.exists():
        return fallback
    return preferred


def _resolve_language_filter(raw: tuple[str, ...]) -> list[SupportedLanguage] | None:
    if not raw:
        return None

    resolved: list[SupportedLanguage] = []
    for language in raw:
        normalized = language.strip().lower()
        if normalized == "python":
            resolved.append(SupportedLanguage.PYTHON)
            continue

        resolved.append(SupportedLanguage.TYPESCRIPT)
        resolved.append(SupportedLanguage.JAVASCRIPT)

    deduped: list[SupportedLanguage] = []
    seen: set[SupportedLanguage] = set()
    for language in resolved:
        if language in seen:
            continue
        seen.add(language)
        deduped.append(language)
    return deduped


def _run_discovery(
    *,
    root: Path,
    output_dir: Path,
    specs_dir: Path,
    dry_run: bool,
    language_filter: list[SupportedLanguage] | None,
) -> _DiscoverSummary:
    pipeline = build_default_pipeline(root, languages=language_filter)
    report = pipeline.run()

    draft_features = sorted(
        group_items(report.all_items),
        key=lambda feature: (feature.feature_id, feature.name),
    )

    specs_config, spec_errors = _load_specs_config(specs_dir)
    traceability_links = infer_traceability(report.all_items, specs_config)
    written_paths = generate_draft_specs(
        draft_features,
        output_dir,
        dry_run=dry_run,
        traceability_links=traceability_links,
    )

    errors = list(report.errors)
    errors.extend(spec_errors)
    return _DiscoverSummary(
        features=draft_features,
        written_paths=written_paths,
        errors=errors,
        output_dir=output_dir,
        report=report,
    )


def _load_specs_config(specs_dir: Path) -> tuple[SpecsConfig, list[str]]:
    if not specs_dir.exists():
        return SpecsConfig(features=[]), []

    try:
        return SpecsConfig.from_directory(specs_dir), []
    except Exception as exc:
        return SpecsConfig(features=[]), [f"Unable to parse specs: {exc}"]


def _build_discover_json(
    summary: _DiscoverSummary,
    *,
    dry_run: bool,
    root: Path,
) -> dict[str, Any]:
    feature_rows = _feature_rows(summary.features, summary.output_dir, root)
    return {
        "features": feature_rows,
        "total_features": len(summary.features),
        "total_scenarios": sum(len(feature.scenarios) for feature in summary.features),
        "output_dir": _display_path(summary.output_dir, root),
        "dry_run": dry_run,
        "written": [_display_path(path, root) for path in summary.written_paths],
        "errors": summary.errors,
    }


def _feature_rows(
    features: list[DraftFeature], output_dir: Path, root: Path
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in features:
        path = output_dir / f"{feature.feature_id}.md"
        rows.append(
            {
                "feature_id": feature.feature_id,
                "name": feature.name,
                "scenario_count": len(feature.scenarios),
                "output_file": _display_path(path, root),
                "confidence": round(feature.confidence, 2),
            }
        )
    return rows


def _print_discover_table(
    summary: _DiscoverSummary, *, dry_run: bool, root: Path
) -> None:
    report = summary.report
    item_counts = _item_kind_counts(report)
    framework_summary = _framework_summary(report)
    language_test_counts = _language_test_counts(report)

    click.echo("Scanning project...")
    if report.languages_detected:
        for language in report.languages_detected:
            framework = framework_summary.get(language.value, "unknown")
            test_count = language_test_counts.get(language, 0)
            click.echo(
                f"  ✓ {language.value.title()} ({framework}) — {test_count} test functions"
            )
    else:
        click.echo("  ✓ No supported languages detected")

    click.echo(f"  ✓ API routes        — {item_counts['api_route']} routes")
    click.echo(f"  ✓ Docstrings        — {item_counts['docstring']} items")
    click.echo(f"  ✓ Git history       — {item_counts['git_commit']} commits")
    click.echo("")
    click.echo("Generating draft specs...")
    click.echo("")

    rows = _feature_rows(summary.features, summary.output_dir, root)
    if rows:
        click.echo("  Feature                  Scenarios  Written to")
        click.echo(
            "  ───────────────────────  ─────────  ─────────────────────────────"
        )
        for row in rows:
            click.echo(
                f"  {row['feature_id']:<23}  {row['scenario_count']:<9}  {row['output_file']}"
            )
        click.echo("")
    else:
        click.echo("  No draft features discovered.")
        click.echo("")

    scenario_total = sum(len(feature.scenarios) for feature in summary.features)
    action = "would be written to" if dry_run else "written to"
    click.echo(
        f"  {len(summary.features)} features, {scenario_total} scenarios {action} "
        f"{_display_path(summary.output_dir, root)}"
    )
    click.echo("  Review drafts, then promote with: specleft discover promote")
    if summary.errors:
        click.echo("")
        click.echo("Errors:")
        for error in summary.errors:
            click.echo(f"  - {error}")


def _item_kind_counts(report: DiscoveryReport) -> dict[str, int]:
    return {
        "test_function": len(report.items_by_kind.get(ItemKind.TEST_FUNCTION, [])),
        "api_route": len(report.items_by_kind.get(ItemKind.API_ROUTE, [])),
        "docstring": len(report.items_by_kind.get(ItemKind.DOCSTRING, [])),
        "git_commit": len(report.items_by_kind.get(ItemKind.GIT_COMMIT, [])),
    }


def _framework_summary(report: DiscoveryReport) -> dict[str, str]:
    frameworks: dict[str, set[str]] = {}
    for item in report.items_by_kind.get(ItemKind.TEST_FUNCTION, []):
        if item.language is None:
            continue
        framework = str(item.metadata.get("framework", "unknown")).lower()
        frameworks.setdefault(item.language.value, set()).add(framework)

    summarized: dict[str, str] = {}
    for language, values in frameworks.items():
        usable = sorted(value for value in values if value != "unknown")
        summarized[language] = ", ".join(usable) if usable else "unknown"
    return summarized


def _language_test_counts(report: DiscoveryReport) -> dict[SupportedLanguage, int]:
    counts: dict[SupportedLanguage, int] = {}
    for item in report.items_by_kind.get(ItemKind.TEST_FUNCTION, []):
        if item.language is None:
            continue
        counts[item.language] = counts.get(item.language, 0) + 1
    return counts


def _promote_specs(
    *,
    source_dir: Path,
    destination_dir: Path,
    feature_ids: tuple[str, ...],
    promote_all: bool,
    overwrite: bool,
    dry_run: bool,
    root: Path,
) -> dict[str, Any]:
    sources = _source_files(source_dir, feature_ids, promote_all)
    promoted: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []

    if not dry_run:
        destination_dir.mkdir(parents=True, exist_ok=True)

    for source in sources:
        if not source.exists():
            missing.append(_display_path(source, root))
            continue

        destination = destination_dir / source.name
        destination_display = _display_path(destination, root)
        if destination.exists() and not overwrite:
            skipped.append(destination_display)
            continue

        if not dry_run:
            shutil.copy2(source, destination)
        promoted.append(destination_display)

    errors: list[str] = []
    for missing_path in missing:
        errors.append(f"Draft file not found: {missing_path}")

    return {
        "source_dir": _display_path(source_dir, root),
        "specs_dir": _display_path(destination_dir, root),
        "dry_run": dry_run,
        "overwrite": overwrite,
        "promoted": promoted,
        "skipped": skipped,
        "missing": missing,
        "errors": errors,
    }


def _source_files(
    source_dir: Path,
    feature_ids: tuple[str, ...],
    promote_all: bool,
) -> list[Path]:
    if promote_all:
        return sorted(source_dir.glob("*.md"))

    deduped = sorted(
        {feature_id.strip() for feature_id in feature_ids if feature_id.strip()}
    )
    return [source_dir / f"{feature_id}.md" for feature_id in deduped]


def _print_promote_table(payload: dict[str, Any]) -> None:
    click.echo(f"Promoting draft specs from {payload['source_dir']}")
    click.echo(f"Destination: {payload['specs_dir']}")
    click.echo("")

    promoted: list[str] = payload["promoted"]
    skipped: list[str] = payload["skipped"]
    missing: list[str] = payload["missing"]

    if promoted:
        click.echo("Promoted:")
        for path in promoted:
            click.echo(f"  ✓ {path}")
    else:
        click.echo("Promoted: none")

    if skipped:
        click.echo("Skipped (already exists):")
        for path in skipped:
            click.echo(f"  - {path}")

    if missing:
        click.echo("Missing:")
        for path in missing:
            click.echo(f"  - {path}")

    click.echo("")
    click.echo(
        f"Summary: {len(promoted)} promoted, {len(skipped)} skipped, "
        f"{len(missing)} missing"
    )


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()
