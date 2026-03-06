# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""TypeScript framework detection rules and policies."""

from specleft.discovery.frameworks.typescript.policies import TypeScriptFrameworkPolicy
from specleft.discovery.frameworks.typescript.rules import JestRule, VitestRule

__all__ = ["TypeScriptFrameworkPolicy", "JestRule", "VitestRule"]
