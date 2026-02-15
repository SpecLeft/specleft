# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared CLI output helpers."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from typing import Any

COMPACT_ENV_VAR = "SPECLEFT_COMPACT"


def compact_mode_enabled() -> bool:
    """Return True when compact output mode is enabled."""
    raw_value = os.getenv(COMPACT_ENV_VAR)
    if raw_value is None:
        return False

    normalized = raw_value.strip().lower()
    return normalized not in {"", "0", "false", "no", "off"}


def resolve_output_format(
    selected_format: str | None,
    *,
    choices: Sequence[str] = ("table", "json"),
) -> str:
    """Resolve output format with TTY-aware defaults when no explicit format is set."""
    available = tuple(choice.lower() for choice in choices)
    if selected_format:
        return selected_format.lower()

    if "table" in available and "json" in available:
        return "table" if sys.stdout.isatty() else "json"

    if "json" in available:
        return "json"

    if not available:
        raise ValueError("At least one output format choice is required.")
    return available[0]


def json_dumps(payload: Any, *, pretty: bool = False) -> str:
    """Serialize JSON using compact separators by default."""
    if pretty:
        return json.dumps(payload, indent=2, default=str)
    return json.dumps(payload, separators=(",", ":"), default=str)
