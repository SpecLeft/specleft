"""Shared pytest fixtures for acceptance tests.

All fixtures are organized in the fixtures/ subpackage by feature.
This conftest.py re-exports them for pytest discovery.
"""

# Re-export dataclasses for test file imports
from fixtures.common import (
    FeatureFiles,
    FeatureOnlyFiles,
    PrdFiles,
    acceptance_workspace,
)

# Feature 1: Planning Mode
from fixtures.feature_1 import (
    feature_1_prd_multi_feature,
    feature_1_prd_slug_test,
)

# Feature 2: Specification Format
from fixtures.feature_2 import (
    feature_2_metadata_variants,
    feature_2_minimal,
)

# Feature 3: Canonical JSON Output
from fixtures.feature_3 import (
    feature_3_canonical_json,
    feature_3_slugification,
)

# Feature 4: Status & Coverage Inspection
from fixtures.feature_4 import (
    feature_4_implemented,
    feature_4_multi_feature_filter,
    feature_4_unimplemented,
)

# Feature 5: Policy Enforcement
from fixtures.feature_5 import (
    feature_5_invalid_signature,
    feature_5_policy_satisfied,
    feature_5_policy_violation,
)

# Feature 6: CI Experience & Messaging
from fixtures.feature_6 import (
    feature_6_ci_failure,
    feature_6_doc_links,
)

# Feature 7: Autonomous Agent Test Execution
from fixtures.feature_7 import (
    feature_7_agent_implements,
    feature_7_coverage,
    feature_7_next_scenario,
    feature_7_skeleton,
)

# Feature 8: Agent Contract Introspection
from fixtures.feature_8 import (
    feature_8_contract,
    feature_8_contract_minimal,
    feature_8_contract_test,
)
from fixtures.feature_9 import feature_9_cli_authoring

__all__ = [
    # Common
    "FeatureFiles",
    "FeatureOnlyFiles",
    "PrdFiles",
    "acceptance_workspace",
    # Feature 1
    "feature_1_prd_multi_feature",
    "feature_1_prd_slug_test",
    # Feature 2
    "feature_2_minimal",
    "feature_2_metadata_variants",
    # Feature 3
    "feature_3_canonical_json",
    "feature_3_slugification",
    # Feature 4
    "feature_4_unimplemented",
    "feature_4_implemented",
    "feature_4_multi_feature_filter",
    # Feature 5
    "feature_5_policy_violation",
    "feature_5_policy_satisfied",
    "feature_5_invalid_signature",
    # Feature 6
    "feature_6_ci_failure",
    "feature_6_doc_links",
    # Feature 7
    "feature_7_next_scenario",
    "feature_7_skeleton",
    "feature_7_agent_implements",
    "feature_7_coverage",
    # Feature 8
    "feature_8_contract",
    "feature_8_contract_minimal",
    "feature_8_contract_test",
    # Feature 9
    "feature_9_cli_authoring",
]
