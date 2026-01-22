"""Canonical payload generation for cryptographic signing.

Deterministic JSON serialization that must match exactly between
the CLI and the license service.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any


def _default_serializer(obj: Any) -> str:
    """JSON serializer for date objects."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj)}")


def canonical_payload(
    policy_type: str,
    license_data: dict[str, Any],
    rules: dict[str, Any],
) -> bytes:
    """Generate deterministic JSON payload for signing.

    The payload structure MUST match exactly in CLI and license service
    to ensure signature verification works correctly.

    Args:
        policy_type: Policy type ("core" or "enforce")
        license_data: License information as dict (from model_dump())
        rules: Policy rules as dict (from model_dump())

    Returns:
        UTF-8 encoded bytes of the canonical JSON payload
    """
    # Build license block with alphabetically sorted keys
    license_block: dict[str, Any] = {
        "expires_at": license_data["expires_at"],
        "issued_at": license_data["issued_at"],
        "license_id": license_data["license_id"],
        "licensed_to": license_data["licensed_to"],
    }

    # Add optional fields in alphabetical order if present
    if license_data.get("derived_from"):
        license_block["derived_from"] = license_data["derived_from"]

    if license_data.get("evaluation"):
        license_block["evaluation"] = {
            "ends_at": license_data["evaluation"]["ends_at"],
            "starts_at": license_data["evaluation"]["starts_at"],
        }

    # Build rules block
    rules_block: dict[str, Any] = {"priorities": {}}

    # Add priorities in sorted order
    for priority_key in sorted(rules.get("priorities", {}).keys()):
        rules_block["priorities"][priority_key] = {
            "must_be_implemented": rules["priorities"][priority_key][
                "must_be_implemented"
            ]
        }

    # Coverage is Enforce-only
    if policy_type == "enforce" and rules.get("coverage"):
        rules_block["coverage"] = {
            "fail_below": rules["coverage"]["fail_below"],
            "threshold_percent": rules["coverage"]["threshold_percent"],
        }

    payload = {
        "license": license_block,
        "policy_type": policy_type,
        "rules": rules_block,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_default_serializer,
    ).encode("utf-8")
