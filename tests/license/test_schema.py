"""Tests for license schema models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError
from specleft.license.schema import (
    CoverageRules,
    EvaluationPeriod,
    LicenseInfo,
    PolicyType,
    SignedPolicy,
)


class TestPolicyType:
    """Tests for PolicyType enum."""

    def test_core_value(self) -> None:
        assert PolicyType.CORE.value == "core"

    def test_enforce_value(self) -> None:
        assert PolicyType.ENFORCE.value == "enforce"


class TestEvaluationPeriod:
    """Tests for EvaluationPeriod model."""

    def test_valid_period(self) -> None:
        period = EvaluationPeriod(
            starts_at=date(2026, 1, 1),
            ends_at=date(2026, 1, 31),
        )
        assert period.starts_at == date(2026, 1, 1)
        assert period.ends_at == date(2026, 1, 31)

    def test_ends_before_starts_raises(self) -> None:
        with pytest.raises(ValidationError, match="ends_at must be after starts_at"):
            EvaluationPeriod(
                starts_at=date(2026, 2, 1),
                ends_at=date(2026, 1, 1),
            )


class TestCoverageRules:
    """Tests for CoverageRules model."""

    def test_default_values(self) -> None:
        rules = CoverageRules()
        assert rules.threshold_percent == 100
        assert rules.fail_below is True

    def test_custom_threshold(self) -> None:
        rules = CoverageRules(threshold_percent=80, fail_below=False)
        assert rules.threshold_percent == 80
        assert rules.fail_below is False

    def test_threshold_bounds(self) -> None:
        CoverageRules(threshold_percent=0)  # Valid
        CoverageRules(threshold_percent=100)  # Valid

        with pytest.raises(ValidationError):
            CoverageRules(threshold_percent=-1)

        with pytest.raises(ValidationError):
            CoverageRules(threshold_percent=101)


class TestLicenseInfo:
    """Tests for LicenseInfo model."""

    def test_valid_license(self) -> None:
        info = LicenseInfo(
            license_id="lic_abc12345678",
            licensed_to="owner/repo",
            issued_at=date(2026, 1, 1),
            expires_at=date(2027, 1, 1),
        )
        assert info.license_id == "lic_abc12345678"
        assert info.licensed_to == "owner/repo"

    def test_invalid_license_id_pattern(self) -> None:
        with pytest.raises(ValidationError, match="license_id"):
            LicenseInfo(
                license_id="invalid-id",  # Missing lic_ prefix
                licensed_to="owner/repo",
                issued_at=date(2026, 1, 1),
                expires_at=date(2027, 1, 1),
            )

    def test_expires_before_issued_raises(self) -> None:
        with pytest.raises(ValidationError, match="expires_at must be after issued_at"):
            LicenseInfo(
                license_id="lic_abc12345678",
                licensed_to="owner/repo",
                issued_at=date(2027, 1, 1),
                expires_at=date(2026, 1, 1),
            )


class TestSignedPolicy:
    """Tests for SignedPolicy model with type-specific validation."""

    def _base_policy_data(self, policy_type: str) -> dict:
        """Create base policy data for testing."""
        data = {
            "policy_id": "test-v1",
            "policy_version": "1.0",
            "policy_type": policy_type,
            "license": {
                "license_id": "lic_test12345678",
                "licensed_to": "owner/repo",
                "issued_at": date(2026, 1, 1),
                "expires_at": date(2027, 1, 1),
            },
            "rules": {
                "priorities": {"critical": {"must_be_implemented": True}},
            },
            "signature": {
                "algorithm": "ed25519",
                "key_id": "test-key",
                "value": "dGVzdA==",
            },
        }
        return data

    def test_valid_core_policy(self) -> None:
        data = self._base_policy_data("core")
        policy = SignedPolicy.model_validate(data)
        assert policy.policy_type == PolicyType.CORE

    def test_valid_enforce_policy(self) -> None:
        data = self._base_policy_data("enforce")
        data["rules"]["coverage"] = {"threshold_percent": 100, "fail_below": True}
        policy = SignedPolicy.model_validate(data)
        assert policy.policy_type == PolicyType.ENFORCE

    def test_core_with_coverage_raises(self) -> None:
        data = self._base_policy_data("core")
        data["rules"]["coverage"] = {"threshold_percent": 100}
        with pytest.raises(ValidationError, match="Core policies cannot have coverage"):
            SignedPolicy.model_validate(data)

    def test_core_with_evaluation_raises(self) -> None:
        data = self._base_policy_data("core")
        data["license"]["evaluation"] = {
            "starts_at": date(2026, 1, 1),
            "ends_at": date(2026, 1, 31),
        }
        with pytest.raises(
            ValidationError, match="Core policies cannot have evaluation"
        ):
            SignedPolicy.model_validate(data)

    def test_enforce_without_coverage_raises(self) -> None:
        data = self._base_policy_data("enforce")
        # No coverage rules
        with pytest.raises(
            ValidationError, match="Enforce policies must have coverage"
        ):
            SignedPolicy.model_validate(data)

    def test_invalid_policy_version_format(self) -> None:
        data = self._base_policy_data("core")
        data["policy_version"] = "1"  # Invalid format
        with pytest.raises(ValidationError, match="policy_version"):
            SignedPolicy.model_validate(data)

    def test_enforce_with_evaluation(self) -> None:
        data = self._base_policy_data("enforce")
        data["rules"]["coverage"] = {"threshold_percent": 80}
        data["license"]["evaluation"] = {
            "starts_at": date(2026, 1, 1),
            "ends_at": date(2026, 1, 31),
        }
        policy = SignedPolicy.model_validate(data)
        assert policy.license.evaluation is not None
        assert policy.license.evaluation.ends_at == date(2026, 1, 31)
