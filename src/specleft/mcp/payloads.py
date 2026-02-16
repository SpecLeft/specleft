# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Payload builders for SpecLeft MCP resources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specleft.commands.contracts.payloads import build_contract_payload
from specleft.commands.status import build_status_entries, build_status_json
from specleft.utils.specs_dir import resolve_specs_dir
from specleft.validator import load_specs_directory


def _build_empty_status_payload(*, initialised: bool, verbose: bool) -> dict[str, Any]:
    if not verbose:
        return {
            "initialised": initialised,
            "features": 0,
            "scenarios": 0,
            "implemented": 0,
            "skipped": 0,
            "coverage_percent": 0.0,
        }

    return {
        "initialised": initialised,
        "summary": {
            "features": 0,
            "scenarios": 0,
            "implemented": 0,
            "skipped": 0,
            "coverage_percent": 0.0,
        },
        "by_priority": {},
        "features": [],
    }


def build_mcp_status_payload(
    *,
    verbose: bool = False,
    features_dir: str | None = ".specleft/specs",
    tests_dir: Path | None = Path("tests"),
) -> dict[str, Any]:
    """Build the status resource payload for MCP clients."""
    resolved_features_dir = resolve_specs_dir(features_dir)
    if not resolved_features_dir.exists():
        return _build_empty_status_payload(initialised=False, verbose=verbose)

    try:
        config = load_specs_directory(resolved_features_dir)
    except FileNotFoundError:
        return _build_empty_status_payload(initialised=False, verbose=verbose)
    except ValueError as exc:
        if "No feature specs found" in str(exc):
            return _build_empty_status_payload(initialised=True, verbose=verbose)
        return _build_empty_status_payload(initialised=False, verbose=verbose)

    entries = build_status_entries(config, tests_dir or Path("tests"))
    status_payload = build_status_json(
        entries,
        include_execution_time=False,
        verbose=verbose,
    )
    if isinstance(status_payload, dict):
        return status_payload
    return _build_empty_status_payload(initialised=True, verbose=verbose)


def build_mcp_contract_payload() -> dict[str, Any]:
    """Build the contract resource payload for MCP clients."""
    payload = build_contract_payload()
    raw_guarantees = payload.get("guarantees")
    guarantees = dict(raw_guarantees) if isinstance(raw_guarantees, dict) else {}
    raw_safety = guarantees.get("safety")
    safety = dict(raw_safety) if isinstance(raw_safety, dict) else {}
    raw_execution = guarantees.get("execution")
    execution = dict(raw_execution) if isinstance(raw_execution, dict) else {}
    raw_determinism = guarantees.get("determinism")
    determinism = dict(raw_determinism) if isinstance(raw_determinism, dict) else {}
    raw_cli_api = guarantees.get("cli_api")
    cli_api = dict(raw_cli_api) if isinstance(raw_cli_api, dict) else {}
    raw_skill_security = guarantees.get("skill_security")
    skill_security = (
        dict(raw_skill_security) if isinstance(raw_skill_security, dict) else {}
    )

    raw_exit_codes = cli_api.get("exit_codes")
    if isinstance(raw_exit_codes, dict):
        exit_codes = dict(raw_exit_codes)
    else:
        exit_codes = {
            "success": 0,
            "error": 1,
            "cancelled": 2,
        }

    return {
        "contract_version": payload.get("contract_version"),
        "specleft_version": payload.get("specleft_version"),
        "guarantees": {
            "dry_run_never_writes": bool(safety.get("dry_run_never_writes", True)),
            "no_writes_without_confirmation": bool(
                safety.get("no_implicit_writes", True)
            ),
            "existing_files_never_overwritten": bool(
                safety.get("existing_tests_not_modified_by_default", True)
            ),
            "skeletons_skipped_by_default": bool(
                execution.get("skeletons_skipped_by_default", True)
            ),
            "skipped_never_fail": bool(execution.get("skipped_never_fail", True)),
            "deterministic_for_same_inputs": bool(
                determinism.get("deterministic_for_same_inputs", True)
            ),
            "safe_for_retries": bool(determinism.get("safe_for_retries", True)),
            "exit_codes": exit_codes,
            "skill_file_integrity_check": bool(
                skill_security.get("skill_file_integrity_check", True)
            ),
            "skill_file_commands_are_simple": bool(
                skill_security.get("skill_file_commands_are_simple", True)
            ),
            "cli_rejects_shell_metacharacters": True,
            "init_refuses_symlinks": True,
            "no_network_access": True,
            "no_telemetry": True,
        },
    }


def build_mcp_guide_payload() -> dict[str, object]:
    """Build the workflow guide payload for MCP clients."""
    return {
        "workflow": {
            "bulk_setup": [
                {
                    "step": 1,
                    "command": "plan --analyze",
                    "description": "Understand how the current plan aligns with the prd-template.yml",
                },
                {
                    "step": 2,
                    "action": "modify",
                    "description": "If required, modify .specleft/templates/prd-template.yml to align PRD parsing.",
                },
                {
                    "step": 3,
                    "command": "plan",
                    "description": "Generate features from the calibrated PRD.",
                },
                {
                    "step": 4,
                    "command": "features add-scenario --add-test skeleton",
                    "description": "Append scenarios and scaffold tests.",
                },
            ],
            "incremental_setup": [
                {
                    "step": 1,
                    "command": "features add",
                    "description": "Add an individual feature spec.",
                },
                {
                    "step": 2,
                    "command": "features add-scenario --add-test skeleton",
                    "description": "Append scenarios and scaffold tests.",
                },
            ],
            "implementation": [
                {
                    "step": 1,
                    "command": "next --limit 1",
                    "description": "Pick the next scenario to implement.",
                },
                {
                    "step": 2,
                    "action": "implement",
                    "description": "Write the test logic first, then application code.",
                },
                {
                    "step": 3,
                    "action": "pytest",
                    "description": "Run tests, fix failures, and repeat.",
                },
                {
                    "step": 4,
                    "command": "features validate --strict",
                    "description": "Validate all specs before commit.",
                },
                {
                    "step": 5,
                    "command": "coverage --threshold 100",
                    "description": "Verify feature coverage target.",
                },
            ],
        },
        "skill_file": "Run specleft_init to generate .specleft/SKILL.md with full CLI reference",
        "security_notes": [
            "Avoid sensitive data in feature and scenario names.",
        ],
    }
