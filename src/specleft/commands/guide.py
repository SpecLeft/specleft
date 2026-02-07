# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Workflow guide command."""

from __future__ import annotations

import json

import click

from specleft.commands.guide_content import (
    COMMAND_ORDER,
    COMMANDS,
    QUICK_START,
    TASK_MAPPINGS,
)
from specleft.commands.guide_content import get_guide_json


def _format_table() -> str:
    lines: list[str] = [
        "SpecLeft Workflow Guide",
        "━" * 71,
        "",
        "When to use each workflow:",
        "",
        "  Task                        Workflow        Action",
        "  " + "─" * 63,
    ]

    for mapping in TASK_MAPPINGS:
        task = mapping["task"].ljust(27)
        workflow = mapping["workflow"].ljust(15)
        action = mapping["action"]
        lines.append(f"  {task}{workflow}{action}")

    lines.extend(
        [
            "",
            "Useful commands:",
            "",
        ]
    )

    for key in COMMAND_ORDER:
        command_info = COMMANDS.get(key)
        if not command_info:
            continue
        usage = command_info["usage"].ljust(38)
        description = command_info["description"]
        lines.append(f"  {usage}{description}")

    lines.extend(
        [
            "",
            "Quick start:",
            "",
        ]
    )

    for index, quick_start in enumerate(QUICK_START, start=1):
        lines.append(f"  {index}. {quick_start}")

    lines.extend(
        [
            "",
            "All commands support --format json for programmatic use.",
            "",
            "━" * 71,
        ]
    )

    return "\n".join(lines)


@click.command("guide")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
def guide(output_format: str) -> None:
    """Display SpecLeft workflow guide."""
    if output_format == "json":
        click.echo(json.dumps(get_guide_json(), indent=2))
        return

    click.echo(_format_table())
