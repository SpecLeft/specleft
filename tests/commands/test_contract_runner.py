"""Tests for contract runner helpers."""

from __future__ import annotations

from specleft.commands.contracts.runner import emit_contract_check
from specleft.commands.contracts.types import ContractCheckResult


def test_emit_contract_check_delegates_to_table(capsys) -> None:
    check = ContractCheckResult(category="safety", name="dry_run", status="pass")
    emit_contract_check(check, verbose=False)
    output = capsys.readouterr().out
    assert "✓ Safety: dry run" in output
