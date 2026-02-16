"""Integration tests for the SpecLeft MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specleft.commands.status import build_status_entries, build_status_json
from specleft import specleft
from specleft.mcp.payloads import build_mcp_status_payload
from specleft.mcp.server import build_mcp_server
from specleft.validator import load_specs_directory
from tests.helpers.specs import create_feature_specs


@pytest.fixture
def mcp_client() -> Any:
    """Return an in-memory FastMCP client for the SpecLeft server."""
    fastmcp = pytest.importorskip("fastmcp")
    return fastmcp.Client(build_mcp_server())


def _resource_json(result: list[Any]) -> dict[str, object]:
    text = result[0].text
    return json.loads(text)


@pytest.mark.asyncio
async def test_server_lists_three_resources(mcp_client: Any) -> None:
    async with mcp_client:
        resources = await mcp_client.list_resources()

    uris = {str(resource.uri) for resource in resources}
    assert uris == {
        "specleft://contract",
        "specleft://guide",
        "specleft://status",
    }


@pytest.mark.asyncio
async def test_server_lists_one_tool(mcp_client: Any) -> None:
    async with mcp_client:
        tools = await mcp_client.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "specleft_init"


@pytest.mark.asyncio
async def test_contract_and_guide_resources_are_json(mcp_client: Any) -> None:
    async with mcp_client:
        contract_result = await mcp_client.read_resource("specleft://contract")
        guide_result = await mcp_client.read_resource("specleft://guide")

    contract_payload = _resource_json(contract_result)
    guide_payload = _resource_json(guide_result)

    assert contract_payload["contract_version"]
    assert "guarantees" in contract_payload
    guarantees = contract_payload["guarantees"]
    assert guarantees["cli_rejects_shell_metacharacters"] is True
    assert guarantees["init_refuses_symlinks"] is True
    assert guarantees["skill_file_integrity_check"] is True
    assert guarantees["no_network_access"] is True
    assert guarantees["no_telemetry"] is True
    assert guide_payload["workflow"]
    assert "skill_file" in guide_payload


@pytest.mark.asyncio
@specleft(
    feature_id="feature-mcp-server",
    scenario_id="agent-discovery-flow-uses-resources-and-init-tool",
)
async def test_agent_discovery_flow_uses_resources_and_init_tool(
    mcp_client: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with specleft.step("Given an agent connects to the SpecLeft MCP server"):
        pass

    with specleft.step("When the agent reads contract, guide, and status resources"):
        async with mcp_client:
            contract_result = await mcp_client.read_resource("specleft://contract")
            guide_result = await mcp_client.read_resource("specleft://guide")
            status_result = await mcp_client.read_resource("specleft://status")

            contract_payload = _resource_json(contract_result)
            guide_payload = _resource_json(guide_result)
            status_payload = _resource_json(status_result)

    with specleft.step("Then status reports initialised=false before setup"):
        assert "guarantees" in contract_payload
        assert "workflow" in guide_payload
        assert status_payload["initialised"] is False

    with specleft.step("And the agent calls specleft_init to bootstrap the project"):
        async with mcp_client:
            init_result = await mcp_client.call_tool("specleft_init", {"example": True})
            init_payload = json.loads(init_result.content[0].text)

    with specleft.step("Then initialisation succeeds and creates the skill file"):
        assert init_payload["success"] is True
        assert (tmp_path / ".specleft" / "SKILL.md").exists()

    with specleft.step("And status reflects initialised project state"):
        async with mcp_client:
            status_after = await mcp_client.read_resource("specleft://status")
        status_after_payload = _resource_json(status_after)
        assert status_after_payload["initialised"] is True
        assert status_after_payload["features"] >= 1


@pytest.mark.asyncio
async def test_init_tool_dry_run_writes_nothing(
    mcp_client: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}

    async with mcp_client:
        result = await mcp_client.call_tool("specleft_init", {"dry_run": True})
    payload = json.loads(result.content[0].text)

    after = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}

    assert payload["success"] is True
    assert payload["dry_run"] is True
    assert before == after


@pytest.mark.asyncio
async def test_init_tool_is_idempotent(
    mcp_client: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    async with mcp_client:
        first = await mcp_client.call_tool("specleft_init", {"blank": True})
        second = await mcp_client.call_tool("specleft_init", {"blank": True})

    first_payload = json.loads(first.content[0].text)
    second_payload = json.loads(second.content[0].text)

    assert first_payload["success"] is True
    assert second_payload["success"] is True


def test_status_payload_verbose_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    create_feature_specs(
        tmp_path,
        feature_id="feature-auth",
        story_id="login",
        scenario_id="user-can-login",
    )

    payload = build_mcp_status_payload(verbose=True)
    config = load_specs_directory(Path(".specleft/specs"))
    entries = build_status_entries(config, Path("tests"))
    expected = build_status_json(
        entries,
        include_execution_time=False,
        verbose=True,
    )
    assert isinstance(expected, dict)

    payload_without_timestamp = dict(payload)
    expected_without_timestamp = dict(expected)
    payload_without_timestamp.pop("timestamp", None)
    expected_without_timestamp.pop("timestamp", None)

    assert payload_without_timestamp == expected_without_timestamp
