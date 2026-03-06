# Feature Spec: Discovery pipeline foundations

## Purpose
Add shared discovery infrastructure for Issues #125 and #126: centralized parser abstraction, one-pass filesystem indexing, framework/config detection, and pipeline orchestration.

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
**Then** it returns detected languages above the ratio threshold, computed against total indexed files.

### Story 4: Discovery configuration and framework detection
**Scenario:** As a pipeline maintainer, I need project-local discovery settings.
**Given** a repository root with `[tool.specleft.discovery]` in `pyproject.toml`
**When** I load `DiscoveryConfig.from_pyproject(root)`
**Then** it should return configured values with safe defaults for missing/invalid fields.

**Scenario:** As a discovery pipeline, I need framework signals shared across miners.
**Given** a repository with `pytest` configuration and matching test files
**When** I call `FrameworkDetector().detect(root, file_index)`
**Then** it should return `{SupportedLanguage.PYTHON: ["pytest"]}`.

### Story 5: Orchestrated miner execution
**Scenario:** As a discovery pipeline, I need deterministic and resilient miner execution.
**Given** a set of registered miners
**When** one miner raises an exception
**Then** the pipeline records the error in that miner result and continues running the remaining miners.

**Scenario:** As a pipeline consumer, I need correct filtering semantics.
**Given** detected project languages and miner language scopes
**When** a miner has no overlap with detected languages
**Then** it is skipped silently.
**And** language-agnostic miners (`languages = frozenset()`) always run.

### Story 6: Default pipeline wiring
**Scenario:** As a command entrypoint (`specleft discover` / `specleft start`), I need one constructor that wires everything.
**Given** a project root
**When** I call `build_default_pipeline(root).run()`
**Then** a `DiscoveryReport` is returned with run duration, detected languages, miner results, and total item counts.

### Story 7: Shared docstring and JSDoc mining
**Scenario:** As a discovery pipeline, I need intent-rich text signals from source code comments.
**Given** configured source directories and a shared miner context
**When** `DocstringMiner` runs
**Then** it extracts Python module/class/function docstrings and TypeScript/JavaScript JSDoc comments into `DiscoveredItem(kind=DOCSTRING)` entries with typed `DocstringMeta`.

**Scenario:** As a pipeline maintainer, I need predictable mining scope and exclusions.
**Given** `source_dirs` in `DiscoveryConfig`
**When** `DocstringMiner` scans files
**Then** it reads only `ctx.file_index.files_under(*ctx.config.source_dirs)` and excludes test files (`test_*.py`, `*.test.ts`, etc.).

**Scenario:** As a spec generation pipeline, I need clean signal quality.
**Given** Python `__init__` docstrings
**When** the content is trivial (10 chars or fewer)
**Then** it is skipped and not emitted as a discovery item.

## Acceptance Criteria
- Language abstraction returns `SupportedLanguage` members for `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` and `None` otherwise.
- `LanguageRegistry().parse(path_to_py_file)` returns `(node, SupportedLanguage.PYTHON)` for valid Python input.
- `LanguageRegistry().parse(path_to_ts_file)` returns `(node, SupportedLanguage.TYPESCRIPT)` for valid TypeScript input.
- Corrupt file content returns `None` without raising.
- Grammar/parser handling is cached and does not recreate parser objects per call.
- `FileIndex` builds once per root and exposes query helpers used by miners.
- `detect_project_languages()` thresholds are applied against total indexed files, not only supported-language files.
- `DiscoveryConfig.from_pyproject(root)` loads custom settings from `[tool.specleft.discovery]`.
- `DiscoveryConfig.from_pyproject(root)` returns defaults when the section is missing.
- `FrameworkDetector.detect()` returns `{PYTHON: ["pytest"]}` on the SpecLeft repo.
- `FrameworkDetector` is called once per pipeline run and the result is shared through one `MinerContext`.
- `MinerContext` is constructed once and reused for all miner calls in that run.
- Per-miner exceptions are captured into `MinerResult.error`/`error_kind` without stopping the run.
- `DiscoveryReport.total_items` excludes items from miners that errored.
- Miners with no language overlap are skipped; language-agnostic miners always run.
- `register()` raises `ValueError` for duplicate `miner_id` UUIDs.
- `MinerResult.miner_id` and `miner_name` in output are populated from the miner instance.
- `build_default_pipeline(root).run()` returns a valid `DiscoveryReport` even when all registered miners fail.
- Integration on the SpecLeft repository produces `report.total_items > 0`.
- Tests cover config parsing, framework detection, pipeline registration/filtering/error isolation, and default pipeline integration.
- Feature spec is updated to document the discovery layer behavior introduced in issues #125 and #126.
- `DocstringMiner` emits module/class/function Python docstrings with `DocstringMeta` and `confidence=0.8`.
- TypeScript/JavaScript JSDoc comments immediately preceding declarations are emitted with the correct `SupportedLanguage`.
- Test files are excluded from docstring mining and configured `source_dirs` scope is respected.
- Trivial `__init__` docstrings (<=10 chars) are skipped.
