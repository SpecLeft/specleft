# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Entrypoint for ``python -m specleft.mcp``."""

from __future__ import annotations

import sys

from specleft.mcp.server import run_mcp_server


def main() -> None:
    try:
        run_mcp_server()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
