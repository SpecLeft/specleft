"""Pytest configuration for SpecLeft tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

# Enable the pytester fixture for testing pytest plugins
pytest_plugins = ["pytester"]


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture(autouse=True)
def reset_nested_warning_state():
    """Reset the nested structure warning state before each test.

    This ensures each test can independently verify warning behavior.
    """
    from specleft.utils.structure import reset_nested_warning_state

    reset_nested_warning_state()
    yield
    reset_nested_warning_state()
