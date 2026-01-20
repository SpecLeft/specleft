"""Access helpers to avoid import cycles with CLI entrypoint."""

from __future__ import annotations

import click


def get_cli() -> click.Group:
    from specleft.cli.main import cli

    return cli
