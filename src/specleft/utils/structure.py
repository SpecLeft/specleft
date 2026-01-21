"""Feature structure detection utilities.

Detects whether the features directory uses single-file or nested layout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import click

LayoutType = Literal["single-file", "nested", "mixed", "empty"]

# Track if warning has been shown in this process to avoid repetition
_nested_warning_shown = False


def reset_nested_warning_state() -> None:
    """Reset the nested structure warning state.

    Used primarily for testing to ensure each test can see the warning.
    """
    global _nested_warning_shown
    _nested_warning_shown = False


def detect_features_layout(features_dir: Path) -> LayoutType:
    """Detect the layout type of the features directory.

    Returns:
        - "single-file": Features are defined as `features/<feature>.md` files directly
        - "nested": Features use `features/<feature>/<story>/scenario.md` directories
        - "mixed": Both layouts detected (may need migration)
        - "empty": No feature files found
    """
    if not features_dir.exists():
        return "empty"

    # Look for single-file features (*.md files directly in features/)
    single_file_features = list(features_dir.glob("*.md"))

    # Look for nested structure indicators (_feature.md or _story.md files)
    nested_indicators = list(features_dir.rglob("_feature.md")) + list(
        features_dir.rglob("_story.md")
    )

    has_single_file = len(single_file_features) > 0
    has_nested = len(nested_indicators) > 0

    if has_single_file and has_nested:
        return "mixed"
    if has_single_file:
        return "single-file"
    if has_nested:
        return "nested"
    return "empty"


def is_nested_structure(features_dir: Path) -> bool:
    """Check if the features directory uses deeply nested structure.

    Returns True if _feature.md or _story.md files are found,
    indicating the legacy nested layout.
    """
    if not features_dir.exists():
        return False

    # Check for _feature.md or _story.md files
    has_feature_meta = any(features_dir.rglob("_feature.md"))
    has_story_meta = any(features_dir.rglob("_story.md"))

    return has_feature_meta or has_story_meta


def get_feature_file_path(features_dir: Path, feature_id: str) -> Path | None:
    """Get the path to a feature's source file.

    For single-file layout: features/<feature_id>.md
    For nested layout: features/<feature_id>/_feature.md

    Returns None if neither exists.
    """
    # Try single-file first
    single_file = features_dir / f"{feature_id}.md"
    if single_file.exists():
        return single_file

    # Try nested layout
    nested_file = features_dir / feature_id / "_feature.md"
    if nested_file.exists():
        return nested_file

    return None


def warn_if_nested_structure(features_dir: Path, *, force: bool = False) -> None:
    """Emit a gentle warning if deeply nested feature structure is detected.

    The warning is shown at most once per process to avoid noise,
    unless force=True is passed.

    Args:
        features_dir: Path to the features directory
        force: If True, show warning even if already shown
    """
    global _nested_warning_shown

    if _nested_warning_shown and not force:
        return

    if not is_nested_structure(features_dir):
        return

    _nested_warning_shown = True
    click.secho(
        "Note: Detected nested feature structure (_feature.md/_story.md files).",
        fg="yellow",
    )
    click.echo(
        "      Consider using single-file features (features/<feature>.md) for better"
    )
    click.echo("      agent compatibility. See: https://specleft.dev/docs")
    click.echo()
