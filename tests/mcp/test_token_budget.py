"""Token usage tests for MCP payloads and declarations."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from specleft.mcp.payloads import build_mcp_contract_payload, build_mcp_guide_payload
from specleft.mcp.server import build_mcp_server


def _count_tokens(payload: str) -> int:
    tiktoken = pytest.importorskip("tiktoken")
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as exc:  # pragma: no cover - depends on network/cache state
        pytest.skip(f"Unable to load cl100k_base encoding: {exc}")
    return len(encoding.encode(payload))


def _compact_json(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def test_contract_payload_within_budget() -> None:
    tokens = _count_tokens(_compact_json(build_mcp_contract_payload()))
    assert tokens <= 120


def test_guide_payload_within_budget() -> None:
    tokens = _count_tokens(_compact_json(build_mcp_guide_payload()))
    assert tokens <= 320


@pytest.mark.asyncio
async def test_declarations_within_budget() -> None:
    fastmcp = pytest.importorskip("fastmcp")
    client_factory: Callable[[Any], Any] = fastmcp.Client
    client = client_factory(build_mcp_server())

    async with client:
        resources = await client.list_resources()
        tools = await client.list_tools()

    declaration_payload = {
        "resources": [
            {
                "uri": str(resource.uri),
                "name": resource.name,
                "description": resource.description,
            }
            for resource in resources
        ],
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ],
    }

    tokens = _count_tokens(_compact_json(declaration_payload))
    assert tokens <= 220
