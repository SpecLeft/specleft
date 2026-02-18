#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BADGE_PATH = REPO_ROOT / ".github" / "assets" / "spec-coverage-badge.svg"


def _resolve_specleft_bin() -> str | None:
    override = os.environ.get("SPECLEFT_BIN")
    if override:
        override_path = Path(override)
        if override_path.exists():
            return str(override_path)
        resolved_override = shutil.which(override)
        if resolved_override:
            return resolved_override

    venv_bin = REPO_ROOT / ".venv" / "bin" / "specleft"
    if venv_bin.exists():
        return str(venv_bin)

    return shutil.which("specleft")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def main() -> int:
    specleft_bin = _resolve_specleft_bin()
    if not specleft_bin:
        print(
            "SKIP: specleft not found; skipping badge update.",
        )
        return 0

    coverage_cmd = [
        specleft_bin,
        "coverage",
        "--threshold",
        "100",
        "--format",
        "json",
    ]
    coverage_proc = _run(coverage_cmd)

    coverage_json: dict | None = None
    if coverage_proc.stdout.strip():
        try:
            coverage_json = json.loads(coverage_proc.stdout)
        except json.JSONDecodeError:
            coverage_json = None

    if coverage_json and coverage_json.get("passed") is False:
        print(f"WARNING: Missing Feature coverage {json.dumps(coverage_json, sort_keys=True)}")
    elif not coverage_json:
        # If we can't parse JSON, treat as a real failure: badge may be wrong.
        print("specleft coverage did not return valid JSON.", file=sys.stderr)
        if coverage_proc.stdout.strip():
            print(coverage_proc.stdout.strip(), file=sys.stderr)
        if coverage_proc.stderr.strip():
            print(coverage_proc.stderr.strip(), file=sys.stderr)
        return 1

    badge_path = Path(os.environ.get("SPECLEFT_BADGE_OUTPUT", str(DEFAULT_BADGE_PATH)))
    badge_path.parent.mkdir(parents=True, exist_ok=True)
    badge_cmd = [
        specleft_bin,
        "coverage",
        "--format",
        "badge",
        "--output",
        str(badge_path),
    ]
    badge_proc = _run(badge_cmd)
    if badge_proc.returncode != 0:
        if badge_proc.stdout.strip():
            print(badge_proc.stdout.strip(), file=sys.stderr)
        if badge_proc.stderr.strip():
            print(badge_proc.stderr.strip(), file=sys.stderr)
        return badge_proc.returncode

    if badge_proc.stdout.strip():
        print(badge_proc.stdout.strip())

    # Keep SVG files pre-commit friendly: ensure a trailing newline.
    svg_content = badge_path.read_bytes()
    if not svg_content.endswith(b"\n"):
        badge_path.write_bytes(svg_content + b"\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
