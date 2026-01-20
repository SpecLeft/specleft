"""Filesystem helper utilities for tests."""

from __future__ import annotations

import textwrap
from pathlib import Path


def write_file(path: Path, content: str) -> None:
    """Write dedented content to a file.

    Args:
        path: The file path to write to.
        content: The content to write (will be dedented and stripped).
    """
    path.write_text(textwrap.dedent(content).strip())
