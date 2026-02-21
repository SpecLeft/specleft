"""Standalone MCP stdio E2E smoke test for installed SpecLeft wheels.

This script intentionally avoids pytest so CI can execute it directly after
building and installing the wheel artifact.
"""

from __future__ import annotations

import json
import selectors
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class JsonRpcResponse:
    """A parsed JSON-RPC response payload."""

    payload: dict[str, Any]

    @property
    def message_id(self) -> int | str | None:
        return self.payload.get("id")


def _encode_message(message: dict[str, Any]) -> bytes:
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return body + b"\n"


def _send_message(proc: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    stdin = proc.stdin
    if stdin is None:
        raise RuntimeError("MCP process stdin is unavailable.")
    stdin.write(_encode_message(message))
    stdin.flush()


def _send_request(
    proc: subprocess.Popen[bytes],
    *,
    method: str,
    msg_id: int,
    params: dict[str, Any] | None = None,
) -> None:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        message["params"] = params
    _send_message(proc, message)


def _send_notification(
    proc: subprocess.Popen[bytes],
    *,
    method: str,
    params: dict[str, Any] | None = None,
) -> None:
    message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        message["params"] = params
    _send_message(proc, message)


def _read_frame(
    proc: subprocess.Popen[bytes],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    stdout = proc.stdout
    if stdout is None:
        raise RuntimeError("MCP process stdout is unavailable.")

    selector = selectors.DefaultSelector()
    selector.register(stdout, selectors.EVENT_READ)

    buffer = bytearray()
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        events = selector.select(timeout=0.1)
        if not events:
            if proc.poll() is not None:
                return None
            continue

        chunk = stdout.read1(4096)
        if not chunk:
            continue
        buffer.extend(chunk)

        while b"\n" in buffer:
            line, _, remainder = bytes(buffer).partition(b"\n")
            buffer = bytearray(remainder)
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                # Skip non-JSON lines (for example, server log output).
                continue
            if isinstance(payload, dict):
                return payload

    return None


def _read_response_for_id(
    proc: subprocess.Popen[bytes],
    *,
    msg_id: int,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> JsonRpcResponse | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        remaining = max(deadline - time.monotonic(), 0.1)
        payload = _read_frame(proc, timeout_seconds=remaining)
        if payload is None:
            return None
        response = JsonRpcResponse(payload=payload)
        if response.message_id == msg_id:
            return response
    return None


def _terminate_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def _stderr_tail(proc: subprocess.Popen[bytes]) -> str:
    if proc.poll() is None:
        return ""
    stderr = proc.stderr
    if stderr is None:
        return ""
    data = stderr.read().decode("utf-8", errors="replace").strip()
    return data


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "specleft.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    failures: list[str] = []
    stderr_hint = ""

    try:
        _send_request(
            proc,
            method="initialize",
            msg_id=1,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "specleft-mcp-e2e", "version": "1.0.0"},
            },
        )
        response = _read_response_for_id(proc, msg_id=1)
        if response is None or "result" not in response.payload:
            failures.append("initialize did not return a valid result")
        else:
            server_info = response.payload["result"].get("serverInfo", {})
            if not isinstance(server_info, dict) or not server_info.get("name"):
                failures.append("initialize result missing serverInfo.name")
            else:
                print("[PASS] initialize handshake")

        _send_notification(proc, method="notifications/initialized")

        _send_request(proc, method="resources/list", msg_id=2)
        response = _read_response_for_id(proc, msg_id=2)
        if response is None or "result" not in response.payload:
            failures.append("resources/list did not return a valid result")
        else:
            resources = response.payload["result"].get("resources", [])
            uris = {
                item.get("uri")
                for item in resources
                if isinstance(item, dict) and isinstance(item.get("uri"), str)
            }
            expected_uris = {"specleft://contract", "specleft://guide", "specleft://status"}
            if uris != expected_uris:
                failures.append(f"resources/list returned {sorted(uris)} expected {sorted(expected_uris)}")
            else:
                print("[PASS] resources/list returns 3 expected resources")

        _send_request(proc, method="tools/list", msg_id=3)
        response = _read_response_for_id(proc, msg_id=3)
        if response is None or "result" not in response.payload:
            failures.append("tools/list did not return a valid result")
        else:
            tools = response.payload["result"].get("tools", [])
            if len(tools) != 1:
                failures.append(f"tools/list returned {len(tools)} tools expected 1")
            elif not isinstance(tools[0], dict) or tools[0].get("name") != "specleft_init":
                failures.append(f"tools/list returned unexpected tool payload: {tools}")
            else:
                print("[PASS] tools/list returns specleft_init")

        _send_request(proc, method="resources/read", msg_id=4, params={"uri": "specleft://contract"})
        response = _read_response_for_id(proc, msg_id=4)
        if response is None or "result" not in response.payload:
            failures.append("resources/read for specleft://contract did not return a valid result")
        else:
            contents = response.payload["result"].get("contents", [])
            first_item = contents[0] if contents else {}
            text = first_item.get("text") if isinstance(first_item, dict) else None
            if not isinstance(text, str):
                failures.append("contract resource returned no text payload")
            else:
                contract_payload = json.loads(text)
                if "guarantees" not in contract_payload:
                    failures.append("contract payload missing guarantees")
                else:
                    print("[PASS] contract resource is readable JSON")

    finally:
        _terminate_process(proc)
        stderr_hint = _stderr_tail(proc)

    if failures:
        print(f"[FAIL] MCP stdio E2E checks failed ({len(failures)}):")
        for failure in failures:
            print(f"  - {failure}")
        if stderr_hint:
            print(f"  - process stderr: {stderr_hint}")
        return 1

    print("[PASS] all MCP stdio E2E checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
