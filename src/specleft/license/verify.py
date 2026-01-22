"""Policy signature verification and validation.

Verifies Ed25519 signatures and performs all license validation checks:
- Signature verification
- License expiration
- Repository binding
- Evaluation period
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

if TYPE_CHECKING:
    from specleft.license.schema import SignedPolicy

# Trusted public keys for signature verification
# In production, this would contain the actual SpecLeft signing keys
TRUSTED_KEYS: dict[str, str] = {
    # Placeholder for production key - base64 encoded 32-byte Ed25519 public key
    "specleft-prod-2026": "",
}


class VerifyFailure(Enum):
    """Verification failure reasons."""

    INVALID_SIGNATURE = "invalid_signature"
    EXPIRED = "expired"
    REPO_MISMATCH = "repo_mismatch"
    REPO_DETECTION_FAILED = "repo_detection_failed"
    EVALUATION_EXPIRED = "evaluation_expired"


@dataclass
class VerifyResult:
    """Result of policy verification."""

    valid: bool
    failure: VerifyFailure | None = None
    message: str | None = None


def add_trusted_key(key_id: str, public_key_base64: str) -> None:
    """Add a trusted public key for verification.

    This is primarily used for testing with test keypairs.

    Args:
        key_id: Key identifier
        public_key_base64: Base64-encoded Ed25519 public key bytes
    """
    TRUSTED_KEYS[key_id] = public_key_base64


def remove_trusted_key(key_id: str) -> None:
    """Remove a trusted public key.

    Args:
        key_id: Key identifier to remove
    """
    TRUSTED_KEYS.pop(key_id, None)


def verify_policy(
    policy: SignedPolicy,
    repo_identity_override: str | None = None,
) -> VerifyResult:
    """Verify a signed policy.

    Performs all validation checks:
    1. Signature verification
    2. License expiration
    3. Repository binding
    4. Evaluation period (Enforce only)

    Args:
        policy: The signed policy to verify
        repo_identity_override: Override repo detection (for testing)

    Returns:
        VerifyResult indicating success or failure reason
    """
    from specleft.license.canonical import canonical_payload
    from specleft.license.repo_identity import RepoIdentity, detect_repo_identity

    # 1. Signature verification
    key_id = policy.signature.key_id
    if key_id not in TRUSTED_KEYS:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.INVALID_SIGNATURE,
            message=f"Unknown key: {key_id}",
        )

    public_key_b64 = TRUSTED_KEYS[key_id]
    if not public_key_b64:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.INVALID_SIGNATURE,
            message=f"Key not configured: {key_id}",
        )

    try:
        pub_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)

        payload = canonical_payload(
            policy.policy_type.value,
            policy.license.model_dump(),
            policy.rules.model_dump(),
        )

        sig = base64.b64decode(policy.signature.value)
        public_key.verify(sig, payload)
    except InvalidSignature:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.INVALID_SIGNATURE,
            message="Signature verification failed",
        )
    except Exception as e:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.INVALID_SIGNATURE,
            message=str(e),
        )

    # 2. License expiration
    if policy.license.expires_at < date.today():
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.EXPIRED,
            message=f"License expired {policy.license.expires_at}. "
            "Renew at https://specleft.dev/renew",
        )

    # 3. Repository binding
    if repo_identity_override:
        # Parse override as owner/repo
        parts = repo_identity_override.split("/")
        repo = RepoIdentity(owner=parts[0], name=parts[1]) if len(parts) == 2 else None
    else:
        repo = detect_repo_identity()

    if repo is None:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.REPO_DETECTION_FAILED,
            message="Cannot detect repository. Ensure git remote 'origin' exists.",
        )

    if not repo.matches(policy.license.licensed_to):
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.REPO_MISMATCH,
            message=f"License for '{policy.license.licensed_to}', "
            f"current repo is '{repo.canonical}'",
        )

    # 4. Evaluation period (Enforce only)
    if policy.license.evaluation and date.today() > policy.license.evaluation.ends_at:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.EVALUATION_EXPIRED,
            message=f"Evaluation ended {policy.license.evaluation.ends_at}",
        )

    return VerifyResult(valid=True)
