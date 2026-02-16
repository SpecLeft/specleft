# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Payload builders for SpecLeft MCP resources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specleft.commands.contracts.payloads import build_contract_payload
from specleft.commands.formatters import get_priority_value
from specleft.commands.status import build_status_entries
from specleft.utils.specs_dir import resolve_specs_dir
from specleft.validator import load_specs_directory

_PRIORITY_ORDER = ("critical", "high", "medium", "low")


def _percent(implemented: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((implemented / total) * 100, 1)


def _build_summary_payload(entries: list[Any]) -> dict[str, int | float]:
    total_scenarios = len(entries)
    implemented = sum(1 for entry in entries if entry.status == "implemented")
    skipped = total_scenarios - implemented
    total_features = len({entry.feature.feature_id for entry in entries})
    return {
        "features": total_features,
        "scenarios": total_scenarios,
        "implemented": implemented,
        "skipped": skipped,
        "coverage_percent": _percent(implemented, total_scenarios),
    }


def _build_priority_payload(entries: list[Any]) -> dict[str, dict[str, int | float]]:
    grouped: dict[str, dict[str, int]] = {}
    for entry in entries:
        priority = get_priority_value(entry.scenario)
        summary = grouped.setdefault(priority, {"total": 0, "implemented": 0})
        summary["total"] += 1
        if entry.status == "implemented":
            summary["implemented"] += 1

    ordered: list[str] = [
        *[item for item in _PRIORITY_ORDER if item in grouped],
        *sorted(priority for priority in grouped if priority not in _PRIORITY_ORDER),
    ]

    return {
        priority: {
            "total": grouped[priority]["total"],
            "implemented": grouped[priority]["implemented"],
            "percent": _percent(
                grouped[priority]["implemented"],
                grouped[priority]["total"],
            ),
        }
        for priority in ordered
    }


def _build_feature_payload(entries: list[Any]) -> list[dict[str, int | float | str]]:
    grouped: dict[str, dict[str, int]] = {}
    for entry in entries:
        feature_id = entry.feature.feature_id
        summary = grouped.setdefault(feature_id, {"total": 0, "implemented": 0})
        summary["total"] += 1
        if entry.status == "implemented":
            summary["implemented"] += 1

    payload: list[dict[str, int | float | str]] = []
    for feature_id in sorted(grouped):
        total = grouped[feature_id]["total"]
        implemented = grouped[feature_id]["implemented"]
        payload.append(
            {
                "feature_id": feature_id,
                "scenarios": total,
                "implemented": implemented,
                "coverage_percent": _percent(implemented, total),
            }
        )
    return payload


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
    features_dir: str | None = None,
    tests_dir: Path | None = None,
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
    summary = _build_summary_payload(entries)

    if not verbose:
        return {"initialised": True, **summary}

    return {
        "initialised": True,
        "summary": summary,
        "by_priority": _build_priority_payload(entries),
        "features": _build_feature_payload(entries),
    }


def build_mcp_contract_payload() -> dict[str, Any]:
    """Build the contract resource payload for MCP clients."""
    payload = build_contract_payload()
    raw_guarantees = payload.get("guarantees")
    guarantees = dict(raw_guarantees) if isinstance(raw_guarantees, dict) else {}
    raw_cli_api = guarantees.get("cli_api")
    cli_api = dict(raw_cli_api) if isinstance(raw_cli_api, dict) else {}
    raw_exit_codes = cli_api.get("exit_codes")
    if isinstance(raw_exit_codes, dict):
        exit_codes = dict(raw_exit_codes)
    else:
        exit_codes = {
            "success": 0,
            "error": 1,
            "cancelled": 2,
        }
    guarantees["exit_codes"] = exit_codes

    mcp_payload = dict(payload)
    mcp_payload["guarantees"] = guarantees
    mcp_payload.pop("docs", None)
    return mcp_payload


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
    }
