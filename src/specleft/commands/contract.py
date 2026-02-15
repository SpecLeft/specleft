# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Contract command group."""

from __future__ import annotations

import sys

import click

from specleft.commands.output import json_dumps, resolve_output_format
from specleft.utils.messaging import print_support_footer
from specleft.commands.contracts.payloads import (
    build_contract_payload,
    build_contract_test_payload,
)
from specleft.commands.contracts.runner import (
    emit_contract_check,
    run_contract_tests,
)
from specleft.commands.contracts.table import (
    print_contract_table,
    print_contract_test_summary,
)


@click.group(invoke_without_command=True)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
@click.pass_context
def contract(ctx: click.Context, format_type: str | None, pretty: bool) -> None:
    """Agent contract commands."""
    if ctx.invoked_subcommand is not None:
        return
    selected_format = resolve_output_format(format_type)
    payload = build_contract_payload()
    if selected_format == "json":
        click.echo(json_dumps(payload, pretty=pretty))
    else:
        print_contract_table(payload)


@contract.command("test")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default=None,
    help="Output format. Defaults to table in a terminal and json otherwise.",
)
@click.option("--verbose", is_flag=True, help="Show detailed results for each check.")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output.")
def contract_test(format_type: str | None, verbose: bool, pretty: bool) -> None:
    """Verify SpecLeft Agent Contract guarantees."""
    selected_format = resolve_output_format(format_type)
    if selected_format == "json":
        passed, checks, errors = run_contract_tests(verbose=verbose)
        payload = build_contract_test_payload(
            passed=passed, checks=checks, errors=errors
        )
        click.echo(json_dumps(payload, pretty=pretty))
    else:
        click.echo("SpecLeft Agent Contract Tests")
        click.echo("━" * 44)
        passed, checks, errors = run_contract_tests(
            verbose=verbose,
            on_progress=lambda check: emit_contract_check(check, verbose),
        )
        click.echo("")
        print_contract_test_summary(passed=passed)
        if errors and verbose:
            click.echo("Errors:")
            for error in errors:
                click.echo(f"  - {error}")
        if not passed:
            click.echo("")
            print_support_footer()
    sys.exit(0 if passed else 1)
