# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Workflow guide command."""

from __future__ import annotations

import click

from specleft.commands.guide_content import (
    COMMAND_ORDER,
    COMMANDS,
    QUICK_START,
    TASK_MAPPINGS,
)
from specleft.commands.guide_content import get_guide_json
from specleft.commands.output import json_dumps, resolve_output_format


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
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def guide(output_format: str | None, pretty: bool) -> None:
    """Display SpecLeft workflow guide."""
    selected_format = resolve_output_format(output_format)
    if selected_format == "json":
        click.echo(json_dumps(get_guide_json(), pretty=pretty))
        return

    click.echo(_format_table())
