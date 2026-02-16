# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Implementation helpers for the MCP ``specleft_init`` tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specleft.commands.doctor import _build_doctor_checks, _build_doctor_output
from specleft.commands.init import _apply_init_plan, _init_plan
from specleft.utils.skill_integrity import (
    SKILL_FILE_PATH,
    SKILL_HASH_PATH,
    sync_skill_files,
)


class SecurityError(RuntimeError):
    """Raised when MCP init detects an unsafe write target."""


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def ensure_safe_write_target(path: Path, workspace: Path | None = None) -> Path:
    """Validate that write targets stay within the current workspace."""
    root = (workspace or Path.cwd()).resolve()
    candidate = path if path.is_absolute() else (root / path)

    if ".." in path.parts:
        raise SecurityError(f"Path traversal is not allowed: {path}")

    if not _is_relative_to(candidate, root):
        raise SecurityError(f"Path escapes workspace: {path}")

    current = candidate
    while True:
        if current.exists() and current.is_symlink():
            raise SecurityError(f"Refusing to write through symlink: {current}")
        if current == root:
            break
        if not _is_relative_to(current, root):
            raise SecurityError(f"Path escapes workspace: {path}")
        current = current.parent

    resolved_parent = candidate.parent.resolve(strict=False)
    if not _is_relative_to(resolved_parent, root):
        raise SecurityError(f"Path escapes workspace: {path}")

    if candidate.exists():
        resolved_candidate = candidate.resolve(strict=False)
        if not _is_relative_to(resolved_candidate, root):
            raise SecurityError(f"Path escapes workspace: {path}")

    return candidate


def _health_payload(checks: dict[str, Any]) -> dict[str, Any]:
    checks_map = checks.get("checks", {})
    python_check = checks_map.get("python_version", {})
    dependencies_check = checks_map.get("dependencies", {})
    plugin_check = checks_map.get("pytest_plugin", {})

    return {
        "python_version": python_check.get("version"),
        "dependencies_ok": dependencies_check.get("status") == "pass",
        "plugin_registered": bool(plugin_check.get("registered", False)),
    }


def _normalize_options(*, example: bool, blank: bool) -> tuple[bool, bool]:
    if example and blank:
        raise ValueError("Choose either --example or --blank, not both.")

    if not example and not blank:
        example = True

    if blank:
        example = False

    return example, blank


def _validate_init_targets(
    directories: list[Path],
    files: list[tuple[Path, str]],
    *,
    workspace: Path,
) -> None:
    for directory in directories:
        ensure_safe_write_target(directory, workspace)
    for file_path, _content in files:
        ensure_safe_write_target(file_path, workspace)
    ensure_safe_write_target(SKILL_FILE_PATH, workspace)
    ensure_safe_write_target(SKILL_HASH_PATH, workspace)


def run_specleft_init(
    *,
    example: bool = False,
    blank: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run SpecLeft initialisation in MCP-safe mode."""
    try:
        use_example, _ = _normalize_options(example=example, blank=blank)
    except ValueError as exc:
        return {
            "success": False,
            "error": str(exc),
            "health": {
                "python_version": None,
                "dependencies_ok": False,
                "plugin_registered": False,
            },
            "created": [],
            "skill_file": str(SKILL_FILE_PATH),
            "next_steps": "Fix the input arguments and retry.",
        }

    checks = _build_doctor_checks(verify_skill=False)
    doctor_output = _build_doctor_output(checks)
    health = _health_payload(checks)

    if not bool(doctor_output.get("healthy", False)):
        return {
            "success": False,
            "error": "Environment health checks failed.",
            "health": health,
            "created": [],
            "skill_file": str(SKILL_FILE_PATH),
            "next_steps": "Run `specleft doctor` and resolve reported issues.",
            "errors": doctor_output.get("errors", []),
        }

    directories, files = _init_plan(example=use_example)
    workspace = Path.cwd().resolve()

    try:
        _validate_init_targets(directories, files, workspace=workspace)
    except SecurityError as exc:
        return {
            "success": False,
            "error": str(exc),
            "health": health,
            "created": [],
            "skill_file": str(SKILL_FILE_PATH),
            "next_steps": "Review filesystem safety and retry initialisation.",
        }

    if dry_run:
        planned = [str(path) for path, _content in files]
        planned.extend([str(SKILL_FILE_PATH), str(SKILL_HASH_PATH)])
        planned.extend(str(directory) for directory in directories)
        return {
            "success": True,
            "dry_run": True,
            "health": health,
            "created": sorted(set(planned)),
            "skill_file": str(SKILL_FILE_PATH),
            "next_steps": "Run specleft_init without dry_run to write files.",
        }

    created_paths = [str(path) for path in _apply_init_plan(directories, files)]
    skill_sync = sync_skill_files(overwrite_existing=False)
    created_paths.extend(skill_sync.created)

    return {
        "success": True,
        "health": health,
        "created": created_paths,
        "skill_file": str(SKILL_FILE_PATH),
        "next_steps": "Read .specleft/SKILL.md for full CLI reference",
        "warnings": skill_sync.warnings,
    }
