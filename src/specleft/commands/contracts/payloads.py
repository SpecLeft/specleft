# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Payload builders for contract commands."""

from __future__ import annotations

from specleft.commands.constants import CLI_VERSION, CONTRACT_DOC_PATH, CONTRACT_VERSION
from specleft.commands.contracts.types import ContractCheckResult


def _fix_command_for_check(check_name: str) -> str | None:
    mapping = {
        "dry_run_no_writes": "specleft test skeleton --dry-run --format json",
        "no_implicit_writes": "specleft test skeleton --format table",
        "existing_tests_not_modified_by_default": "specleft test skeleton --force --format table",
        "validation_non_destructive": "specleft features validate --format json",
        "json_supported_globally": "specleft guide --format json",
        "json_schema_valid": "specleft contract --format json",
        "exit_codes_correct": "specleft test skeleton --format table",
    }
    return mapping.get(check_name)


def build_contract_payload() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "specleft_version": CLI_VERSION,
        "guarantees": {
            "safety": {
                "no_implicit_writes": True,
                "dry_run_never_writes": True,
                "existing_tests_not_modified_by_default": True,
            },
            "execution": {
                "skeletons_skipped_by_default": True,
                "skipped_never_fail": True,
                "validation_non_destructive": True,
            },
            "determinism": {
                "deterministic_for_same_inputs": True,
                "safe_for_retries": True,
            },
            "cli_api": {
                "json_supported_globally": True,
                "json_additive_within_minor": True,
                "exit_codes": {
                    "success": 0,
                    "error": 1,
                    "cancelled": 2,
                },
            },
            "skill_security": {
                "skill_file_integrity_check": True,
                "skill_file_commands_are_simple": True,
            },
        },
        "docs": {
            "agent_contract": CONTRACT_DOC_PATH,
        },
    }


def build_contract_test_payload(
    *,
    passed: bool,
    checks: list[ContractCheckResult],
    errors: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "specleft_version": CLI_VERSION,
        "passed": passed,
        "checks": [
            {
                "category": check.category,
                "name": check.name,
                "status": check.status,
                **({"message": check.message} if check.message else {}),
                **(
                    {"fix_command": _fix_command_for_check(check.name)}
                    if check.status == "fail"
                    and _fix_command_for_check(check.name) is not None
                    else {}
                ),
            }
            for check in checks
        ],
    }
    if errors:
        payload["errors"] = errors
    return payload
