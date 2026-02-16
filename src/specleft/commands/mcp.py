# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""MCP command."""

from __future__ import annotations

import click

from specleft.utils.messaging import print_support_footer


@click.command("mcp")
def mcp() -> None:
    """Run the SpecLeft MCP server over stdio."""
    try:
        from specleft.mcp.server import run_mcp_server

        run_mcp_server()
    except RuntimeError as exc:
        click.secho(str(exc), fg="red", err=True)
        print_support_footer()
        raise SystemExit(1) from exc
