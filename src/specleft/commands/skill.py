# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Skill file lifecycle commands."""

from __future__ import annotations

import sys
from typing import cast

import click

from specleft.commands.output import json_dumps, resolve_output_format
from specleft.utils.skill_integrity import (
    INTEGRITY_MODIFIED,
    INTEGRITY_OUTDATED,
    sync_skill_files,
    verify_skill_integrity,
)


@click.group("skill")
def skill_group() -> None:
    """Manage SpecLeft skill files."""


def _print_integrity_table(payload: dict[str, object]) -> None:
    integrity = str(payload.get("integrity"))
    marker = "✓" if integrity == "pass" else ("⚠" if integrity == "outdated" else "✗")
    click.echo(f"{marker} Skill integrity: {integrity}")
    click.echo(f"Skill file: {payload.get('skill_file')}")
    click.echo(f"Checksum file: {payload.get('checksum_file')}")
    click.echo(f"Expected hash: {payload.get('expected_hash')}")
    click.echo(f"Actual hash: {payload.get('actual_hash')}")
    click.echo(f"Template hash: {payload.get('current_template_hash')}")
    click.echo(f"Commands simple: {payload.get('commands_simple')}")
    message = payload.get("message")
    if message:
        click.echo(f"Message: {message}")


@skill_group.command("verify")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def skill_verify(format_type: str | None, pretty: bool) -> None:
    """Verify SKILL.md integrity and freshness."""
    selected_format = resolve_output_format(format_type)
    result = verify_skill_integrity().to_payload()
    if selected_format == "json":
        click.echo(json_dumps(result, pretty=pretty))
    else:
        _print_integrity_table(result)

    integrity = str(result["integrity"])
    if integrity == INTEGRITY_MODIFIED:
        sys.exit(1)
    if integrity == INTEGRITY_OUTDATED:
        sys.exit(0)
    sys.exit(0)


def _print_sync_table(payload: dict[str, object]) -> None:
    created = cast(list[str], payload.get("created", []))
    updated = cast(list[str], payload.get("updated", []))
    skipped = cast(list[str], payload.get("skipped", []))
    warnings = cast(list[str], payload.get("warnings", []))
    click.echo("Skill sync complete.")
    for entry in created:
        click.echo(f"✓ Created {entry}")
    for entry in updated:
        click.echo(f"✓ Updated {entry}")
    for entry in skipped:
        click.echo(f"• Skipped {entry}")
    for warning in warnings:
        click.secho(str(warning), fg="yellow")
    click.echo(f"Skill file hash: {payload.get('skill_file_hash')}")


@skill_group.command("update")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def skill_update(format_type: str | None, pretty: bool) -> None:
    """Regenerate SKILL.md and checksum from the current SpecLeft version."""
    selected_format = resolve_output_format(format_type)
    payload = sync_skill_files(overwrite_existing=True).to_payload()
    if selected_format == "json":
        click.echo(json_dumps(payload, pretty=pretty))
    else:
        _print_sync_table(payload)
    sys.exit(0)
