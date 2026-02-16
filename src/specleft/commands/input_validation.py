# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Input validation callbacks for security-sensitive CLI parameters."""

from __future__ import annotations

import re

import click

_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHELL_METACHARACTERS = set("$`|;&><(){}[]!\\'\"")


def validate_id_parameter(
    _ctx: click.Context | None,
    _param: click.Parameter | None,
    value: str | None,
) -> str | None:
    """Enforce strict kebab-case IDs for CLI parameters."""
    if value is None:
        return value
    if not _ID_PATTERN.fullmatch(value):
        raise click.BadParameter(
            f"Must be kebab-case alphanumeric (got: {value!r}). "
            "Characters allowed: a-z, 0-9, hyphens."
        )
    return value


def validate_id_parameter_multiple(
    _ctx: click.Context | None,
    _param: click.Parameter | None,
    value: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """Enforce strict kebab-case IDs for repeatable CLI parameters."""
    if value is None:
        return value
    for item in value:
        validate_id_parameter(None, None, item)
    return value


def validate_text_parameter(
    _ctx: click.Context | None,
    _param: click.Parameter | None,
    value: str | None,
) -> str | None:
    """Reject shell metacharacters in freeform text CLI parameters."""
    if value is None:
        return value
    dangerous = sorted(char for char in set(value) if char in _SHELL_METACHARACTERS)
    if dangerous:
        rendered = ", ".join(repr(char) for char in dangerous)
        raise click.BadParameter(
            f"Contains disallowed characters: {rendered}. "
            "Avoid shell metacharacters in text inputs."
        )
    return value
