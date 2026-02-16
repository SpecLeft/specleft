# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""FastMCP server wiring for SpecLeft."""

from __future__ import annotations

from typing import Any

from specleft.commands.constants import CLI_VERSION
from specleft.mcp.init_tool import run_specleft_init
from specleft.mcp.payloads import (
    build_mcp_contract_payload,
    build_mcp_guide_payload,
    build_mcp_status_payload,
)


def _require_fastmcp() -> tuple[type[Any], type[Any]]:
    try:
        from fastmcp import FastMCP
        from fastmcp.resources import FunctionResource
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised in CLI error path
        raise RuntimeError(
            "FastMCP is not installed. Install with `pip install specleft[mcp]`."
        ) from exc

    return FastMCP, FunctionResource


def build_mcp_server() -> Any:
    """Create the SpecLeft MCP server instance."""
    FastMCP, FunctionResource = _require_fastmcp()

    mcp = FastMCP(
        name="SpecLeft",
        version=CLI_VERSION,
        website_url="https://specleft.dev",
        instructions=(
            "Use contract, guide, and status resources before mutating project files. "
            "Use specleft_init only when status reports initialised=false."
        ),
    )

    mcp.add_resource(
        FunctionResource(
            uri="specleft://contract",
            name="SpecLeft Agent Contract",
            description="Safety and determinism guarantees for this SpecLeft installation.",
            mime_type="application/json",
            fn=build_mcp_contract_payload,
        )
    )

    mcp.add_resource(
        FunctionResource(
            uri="specleft://guide",
            name="SpecLeft Workflow Guide",
            description="Workflow and spec format guidance for agents using SpecLeft.",
            mime_type="application/json",
            fn=build_mcp_guide_payload,
        )
    )

    mcp.add_resource(
        FunctionResource(
            uri="specleft://status",
            name="SpecLeft Project Status",
            description="Project-level implementation and coverage summary.",
            mime_type="application/json",
            fn=build_mcp_status_payload,
        )
    )

    @mcp.tool(  # type: ignore[misc]
        name="specleft_init",
        description=(
            "Initialise a SpecLeft project, run health checks, and generate .specleft/SKILL.md."
        ),
    )
    def specleft_init(
        example: bool = False,
        blank: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return run_specleft_init(example=example, blank=blank, dry_run=dry_run)

    return mcp


def run_mcp_server() -> None:
    """Run the SpecLeft MCP server over stdio."""
    server = build_mcp_server()
    server.run(transport="stdio", show_banner=False)
