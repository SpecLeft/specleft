"""Access helpers to avoid import cycles with CLI entrypoint."""

from __future__ import annotations


def get_cli():
    from specleft.cli.main import cli

    return cli
