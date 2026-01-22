"""Tests for policy signature verification."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from specleft.license.schema import SignedPolicy
from specleft.license.verify import (
    VerifyFailure,
    add_trusted_key,
    remove_trusted_key,
    verify_policy,
)

from tests.license.fixtures import (
    TEST_KEY_ID,
    TEST_PUBLIC_KEY_B64,
    create_core_policy_data,
    create_enforce_policy_data,
)


@pytest.fixture(autouse=True)
def setup_test_key():
    """Set up test key for each test."""
    add_trusted_key(TEST_KEY_ID, TEST_PUBLIC_KEY_B64)
    yield
    remove_trusted_key(TEST_KEY_ID)


class TestVerifySignature:
    """Tests for signature verification."""

    def test_verify_valid_signature(self) -> None:
        """Passes with correct signature."""
        data = create_core_policy_data(licensed_to="test-owner/test-repo")
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is True
        assert result.failure is None

    def test_verify_tampered_license_id(self) -> None:
        """Fails if license_id changed after signing."""
        data = create_core_policy_data()
        # Tamper with the license_id after signing
        data["license"]["license_id"] = "lic_tampered1234"
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.INVALID_SIGNATURE

    def test_verify_tampered_licensed_to(self) -> None:
        """Fails if licensed_to changed after signing."""
        data = create_core_policy_data(licensed_to="original/repo")
        # Tamper with licensed_to
        data["license"]["licensed_to"] = "attacker/repo"
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="attacker/repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.INVALID_SIGNATURE

    def test_verify_tampered_dates(self) -> None:
        """Fails if dates changed after signing."""
        data = create_core_policy_data()
        # Tamper with expiry date
        data["license"]["expires_at"] = date.today() + timedelta(days=1000)
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.INVALID_SIGNATURE

    def test_verify_tampered_rules(self) -> None:
        """Fails if rules changed after signing."""
        data = create_core_policy_data(
            priorities={"critical": {"must_be_implemented": True}}
        )
        # Tamper with rules
        data["rules"]["priorities"]["critical"]["must_be_implemented"] = False
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.INVALID_SIGNATURE

    def test_verify_unknown_key_id(self) -> None:
        """Fails with clear error for unknown key."""
        data = create_core_policy_data()
        data["signature"]["key_id"] = "unknown-key-id"
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.INVALID_SIGNATURE
        assert "Unknown key" in (result.message or "")


class TestVerifyExpiration:
    """Tests for license expiration checks."""

    def test_verify_expired_license(self) -> None:
        """Fails with renewal link for expired license."""
        yesterday = date.today() - timedelta(days=1)
        data = create_core_policy_data(
            issued_at=date.today() - timedelta(days=365),
            expires_at=yesterday,
        )
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.EXPIRED
        assert "renew" in (result.message or "").lower()


class TestVerifyRepoBinding:
    """Tests for repository binding verification."""

    def test_verify_repo_mismatch_exact(self) -> None:
        """owner/repo vs owner/other fails."""
        data = create_core_policy_data(licensed_to="owner/repo")
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="owner/other")

        assert result.valid is False
        assert result.failure == VerifyFailure.REPO_MISMATCH

    def test_verify_repo_mismatch_org(self) -> None:
        """owner/* vs different-owner/repo fails."""
        data = create_core_policy_data(licensed_to="owner/*")
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="different-owner/repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.REPO_MISMATCH

    def test_verify_org_wildcard_matches(self) -> None:
        """owner/* matches owner/any-repo."""
        data = create_core_policy_data(licensed_to="owner/*")
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="owner/any-repo")

        assert result.valid is True


class TestVerifyEvaluation:
    """Tests for evaluation period checks."""

    def test_verify_evaluation_active(self) -> None:
        """Passes within evaluation window."""
        today = date.today()
        data = create_enforce_policy_data(
            licensed_to="test-owner/test-repo",
            evaluation_starts=today - timedelta(days=10),
            evaluation_ends=today + timedelta(days=20),
        )
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is True

    def test_verify_evaluation_expired(self) -> None:
        """Returns EVALUATION_EXPIRED after window ends."""
        today = date.today()
        data = create_enforce_policy_data(
            licensed_to="test-owner/test-repo",
            evaluation_starts=today - timedelta(days=40),
            evaluation_ends=today - timedelta(days=10),
        )
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is False
        assert result.failure == VerifyFailure.EVALUATION_EXPIRED

    def test_verify_enforce_no_evaluation(self) -> None:
        """Purchased license has no eval block and works."""
        data = create_enforce_policy_data(
            licensed_to="test-owner/test-repo",
            # No evaluation period = purchased license
        )
        policy = SignedPolicy.model_validate(data)

        result = verify_policy(policy, repo_identity_override="test-owner/test-repo")

        assert result.valid is True
        assert policy.license.evaluation is None
