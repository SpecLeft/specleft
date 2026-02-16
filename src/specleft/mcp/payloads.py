# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Payload builders for SpecLeft MCP resources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specleft.commands.coverage import _build_coverage_json
from specleft.commands.contracts.payloads import build_contract_payload
from specleft.commands.features import _build_features_list_json
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
    status_summary = build_status_json(
        entries,
        include_execution_time=False,
        verbose=verbose,
    )
    coverage_root = _build_coverage_json(entries)
    raw_coverage = coverage_root.get("coverage")
    coverage_payload: dict[str, Any] = (
        raw_coverage if isinstance(raw_coverage, dict) else {}
    )
    features_payload = _build_features_list_json(config)

    if not verbose:
        summary = dict(status_summary) if isinstance(status_summary, dict) else {}
        features_summary = features_payload.get("summary", {})
        coverage_overall = coverage_payload.get("overall", {})
        summary["features"] = (
            features_summary.get("features", summary.get("features", 0))
            if isinstance(features_summary, dict)
            else summary.get("features", 0)
        )
        if isinstance(coverage_overall, dict):
            summary["coverage_percent"] = coverage_overall.get(
                "percent",
                summary.get("coverage_percent", 0.0),
            )
        return summary

    summary_section = {}
    if isinstance(status_summary, dict):
        raw_summary = status_summary.get("summary", {})
        if isinstance(raw_summary, dict):
            summary_section = dict(raw_summary)
    features_summary = features_payload.get("summary", {})
    if isinstance(features_summary, dict):
        summary_section["features"] = features_summary.get(
            "features",
            summary_section.get("features", 0),
        )
    coverage_overall = coverage_payload.get("overall", {})
    if isinstance(coverage_overall, dict):
        summary_section["coverage_percent"] = coverage_overall.get(
            "percent",
            summary_section.get("coverage_percent", 0.0),
        )

    by_priority: dict[str, Any] = {}
    raw_by_priority = coverage_payload.get("by_priority", {})
    if isinstance(raw_by_priority, dict):
        by_priority = raw_by_priority

    features: list[dict[str, Any]] = []
    raw_by_feature = coverage_payload.get("by_feature", [])
    if isinstance(raw_by_feature, list):
        for item in raw_by_feature:
            if not isinstance(item, dict):
                continue
            features.append(
                {
                    "feature_id": item.get("feature_id"),
                    "scenarios": item.get("total", 0),
                    "implemented": item.get("implemented", 0),
                    "coverage_percent": item.get("percent", 0.0),
                }
            )
    return {
        "initialised": True,
        "summary": summary_section,
        "by_priority": by_priority,
        "features": features,
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
