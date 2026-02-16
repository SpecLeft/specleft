"""Security tests for MCP init workflow."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path

import pytest

from specleft.mcp.init_tool import (
    SecurityError,
    ensure_safe_write_target,
    run_specleft_init,
)
from specleft.utils.skill_integrity import verify_skill_integrity


def test_ensure_safe_write_target_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(SecurityError, match="Path traversal"):
        ensure_safe_write_target(Path("../outside.txt"), workspace=tmp_path)


def test_init_rejects_symlink_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)

    (tmp_path / ".specleft").mkdir(parents=True)
    (tmp_path / ".specleft" / "specs").symlink_to(outside)

    payload = run_specleft_init(blank=True)

    assert payload["success"] is False
    assert "symlink" in str(payload["error"]).lower()


def test_init_generates_verified_read_only_skill_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    payload = run_specleft_init(blank=True)
    assert payload["success"] is True

    skill_file = tmp_path / ".specleft" / "SKILL.md"
    checksum_file = tmp_path / ".specleft" / "SKILL.md.sha256"

    skill_hash = hashlib.sha256(skill_file.read_bytes()).hexdigest()
    assert checksum_file.read_text().strip() == skill_hash

    mode = stat.S_IMODE(skill_file.stat().st_mode)
    assert mode == 0o444

    integrity = verify_skill_integrity().to_payload()
    assert integrity["commands_simple"] is True
    assert integrity["integrity"] in {"pass", "outdated"}


def test_init_does_not_regenerate_modified_skill_file_without_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    skill_file = tmp_path / ".specleft" / "SKILL.md"
    checksum_file = tmp_path / ".specleft" / "SKILL.md.sha256"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text("# tampered\n")
    checksum_file.write_text(("a" * 64) + "\n")

    payload = run_specleft_init(blank=True)

    assert payload["success"] is True
    assert payload["skill_file_regenerated"] is False
    warnings = payload.get("warnings", [])
    assert isinstance(warnings, list)
    assert warnings
    assert "checksum mismatch" in warnings[0].lower()
    assert skill_file.read_text() == "# tampered\n"
