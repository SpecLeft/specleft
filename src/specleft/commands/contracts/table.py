# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Table output for contract commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import click

from specleft.commands.constants import CONTRACT_DOC_PATH
from specleft.commands.contracts.types import ContractCheckResult


def print_contract_table(payload: Mapping[str, object]) -> None:
    exit_codes = cast(dict[str, Any], payload.get("exit_codes", {}))
    click.echo("SpecLeft Agent Contract")
    click.echo("─" * 40)
    click.echo(f"Contract version: {payload.get('contract_version')}")
    click.echo(f"SpecLeft version: {payload.get('specleft_version')}")
    click.echo("")
    click.echo("Safety:")
    click.echo(
        "  - No writes without confirmation or --force"
        if payload.get("no_writes_without_confirmation")
        else "  - No implicit writes guarantee missing"
    )
    click.echo(
        "  - --dry-run never writes to disk"
        if payload.get("dry_run_never_writes")
        else "  - --dry-run guarantee missing"
    )
    click.echo(
        "  - Existing tests not modified by default"
        if payload.get("existing_files_never_overwritten")
        else "  - Existing test protection missing"
    )
    click.echo("")
    click.echo("Execution:")
    click.echo(
        "  - Skeleton tests skipped by default"
        if payload.get("skeletons_skipped_by_default")
        else "  - Skeleton skip guarantee missing"
    )
    click.echo(
        "  - Skipped scenarios never fail tests"
        if payload.get("skipped_never_fail")
        else "  - Skip behavior guarantee missing"
    )
    click.echo(
        "  - Init refuses symlink targets"
        if payload.get("init_refuses_symlinks")
        else "  - Init path safety guarantee missing"
    )
    click.echo("")
    click.echo("Determinism:")
    click.echo(
        "  - Commands deterministic for same inputs"
        if payload.get("deterministic_for_same_inputs")
        else "  - Determinism guarantee missing"
    )
    click.echo(
        "  - Safe to re-run in retry loops"
        if payload.get("safe_for_retries")
        else "  - Retry safety guarantee missing"
    )
    click.echo("")
    click.echo("JSON & CLI:")
    success = exit_codes.get("success")
    error = exit_codes.get("error")
    cancelled = exit_codes.get("cancelled")
    click.echo(
        f"  - Stable exit codes: {success}=success, {error}=error, {cancelled}=cancel"
    )
    click.echo(
        "  - CLI rejects shell metacharacters in arguments"
        if payload.get("cli_rejects_shell_metacharacters")
        else "  - CLI input hardening guarantee missing"
    )
    click.echo("")
    click.echo("Skill Security:")
    click.echo(
        "  - Skill file integrity is verifiable"
        if payload.get("skill_file_integrity_check")
        else "  - Skill integrity guarantee missing"
    )
    click.echo(
        "  - Skill commands are simple invocations (no shell metacharacters)"
        if payload.get("skill_file_commands_are_simple")
        else "  - Skill command simplicity guarantee missing"
    )
    click.echo(
        "  - No network access and no telemetry"
        if payload.get("no_network_access") and payload.get("no_telemetry")
        else "  - Network/telemetry isolation guarantee missing"
    )
    click.echo("")
    click.echo(f"For full details, see: {CONTRACT_DOC_PATH}")
    click.echo("─" * 40)


def format_contract_check_label(check: ContractCheckResult) -> str:
    return f"{check.category.capitalize()}: {check.name.replace('_', ' ')}"


def emit_contract_check(check: ContractCheckResult, verbose: bool) -> None:
    marker = "✓" if check.status == "pass" else "✗"
    click.echo(f"{marker} {format_contract_check_label(check)}")
    if verbose and check.message:
        click.echo(f"  {check.message}")


def print_contract_test_summary(*, passed: bool) -> None:
    if passed:
        click.echo("All Agent Contract guarantees verified.")
    else:
        click.echo("One or more Agent Contract guarantees failed.")
