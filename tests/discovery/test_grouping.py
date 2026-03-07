# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Tests for phase-2 feature grouping."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from specleft.discovery.grouping import group_items
from specleft.discovery.models import (
    ApiRouteMeta,
    DiscoveredItem,
    DocstringMeta,
    GitCommitMeta,
    ItemKind,
    SupportedLanguage,
    TestFunctionMeta,
)


def _test_item(name: str, file_path: Path) -> DiscoveredItem:
    return DiscoveredItem(
        kind=ItemKind.TEST_FUNCTION,
        name=name,
        file_path=file_path,
        line_number=1,
        language=SupportedLanguage.PYTHON,
        raw_text=None,
        metadata=TestFunctionMeta(framework="pytest").model_dump(),
        confidence=0.9,
    )


def _route_item(name: str, path: str, file_path: Path) -> DiscoveredItem:
    return DiscoveredItem(
        kind=ItemKind.API_ROUTE,
        name=name,
        file_path=file_path,
        line_number=1,
        language=SupportedLanguage.PYTHON,
        raw_text=None,
        metadata=ApiRouteMeta(
            http_method="GET",
            path=path,
            framework="fastapi",
        ).model_dump(),
        confidence=0.9,
    )


def _doc_item(name: str, file_path: Path) -> DiscoveredItem:
    return DiscoveredItem(
        kind=ItemKind.DOCSTRING,
        name=name,
        file_path=file_path,
        line_number=1,
        language=SupportedLanguage.PYTHON,
        raw_text=name,
        metadata=DocstringMeta(
            target_kind="module",
            target_name=file_path.stem,
            text=name,
        ).model_dump(),
        confidence=0.8,
    )


def _git_item(subject: str, file_prefixes: list[str]) -> DiscoveredItem:
    return DiscoveredItem(
        kind=ItemKind.GIT_COMMIT,
        name=subject,
        file_path=None,
        line_number=None,
        language=None,
        raw_text=None,
        metadata=GitCommitMeta(
            commit_hash="abc1234",
            subject=subject,
            changed_files=[f"{prefix}/file.py" for prefix in file_prefixes],
            file_prefixes=file_prefixes,
        ).model_dump(),
        confidence=0.5,
    )


def _feature_for_item(features: list[Any], item: DiscoveredItem) -> Any:
    return next(
        feature
        for feature in features
        if any(source is item for source in feature.source_items)
    )


def test_items_from_auth_directory_land_in_single_group() -> None:
    items = [
        _test_item(f"test_auth_case_{index}", Path(f"tests/auth/test_case_{index}.py"))
        for index in range(10)
    ]

    features = group_items(items)

    assert len(features) == 1
    assert features[0].feature_id == "authentication"
    assert len(features[0].source_items) == 10


def test_api_routes_group_by_first_path_segment() -> None:
    payment_get = _route_item(
        "GET /payments/{id}",
        "/payments/{id}",
        Path("src/api/payments.py"),
    )
    payment_post = _route_item(
        "POST /payments",
        "/payments",
        Path("src/api/payments_write.py"),
    )
    users_get = _route_item("GET /users/{id}", "/users/{id}", Path("src/api/users.py"))

    features = group_items([payment_get, payment_post, users_get])

    payment_feature = _feature_for_item(features, payment_get)
    assert payment_feature is _feature_for_item(features, payment_post)
    assert payment_feature.feature_id == "payments"
    assert _feature_for_item(features, users_get).feature_id == "users"


def test_every_item_is_assigned_exactly_once() -> None:
    auth_test = _test_item("test_auth_valid", Path("tests/auth/test_login.py"))
    auth_doc = _doc_item("Authentication module", Path("src/auth/service.py"))
    billing_route = _route_item("GET /billing", "/billing", Path("src/api/billing.py"))
    git_auth = _git_item("feat: auth hardening", ["tests/auth", "src/auth"])
    git_billing = _git_item("feat: billing endpoint", ["src/api/billing"])
    items = [auth_test, auth_doc, billing_route, git_auth, git_billing]

    features = group_items(items)
    assigned = [item for feature in features for item in feature.source_items]

    counts = Counter(id(item) for item in assigned)
    assert len(assigned) == len(items)
    assert len(counts) == len(items)
    assert all(count == 1 for count in counts.values())


def test_git_items_merge_into_nearest_existing_group() -> None:
    auth_test = _test_item("test_auth_login", Path("tests/auth/test_login.py"))
    billing_test = _test_item(
        "test_invoice_paid", Path("tests/billing/test_invoice.py")
    )
    git_auth = _git_item("feat: improve auth", ["tests/auth", "src/auth"])
    git_billing = _git_item("feat: tighten invoices", ["tests/billing"])

    features = group_items([auth_test, billing_test, git_auth, git_billing])

    assert len(features) == 2
    assert git_auth in _feature_for_item(features, auth_test).source_items
    assert git_billing in _feature_for_item(features, billing_test).source_items


def test_grouping_uses_typed_meta_for_api_and_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_item = _route_item("GET /users", "/users", Path("src/api/users.py"))
    git_item = _git_item("feat: users", ["src/api/users"])

    calls = {"api": 0, "git": 0}
    original = DiscoveredItem.typed_meta

    def _spy(self: DiscoveredItem) -> Any:
        meta = original(self)
        if self.kind is ItemKind.API_ROUTE:
            calls["api"] += 1
        if self.kind is ItemKind.GIT_COMMIT:
            calls["git"] += 1
        return meta

    monkeypatch.setattr(DiscoveredItem, "typed_meta", _spy)

    group_items([api_item, git_item])

    assert calls["api"] >= 1
    assert calls["git"] >= 1


def test_single_item_group_is_valid() -> None:
    solo = _doc_item("single docstring", Path("src/single/service.py"))

    features = group_items([solo])

    assert len(features) == 1
    assert len(features[0].source_items) == 1


def test_unmatched_git_items_form_group_when_three_share_prefix() -> None:
    git_a = _git_item("feat: payments workflow", ["payments/core"])
    git_b = _git_item("fix: payments retries", ["payments/jobs"])
    git_c = _git_item("refactor: payments ledger", ["payments/ledger"])

    features = group_items([git_a, git_b, git_c])

    assert len(features) == 1
    assert features[0].feature_id == "payments"
    assert len(features[0].source_items) == 3


def test_confidence_scores_include_kind_docstring_and_git_bonuses() -> None:
    auth_test = _test_item("test_auth_login", Path("tests/auth/test_login.py"))
    auth_doc = _doc_item("Authentication service", Path("src/auth/service.py"))
    auth_git = _git_item("feat: auth service", ["tests/auth", "src/auth"])

    feature = _feature_for_item(group_items([auth_test, auth_doc, auth_git]), auth_test)

    assert feature.confidence == pytest.approx(0.9)
