# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""SKILL.md integrity helpers."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from specleft.templates.skill_template import get_skill_content

IntegrityStatus = Literal["pass", "modified", "outdated"]
INTEGRITY_PASS: Final[IntegrityStatus] = "pass"
INTEGRITY_MODIFIED: Final[IntegrityStatus] = "modified"
INTEGRITY_OUTDATED: Final[IntegrityStatus] = "outdated"

SKILL_FILE_PATH = Path(".specleft/SKILL.md")
SKILL_HASH_PATH = Path(".specleft/SKILL.md.sha256")

_READ_ONLY_MODE = 0o444
_WRITE_MODE = 0o644
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_METACHARACTERS = ("&&", "||", ";", "|", ">", "<", "$(", "`")
_BACKTICK_COMMAND = re.compile(r"`([^`\n]+)`")


def skill_template_hash() -> str:
    """Return SHA-256 hash for the canonical SKILL template."""
    return _sha256_hex(get_skill_content())


def _sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _set_read_only(path: Path) -> None:
    try:
        os.chmod(path, _READ_ONLY_MODE)
    except OSError:
        return


def _set_writeable(path: Path) -> None:
    try:
        os.chmod(path, _WRITE_MODE)
    except OSError:
        return


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _set_writeable(path)
    path.write_text(content)
    _set_read_only(path)


def _read_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        raw = path.read_text().strip().split()
    except OSError:
        return None
    if not raw:
        return None
    value = raw[0].lower()
    if not _SHA256_PATTERN.fullmatch(value):
        return None
    return value


def _extract_specleft_commands(content: str) -> list[str]:
    commands: list[str] = []
    for match in _BACKTICK_COMMAND.findall(content):
        command = match.strip()
        if command.startswith("specleft "):
            commands.append(command)
    return commands


def _commands_are_simple(commands: list[str]) -> bool:
    if not commands:
        return False
    for command in commands:
        if any(token in command for token in _METACHARACTERS):
            return False
    return True


@dataclass
class SkillSyncResult:
    """Outcome for skill file synchronization."""

    created: list[str]
    updated: list[str]
    skipped: list[str]
    warnings: list[str]
    skill_file_hash: str

    def to_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "skill_file_hash": self.skill_file_hash,
        }


@dataclass
class SkillIntegrityResult:
    """Structured integrity verification result for SKILL.md."""

    skill_file: str
    checksum_file: str
    expected_hash: str | None
    actual_hash: str | None
    current_template_hash: str
    integrity: IntegrityStatus
    commands_simple: bool
    message: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "skill_file": self.skill_file,
            "checksum_file": self.checksum_file,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "current_template_hash": self.current_template_hash,
            "commands_simple": self.commands_simple,
            "integrity": self.integrity,
        }
        if self.message:
            payload["message"] = self.message
        return payload


def sync_skill_files(*, overwrite_existing: bool) -> SkillSyncResult:
    """Ensure SKILL.md and checksum file exist and are consistent."""
    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    canonical_content = get_skill_content()
    canonical_hash = _sha256_hex(canonical_content)
    skill_path = SKILL_FILE_PATH
    hash_path = SKILL_HASH_PATH

    skill_exists = skill_path.exists()
    if not skill_exists:
        _write_file(skill_path, canonical_content)
        created.append(str(skill_path))
        skill_hash = canonical_hash
    elif overwrite_existing:
        current_content = skill_path.read_text()
        if current_content != canonical_content:
            _write_file(skill_path, canonical_content)
            updated.append(str(skill_path))
        else:
            skipped.append(str(skill_path))
        skill_hash = canonical_hash
    else:
        skipped.append(str(skill_path))
        warnings.append("Warning: Skipped creation. Specleft SKILL.md exists already.")
        skill_hash = _sha256_hex(skill_path.read_text())

    hash_exists = hash_path.exists()
    hash_content = f"{skill_hash}\n"
    if not hash_exists:
        _write_file(hash_path, hash_content)
        created.append(str(hash_path))
    elif overwrite_existing:
        current_hash = hash_path.read_text()
        if current_hash != hash_content:
            _write_file(hash_path, hash_content)
            updated.append(str(hash_path))
        else:
            skipped.append(str(hash_path))
    else:
        skipped.append(str(hash_path))

    return SkillSyncResult(
        created=created,
        updated=updated,
        skipped=skipped,
        warnings=warnings,
        skill_file_hash=skill_hash,
    )


def verify_skill_integrity() -> SkillIntegrityResult:
    """Verify SKILL.md integrity and freshness."""
    skill_path = SKILL_FILE_PATH
    hash_path = SKILL_HASH_PATH
    template_hash = skill_template_hash()

    if not skill_path.exists():
        return SkillIntegrityResult(
            skill_file=str(skill_path),
            checksum_file=str(hash_path),
            expected_hash=_read_hash(hash_path),
            actual_hash=None,
            current_template_hash=template_hash,
            integrity=INTEGRITY_MODIFIED,
            commands_simple=False,
            message="Skill file is missing. Run `specleft skill update`.",
        )

    try:
        content = skill_path.read_text()
    except OSError:
        return SkillIntegrityResult(
            skill_file=str(skill_path),
            checksum_file=str(hash_path),
            expected_hash=_read_hash(hash_path),
            actual_hash=None,
            current_template_hash=template_hash,
            integrity=INTEGRITY_MODIFIED,
            commands_simple=False,
            message="Skill file cannot be read.",
        )

    actual_hash = _sha256_hex(content)
    expected_hash = _read_hash(hash_path)
    commands = _extract_specleft_commands(content)
    commands_simple = _commands_are_simple(commands)

    if expected_hash is None:
        return SkillIntegrityResult(
            skill_file=str(skill_path),
            checksum_file=str(hash_path),
            expected_hash=None,
            actual_hash=actual_hash,
            current_template_hash=template_hash,
            integrity=INTEGRITY_MODIFIED,
            commands_simple=commands_simple,
            message="Skill checksum file is missing or invalid. Run `specleft skill update`.",
        )

    if expected_hash != actual_hash:
        return SkillIntegrityResult(
            skill_file=str(skill_path),
            checksum_file=str(hash_path),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            current_template_hash=template_hash,
            integrity=INTEGRITY_MODIFIED,
            commands_simple=commands_simple,
            message=(
                "Skill file hash mismatch. Run `specleft skill update` to regenerate."
            ),
        )

    if not commands_simple:
        return SkillIntegrityResult(
            skill_file=str(skill_path),
            checksum_file=str(hash_path),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            current_template_hash=template_hash,
            integrity=INTEGRITY_MODIFIED,
            commands_simple=False,
            message=(
                "Skill file contains non-simple commands. This can indicate tampering."
            ),
        )

    if actual_hash != template_hash:
        return SkillIntegrityResult(
            skill_file=str(skill_path),
            checksum_file=str(hash_path),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            current_template_hash=template_hash,
            integrity=INTEGRITY_OUTDATED,
            commands_simple=True,
            message=(
                "Skill file is valid but outdated for this SpecLeft version. "
                "Run `specleft skill update`."
            ),
        )

    return SkillIntegrityResult(
        skill_file=str(skill_path),
        checksum_file=str(hash_path),
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        current_template_hash=template_hash,
        integrity=INTEGRITY_PASS,
        commands_simple=True,
    )
