"""CLI entrypoint for SpecLeft."""

from __future__ import annotations

import click

from specleft.commands import (
    contract,
    coverage,
    doctor,
    enforce,
    features,
    init,
    next_command,
    plan,
    status,
    test,
)
from specleft.commands.constants import CLI_VERSION


@click.group()
@click.version_option(version=CLI_VERSION, prog_name="specleft")
def cli() -> None:
    """
    SpecLeft - Code driven intent analysis for Python.

    Documentation: https://specleft.dev/docs \n
    Github: https://github.com/SpecLeft/spec-left
    """


cli.add_command(test)
cli.add_command(features)
cli.add_command(doctor)
cli.add_command(status)
cli.add_command(next_command)
cli.add_command(plan)
cli.add_command(coverage)
cli.add_command(init)
cli.add_command(contract)
cli.add_command(enforce)


__all__ = ["cli"]


if __name__ == "__main__":
    cli()
