"""Tests for contract table output helpers."""

from __future__ import annotations

import pytest
from specleft.commands.contracts.table import (
    emit_contract_check,
    format_contract_check_label,
    print_contract_table,
    print_contract_test_summary,
)
from specleft.commands.contracts.types import ContractCheckResult


def test_format_contract_check_label() -> None:
    check = ContractCheckResult(category="safety", name="dry_run", status="pass")
    assert format_contract_check_label(check) == "Safety: dry run"


def test_emit_contract_check_outputs_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    check = ContractCheckResult(
        category="execution",
        name="skipped_never_fail",
        status="fail",
        message="missing skip",
    )
    emit_contract_check(check, verbose=True)
    output = capsys.readouterr().out
    assert "✗ Execution: skipped never fail" in output
    assert "missing skip" in output


def test_print_contract_table_outputs_sections(
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {
        "contract_version": "1.1",
        "specleft_version": "0.2.0",
        "guarantees": {
            "dry_run_never_writes": True,
            "no_writes_without_confirmation": True,
            "existing_files_never_overwritten": True,
            "skeletons_skipped_by_default": True,
            "skipped_never_fail": True,
            "deterministic_for_same_inputs": True,
            "safe_for_retries": True,
            "exit_codes": {
                "success": 0,
                "error": 1,
                "cancelled": 2,
            },
            "skill_file_integrity_check": True,
            "skill_file_commands_are_simple": True,
            "cli_rejects_shell_metacharacters": True,
            "init_refuses_symlinks": True,
            "no_network_access": True,
            "no_telemetry": True,
        },
    }
    print_contract_table(payload)
    output = capsys.readouterr().out
    assert "SpecLeft Agent Contract" in output
    assert "Safety:" in output
    assert "Execution:" in output
    assert "Determinism:" in output
    assert "JSON & CLI:" in output
    assert "Skill Security:" in output


def test_print_contract_test_summary(capsys: pytest.CaptureFixture[str]) -> None:
    print_contract_test_summary(passed=True)
    output = capsys.readouterr().out
    assert "All Agent Contract guarantees verified" in output

    print_contract_test_summary(passed=False)
    output = capsys.readouterr().out
    assert "Agent Contract guarantees failed" in output
