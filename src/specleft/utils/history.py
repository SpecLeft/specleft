# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""History logging utilities for feature authoring."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _history_dir() -> Path:
    return Path(".specleft") / "history"


def _history_path(feature_id: str) -> Path:
    return _history_dir() / f"{feature_id}.json"


def load_feature_history(feature_id: str) -> list[dict[str, Any]]:
    """Load history events for a feature."""
    history_path = _history_path(feature_id)
    if not history_path.exists():
        return []

    try:
        payload = json.loads(history_path.read_text())
    except json.JSONDecodeError:
        return []

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def log_feature_event(
    feature_id: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Append a history event for a feature and return updated entries."""
    history_dir = _history_dir()
    history_dir.mkdir(parents=True, exist_ok=True)

    entries = load_feature_history(feature_id)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "feature_id": feature_id,
        "details": details or {},
    }
    entries.append(entry)
    _history_path(feature_id).write_text(json.dumps(entries, indent=2))
    return entries
