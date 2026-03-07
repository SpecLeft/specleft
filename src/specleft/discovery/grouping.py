# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 SpecLeft Contributors

"""Phase-2 grouping logic for discovery items."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slugify import slugify

from specleft.discovery.models import (
    ApiRouteMeta,
    DiscoveredItem,
    DraftFeature,
    DraftScenario,
    GitCommitMeta,
    ItemKind,
)
from specleft.schema import SpecStep, StepType

_GENERIC_PATH_SEGMENTS = frozenset(
    {
        "app",
        "core",
        "features",
        "lib",
        "specleft",
        "specs",
        "src",
        "test",
        "tests",
    }
)
_ABBREVIATION_EXPANSIONS: dict[str, str] = {
    "auth": "authentication",
    "cfg": "configuration",
    "config": "configuration",
    "mgmt": "management",
    "msg": "messaging",
    "notif": "notifications",
}
_NAME_PREFIXES = (
    "test_",
    "test ",
    "it_",
    "it ",
    "should_",
    "should ",
)


@dataclass
class _Group:
    key: str
    items: list[DiscoveredItem] = field(default_factory=list)
    path_signals: set[str] = field(default_factory=set)


def group_items(items: list[DiscoveredItem]) -> list[DraftFeature]:
    """Group discovered items into draft features using deterministic heuristics."""
    segment_counts = _segment_counts(items)
    groups: dict[str, _Group] = {}
    git_items: list[DiscoveredItem] = []

    for item in items:
        if item.kind is ItemKind.GIT_COMMIT:
            git_items.append(item)
            continue

        key = _group_key_for_item(item, segment_counts)
        _append_to_group(groups, key, item)

    _assign_git_items(groups, git_items)

    features: list[DraftFeature] = []
    for group in groups.values():
        if not group.items:
            continue
        features.append(_group_to_feature(group))
    return features


def _segment_counts(items: list[DiscoveredItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if item.file_path is None:
            continue
        for part in item.file_path.parent.parts:
            token = _normalize_token(part)
            if not token:
                continue
            counts[token] = counts.get(token, 0) + 1
    return counts


def _group_key_for_item(item: DiscoveredItem, segment_counts: dict[str, int]) -> str:
    path_key = _path_group_key(item.file_path, segment_counts)

    if item.kind is ItemKind.API_ROUTE:
        api_key = _api_group_key(item)
        if api_key:
            return api_key

    if path_key:
        return path_key

    name_key = _name_group_key(item.name)
    if name_key:
        return name_key

    if item.file_path is not None:
        fallback = _normalize_token(item.file_path.stem)
        if fallback:
            return fallback

    return "misc"


def _path_group_key(
    file_path: Path | None, segment_counts: dict[str, int]
) -> str | None:
    if file_path is None:
        return None

    parent_parts = [part for part in file_path.parent.parts if part not in {"", "."}]
    if not parent_parts:
        return None

    preferred = _deepest_shared_specific_segment(parent_parts, segment_counts)
    if preferred:
        return preferred

    for part in reversed(parent_parts):
        token = _normalize_token(part)
        if token and token not in _GENERIC_PATH_SEGMENTS:
            return token
    return None


def _deepest_shared_specific_segment(
    parent_parts: list[str], segment_counts: dict[str, int]
) -> str | None:
    for part in reversed(parent_parts):
        token = _normalize_token(part)
        if not token or token in _GENERIC_PATH_SEGMENTS:
            continue
        if segment_counts.get(token, 0) >= 2:
            return token
    return None


def _api_group_key(item: DiscoveredItem) -> str | None:
    meta = item.typed_meta()
    if not isinstance(meta, ApiRouteMeta):
        return None

    segments = [segment for segment in meta.path.split("/") if segment]
    for segment in segments:
        if segment.startswith("{") and segment.endswith("}"):
            continue
        token = _normalize_token(segment)
        if token:
            return token
    return "root"


def _name_group_key(name: str) -> str | None:
    normalized = name.strip().lower()
    for prefix in _NAME_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break

    tokens = [token for token in slugify(normalized, separator=" ").split() if token]
    while tokens and tokens[0] in {"and", "but", "given", "then", "when"}:
        tokens = tokens[1:]

    if not tokens:
        return None
    return tokens[0]


def _assign_git_items(
    groups: dict[str, _Group], git_items: list[DiscoveredItem]
) -> None:
    pending: dict[str, list[DiscoveredItem]] = {}

    for git_item in git_items:
        best_key = _best_group_key_for_git(groups, git_item)
        if best_key is not None:
            _append_to_group(groups, best_key, git_item)
            continue

        bucket_key = _git_bucket_key(git_item)
        pending.setdefault(bucket_key, []).append(git_item)

    for bucket_key, bucket_items in pending.items():
        if len(bucket_items) >= 3:
            for git_item in bucket_items:
                _append_to_group(groups, bucket_key, git_item)
            continue

        for git_item in bucket_items:
            _append_to_group(
                groups, _fallback_group_for_git(groups, git_item), git_item
            )


def _best_group_key_for_git(
    groups: dict[str, _Group], git_item: DiscoveredItem
) -> str | None:
    if not groups:
        return None

    meta = git_item.typed_meta()
    if not isinstance(meta, GitCommitMeta):
        return None

    best_key: str | None = None
    best_score = 0
    best_size = -1

    for key, group in groups.items():
        score = _overlap_score(meta.file_prefixes, group.path_signals)
        size = len(group.items)
        if score == 0:
            continue
        if score > best_score or (score == best_score and size > best_size):
            best_key = key
            best_score = score
            best_size = size

    return best_key


def _overlap_score(prefixes: list[str], signals: set[str]) -> int:
    score = 0
    for prefix in prefixes:
        prefix_signal = prefix.strip("/")
        if not prefix_signal:
            continue
        for signal in signals:
            if signal.startswith(prefix_signal) or prefix_signal.startswith(signal):
                score += 1
    return score


def _git_bucket_key(git_item: DiscoveredItem) -> str:
    meta = git_item.typed_meta()
    if isinstance(meta, GitCommitMeta) and meta.file_prefixes:
        first = meta.file_prefixes[0].split("/", maxsplit=1)[0]
        token = _normalize_token(first)
        if token:
            return token

    fallback = _name_group_key(git_item.name)
    return fallback or "misc"


def _fallback_group_for_git(groups: dict[str, _Group], git_item: DiscoveredItem) -> str:
    named_key = _name_group_key(git_item.name)
    if named_key and named_key in groups:
        return named_key

    if groups:
        return max(groups.items(), key=lambda pair: len(pair[1].items))[0]
    return "misc"


def _append_to_group(groups: dict[str, _Group], key: str, item: DiscoveredItem) -> None:
    group = groups.get(key)
    if group is None:
        group = _Group(key=key)
        groups[key] = group

    group.items.append(item)
    group.path_signals.update(_path_signals_for_item(item))


def _path_signals_for_item(item: DiscoveredItem) -> set[str]:
    if item.file_path is None:
        return set()

    as_posix = item.file_path.as_posix().strip("/")
    if not as_posix:
        return set()

    parts = as_posix.split("/")
    signals: set[str] = set()
    for index in range(1, len(parts) + 1):
        signals.add("/".join(parts[:index]))
    parent = item.file_path.parent.as_posix()
    if parent != ".":
        signals.add(parent)
    return signals


def _group_to_feature(group: _Group) -> DraftFeature:
    expanded_label = _expand_abbreviations(group.key)
    feature_id = slugify(expanded_label, lowercase=True)
    if not feature_id:
        feature_id = "misc"

    feature_name = expanded_label.title()
    scenarios = [
        _item_to_scenario(item, index) for index, item in enumerate(group.items)
    ]

    return DraftFeature(
        feature_id=feature_id,
        name=feature_name,
        scenarios=scenarios,
        source_items=list(group.items),
        confidence=_group_confidence(group.items),
    )


def _item_to_scenario(item: DiscoveredItem, index: int) -> DraftScenario:
    label = _scenario_label(item)
    title = slugify(label, lowercase=True) or f"scenario-{index + 1}"

    return DraftScenario(
        title=title,
        steps=[
            SpecStep(type=StepType.GIVEN, description=f"context for {label}"),
            SpecStep(type=StepType.WHEN, description=f"action for {label}"),
            SpecStep(type=StepType.THEN, description=f"outcome for {label}"),
        ],
        source_items=[item],
    )


def _scenario_label(item: DiscoveredItem) -> str:
    if item.kind is ItemKind.API_ROUTE:
        meta = item.typed_meta()
        if isinstance(meta, ApiRouteMeta):
            method = (
                ", ".join(meta.http_method)
                if isinstance(meta.http_method, list)
                else meta.http_method
            )
            return f"{method} {meta.path}".strip()

    candidate = item.name.replace("_", " ").replace("-", " ").strip()
    for prefix in ("test ", "it "):
        if candidate.lower().startswith(prefix):
            candidate = candidate[len(prefix) :]
            break
    return candidate or "scenario"


def _group_confidence(items: list[DiscoveredItem]) -> float:
    score = 0.5
    if len({item.kind for item in items}) >= 2:
        score += 0.2
    if any(item.kind is ItemKind.DOCSTRING for item in items):
        score += 0.1
    if any(item.kind is ItemKind.GIT_COMMIT for item in items):
        score += 0.1
    return min(score, 1.0)


def _expand_abbreviations(key: str) -> str:
    tokens = [token for token in slugify(key, separator=" ").split() if token]
    if not tokens:
        return "misc"

    expanded = [_ABBREVIATION_EXPANSIONS.get(token, token) for token in tokens]
    return " ".join(expanded)


def _normalize_token(value: str) -> str:
    return slugify(value, lowercase=True)
