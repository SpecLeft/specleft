# Feature Spec: Discovery language registry and file indexing

## Purpose
Add shared discovery infrastructure for Issue #125: centralized parser abstraction and one-pass filesystem indexing.

## User Stories

### Story 1: Shared language detection and parsing
**Scenario:** As a discovery miner, I need a single abstraction to detect and parse language files.
**Given** a project file path
**When** I call `LanguageRegistry().detect_language(path)`
**Then** it should map supported extensions to a `SupportedLanguage` enum value and return `None` for unsupported files.

**Scenario:** As a discovery miner, I need resilient parsing.
**Given** a supported file path and `LanguageRegistry`
**When** parsing succeeds
**Then** `parse(path)` returns `(root_node, detected_language)`.
**And when parse fails or content is corrupt
**Then** `parse(path)` returns `None` without raising.

### Story 2: Shared file indexing
**Scenario:** As a discovery pipeline, I need to avoid repeated filesystem walks.
**Given** a `FileIndex` built for the repository
**Then** miners can query `files_by_language`, `files_by_extension`, `files_matching`, and `files_under`.

**Scenario:** As a pipeline maintainer, I need noisy directories excluded consistently.
**Given** directories in `DEFAULT_EXCLUDE_DIRS`
**Then** those paths are never returned by index lookups.

### Story 3: Project language signal
**Scenario:** As downstream planning logic, I need a low-cost language signal.
**Given** a populated `FileIndex`
**When** calling `detect_project_languages(index)`
**Then** it returns detected languages above the ratio threshold.

## Acceptance Criteria
- Language abstraction returns `SupportedLanguage` members for `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` and `None` otherwise.
- Grammar/parser handling is cached and does not recreate parser objects per call.
- `FileIndex` builds once per root and exposes query helpers used by miners.
- Tests cover registry parsing, caching behavior, index filtering, and language detection thresholding.
- Feature spec is updated to document the new discovery layer behavior for issue #125.
