# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""License management commands."""

from __future__ import annotations

from pathlib import Path

import click
from click.core import ParameterSource

from specleft.license.status import DEFAULT_LICENSE_PATH, resolve_license


@click.group("license")
def license_group() -> None:
    """License management commands."""


@license_group.command("status")
@click.option(
    "--file",
    "file_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_LICENSE_PATH,
    show_default=True,
    help="License policy file to check.",
)
@click.pass_context
def license_status(ctx: click.Context, file_path: Path) -> None:
    """Show license status information."""
    source = ctx.get_parameter_source("file_path")
    preferred: Path | None = None
    if source != ParameterSource.DEFAULT:
        preferred = file_path
    else:
        preferred = None if file_path == DEFAULT_LICENSE_PATH else file_path

    validation = resolve_license(preferred)

    click.echo("SpecLeft License Status")
    click.echo("-----------------------")
    click.echo("Core License: Apache 2.0")

    if validation.valid and validation.policy:
        policy = validation.policy
        commercial_status = "Active"
        license_type = policy.policy_type.value.capitalize()
        license_id = policy.license.license_id
        if policy.license.evaluation:
            valid_until = policy.license.evaluation.ends_at
        else:
            valid_until = policy.license.expires_at
        licensed_to = policy.license.licensed_to
    else:
        commercial_status = "Inactive"
        license_type = "Unknown"
        license_id = "N/A"
        valid_until = None
        licensed_to = "N/A"

    click.echo(f"Commercial License: {commercial_status}")
    click.echo(f"License Type: {license_type}")
    click.echo(f"License ID: {license_id}")
    if valid_until:
        click.echo(f"Valid Until: {valid_until}")
    else:
        click.echo("Valid Until: N/A")
    click.echo(f"Licensed To: {licensed_to}")

    validated_path = validation.path
    if validated_path is None and preferred is not None:
        validated_path = preferred

    if validated_path is None:
        click.echo("Validated File: (none)")
    else:
        click.echo(f"Validated File: {validated_path}")
