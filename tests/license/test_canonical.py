"""Tests for canonical payload generation."""

from __future__ import annotations

import json
from datetime import date

from specleft.license.canonical import canonical_payload


class TestCanonicalPayload:
    """Tests for canonical payload generation."""

    def test_canonical_deterministic(self) -> None:
        """Same input produces same output."""
        license_data = {
            "license_id": "lic_test12345678",
            "licensed_to": "owner/repo",
            "issued_at": date(2026, 1, 1),
            "expires_at": date(2027, 1, 1),
        }
        rules = {"priorities": {"critical": {"must_be_implemented": True}}}

        payload1 = canonical_payload("core", license_data, rules)
        payload2 = canonical_payload("core", license_data, rules)

        assert payload1 == payload2

    def test_canonical_sorted_keys(self) -> None:
        """Keys are sorted alphabetically."""
        license_data = {
            "license_id": "lic_test12345678",
            "licensed_to": "owner/repo",
            "issued_at": date(2026, 1, 1),
            "expires_at": date(2027, 1, 1),
        }
        rules = {"priorities": {"high": {"must_be_implemented": False}}}

        payload = canonical_payload("core", license_data, rules)
        decoded = json.loads(payload.decode("utf-8"))

        # Top level keys should be sorted
        assert list(decoded.keys()) == ["license", "policy_type", "rules"]

        # License keys should be sorted
        assert list(decoded["license"].keys()) == [
            "expires_at",
            "issued_at",
            "license_id",
            "licensed_to",
        ]

    def test_canonical_core_no_coverage(self) -> None:
        """Core policies exclude coverage block even if provided."""
        license_data = {
            "license_id": "lic_test12345678",
            "licensed_to": "owner/repo",
            "issued_at": date(2026, 1, 1),
            "expires_at": date(2027, 1, 1),
        }
        rules = {
            "priorities": {"critical": {"must_be_implemented": True}},
            "coverage": {"threshold_percent": 100, "fail_below": True},
        }

        payload = canonical_payload("core", license_data, rules)
        decoded = json.loads(payload.decode("utf-8"))

        assert "coverage" not in decoded["rules"]

    def test_canonical_enforce_includes_coverage(self) -> None:
        """Enforce policies include coverage block."""
        license_data = {
            "license_id": "lic_test12345678",
            "licensed_to": "owner/repo",
            "issued_at": date(2026, 1, 1),
            "expires_at": date(2027, 1, 1),
        }
        rules = {
            "priorities": {"critical": {"must_be_implemented": True}},
            "coverage": {"threshold_percent": 80, "fail_below": True},
        }

        payload = canonical_payload("enforce", license_data, rules)
        decoded = json.loads(payload.decode("utf-8"))

        assert "coverage" in decoded["rules"]
        assert decoded["rules"]["coverage"]["threshold_percent"] == 80
        assert decoded["rules"]["coverage"]["fail_below"] is True

    def test_canonical_evaluation_block(self) -> None:
        """Evaluation dates are serialized correctly."""
        license_data = {
            "license_id": "lic_test12345678",
            "licensed_to": "owner/repo",
            "issued_at": date(2026, 1, 1),
            "expires_at": date(2027, 1, 1),
            "evaluation": {
                "starts_at": date(2026, 1, 1),
                "ends_at": date(2026, 1, 31),
            },
        }
        rules = {
            "priorities": {},
            "coverage": {"threshold_percent": 100, "fail_below": True},
        }

        payload = canonical_payload("enforce", license_data, rules)
        decoded = json.loads(payload.decode("utf-8"))

        assert "evaluation" in decoded["license"]
        assert decoded["license"]["evaluation"]["starts_at"] == "2026-01-01"
        assert decoded["license"]["evaluation"]["ends_at"] == "2026-01-31"

    def test_canonical_derived_from(self) -> None:
        """Downgraded Core includes derived_from."""
        license_data = {
            "license_id": "lic_test12345678-core",
            "licensed_to": "owner/repo",
            "issued_at": date(2026, 1, 1),
            "expires_at": date(2027, 1, 1),
            "derived_from": "lic_test12345678",
        }
        rules = {"priorities": {"critical": {"must_be_implemented": True}}}

        payload = canonical_payload("core", license_data, rules)
        decoded = json.loads(payload.decode("utf-8"))

        assert decoded["license"]["derived_from"] == "lic_test12345678"
