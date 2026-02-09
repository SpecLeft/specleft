# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Shared messaging helpers for CLI output."""

from __future__ import annotations

import click

DEFAULT_DOCUMENTATION_URL = "https://specleft.dev/docs"
DEFAULT_SUPPORT_URL = "https://specleft.dev/contact"


def print_support_footer(
    *,
    documentation_url: str | None = DEFAULT_DOCUMENTATION_URL,
    support_url: str = DEFAULT_SUPPORT_URL,
    err: bool = True,
) -> None:
    if documentation_url:
        click.echo(f"Documentation: {documentation_url}", err=err)
    click.echo(f"Support: {support_url}", err=err)
