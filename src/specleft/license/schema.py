"""License schema definitions for policy validation.

Pydantic models for parsing and validating signed policy files.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PolicyType(str, Enum):
    """Policy tier types."""

    CORE = "core"
    ENFORCE = "enforce"


class EvaluationPeriod(BaseModel):
    """Fixed evaluation window (set at purchase time)."""

    starts_at: date
    ends_at: date

    @model_validator(mode="after")
    def validate_dates(self) -> EvaluationPeriod:
        """Ensure ends_at is after starts_at."""
        if self.ends_at < self.starts_at:
            raise ValueError("Evaluation ends_at must be after starts_at")
        return self


class CoverageRules(BaseModel):
    """Coverage threshold configuration (Enforce tier only)."""

    threshold_percent: int = Field(default=100, ge=0, le=100)
    fail_below: bool = True


class PriorityRule(BaseModel):
    """Rule for a specific priority level."""

    must_be_implemented: bool = False


class PolicyRules(BaseModel):
    """Rules block containing priority and coverage configuration."""

    priorities: dict[str, PriorityRule] = Field(default_factory=dict)
    coverage: CoverageRules | None = None  # Enforce only


class LicenseInfo(BaseModel):
    """License information block."""

    license_id: str = Field(pattern=r"^lic_[a-zA-Z0-9]{8,}$")
    licensed_to: str  # "owner/repo" or "owner/*"
    issued_at: date
    expires_at: date
    evaluation: EvaluationPeriod | None = None  # Enforce only
    derived_from: str | None = None  # Downgraded Core only

    @model_validator(mode="after")
    def validate_dates(self) -> LicenseInfo:
        """Ensure expires_at is after issued_at."""
        if self.expires_at < self.issued_at:
            raise ValueError("License expires_at must be after issued_at")
        return self


class SignatureBlock(BaseModel):
    """Cryptographic signature block."""

    algorithm: Literal["ed25519"] = "ed25519"
    key_id: str
    value: str  # Base64 encoded signature


class SignedPolicy(BaseModel):
    """Complete signed policy document."""

    policy_id: str
    policy_version: str = Field(pattern=r"^\d+\.\d+$")
    policy_type: PolicyType
    license: LicenseInfo
    rules: PolicyRules
    signature: SignatureBlock

    @model_validator(mode="after")
    def validate_type_rules(self) -> SignedPolicy:
        """Validate type-specific constraints.

        - Core policies cannot have coverage rules or evaluation periods
        - Enforce policies must have coverage rules
        """
        if self.policy_type == PolicyType.CORE:
            if self.rules.coverage is not None:
                raise ValueError("Core policies cannot have coverage rules")
            if self.license.evaluation is not None:
                raise ValueError("Core policies cannot have evaluation periods")
        if self.policy_type == PolicyType.ENFORCE and self.rules.coverage is None:
            raise ValueError("Enforce policies must have coverage rules")
        return self
