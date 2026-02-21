# MCP Testing

This document covers end-to-end testing for the SpecLeft MCP server as an installed package.

## Goal

Catch packaging/runtime issues that in-memory MCP tests do not catch:

- broken `python -m specleft.mcp` entrypoint
- missing runtime dependencies in built wheel
- import-time failures in installed package
- stdio protocol regressions

## Local E2E Smoke Test

Run:

```bash
make test-mcp-e2e
```

This target:

1. Builds wheel artifacts (`python -m build`)
2. Builds a clean container from `test-mcp.Dockerfile`
3. Installs the wheel with MCP extras (`[mcp]`)
4. Runs `tests/mcp/e2e_stdio.py`

## What `tests/mcp/e2e_stdio.py` Verifies

- MCP initialize handshake succeeds
- `resources/list` returns exactly:
  - `specleft://contract`
  - `specleft://guide`
  - `specleft://status`
- `tools/list` returns exactly one tool: `specleft_init`
- `resources/read` for `specleft://contract` returns JSON with `guarantees`
- Exit code is `0` on success, `1` on any failure

## CI Workflow

Workflow file:

- `.github/workflows/test-mcp-e2e.yml`

Trigger:

- Pull requests that touch MCP server code, E2E script, or `pyproject.toml`

Matrix:

- Python 3.10, 3.11, 3.12

The workflow builds the wheel, installs it with `[mcp]`, and executes `python tests/mcp/e2e_stdio.py`.

## Notes

- The current MCP server transport behavior is newline-delimited JSON-RPC over stdio; the E2E script validates this behavior directly.
- Unit/integration MCP tests in `tests/mcp/test_server.py` and `tests/mcp/test_security.py` should still run alongside this smoke test.
