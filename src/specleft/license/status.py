# NOTICE: Commercial License
# See LICENSE-COMMERCIAL for details.
# Copyright (c) 2026 SpecLeft.

"""License status and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click
import yaml

from specleft.license.repo_identity import detect_repo_identity
from specleft.specleft_signing.schema import SignedPolicy
from specleft.specleft_signing.verify import VerifyFailure, VerifyResult, verify_policy

DEFAULT_LICENSE_PATH = Path(".specleft/policies/policy.yml")
LICENSE_DIR = Path(".specleft/policies")


@dataclass
class LicenseValidation:
    """Result of license file validation."""

    valid: bool
    policy: SignedPolicy | None
    verify_result: VerifyResult | None
    path: Path | None
    message: str | None = None


def _load_policy(path: Path) -> SignedPolicy | None:
    try:
        content = yaml.safe_load(path.read_text())
        return SignedPolicy.model_validate(content)
    except FileNotFoundError:
        return None
    except yaml.YAMLError as exc:
        click.echo(f"Error: Invalid YAML in policy file: {exc}", err=True)
        return None
    except Exception as exc:  # noqa: BLE001 - display any model error
        click.echo(f"Error: {exc}", err=True)
        return None


def _verify_repo_binding(policy: SignedPolicy) -> VerifyResult:
    repo = detect_repo_identity()
    if repo is None:
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.REPO_MISMATCH,
            message="Cannot detect repository. Ensure git remote 'origin' exists.",
        )
    if not repo.matches(policy.license.licensed_to):
        return VerifyResult(
            valid=False,
            failure=VerifyFailure.REPO_MISMATCH,
            message=(
                f"License for '{policy.license.licensed_to}', "
                f"current repo is '{repo.canonical}'"
            ),
        )
    return VerifyResult(valid=True)


def _candidate_paths(preferred: Path | None) -> list[Path]:
    if preferred is not None:
        return [preferred]

    if DEFAULT_LICENSE_PATH.exists():
        return [DEFAULT_LICENSE_PATH]

    if not LICENSE_DIR.exists():
        return []

    candidates = sorted(LICENSE_DIR.glob("*.yml"))
    candidates.extend(sorted(LICENSE_DIR.glob("*.yaml")))
    return candidates


def resolve_license(preferred: Path | None = None) -> LicenseValidation:
    """Resolve and validate the most appropriate license file."""
    candidates = _candidate_paths(preferred)
    last_result: VerifyResult | None = None
    last_policy: SignedPolicy | None = None
    last_path: Path | None = None

    for candidate in candidates:
        if not candidate.exists():
            continue
        policy = _load_policy(candidate)
        last_policy = policy
        last_path = candidate
        if policy is None:
            continue
        result = verify_policy(policy)
        if result.valid:
            repo_result = _verify_repo_binding(policy)
            if repo_result.valid:
                return LicenseValidation(
                    valid=True,
                    policy=policy,
                    verify_result=repo_result,
                    path=candidate,
                )
            result = repo_result
        last_result = result

    return LicenseValidation(
        valid=False,
        policy=last_policy,
        verify_result=last_result,
        path=last_path,
        message=last_result.message if last_result else None,
    )
