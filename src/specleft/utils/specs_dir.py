# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Resolve the specs directory with fallback behavior."""

from __future__ import annotations

from pathlib import Path

DEFAULT_SPECS_DIR = Path(".specleft/specs")
FALLBACK_SPECS_DIR = Path("features")


def resolve_specs_dir(preferred: str | Path | None) -> Path:
    """Return the specs directory, preferring .specleft/specs.

    If an explicit path is provided, it is always returned.
    Otherwise, .specleft/specs is preferred when it exists,
    falling back to the legacy features/ directory.
    """
    if preferred:
        return Path(preferred)

    if DEFAULT_SPECS_DIR.exists():
        return DEFAULT_SPECS_DIR

    if FALLBACK_SPECS_DIR.exists():
        return FALLBACK_SPECS_DIR

    return DEFAULT_SPECS_DIR
