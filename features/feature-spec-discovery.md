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

### Story 8: Python test-function mining
**Scenario:** As a discovery pipeline, I need to extract executable Python test signals.
**Given** Python test files selected from `FileIndex`
**When** `PythonTestMiner` runs
**Then** it emits `DiscoveredItem(kind=TEST_FUNCTION)` entries for top-level `test_` functions and `test_` methods under `Test*` classes.

**Scenario:** As a miner maintainer, I need framework and metadata fidelity.
**Given** framework detection from `ctx.frameworks[SupportedLanguage.PYTHON]`
**When** test items are emitted
**Then** metadata validates against `TestFunctionMeta`, including decorator names, docstring flags, class context, and parametrization detection.

**Scenario:** As a pipeline operator, I need resilient parse handling.
**Given** one malformed Python test file and one valid file
**When** `PythonTestMiner` executes
**Then** it reports `MinerErrorKind.PARSE_ERROR` for parse failures and still returns items from valid files.

### Story 9: TypeScript/JavaScript test-function mining
**Scenario:** As a discovery pipeline, I need to extract Jest/Vitest test signals from TS/JS test files.
**Given** TypeScript/JavaScript test files selected from `FileIndex`
**When** `TypeScriptTestMiner` runs
**Then** it emits `DiscoveredItem(kind=TEST_FUNCTION)` entries for `it(...)` and `test(...)` calls, including nested calls inside `describe(...)` blocks.

**Scenario:** As a miner maintainer, I need describe context and todo fidelity.
**Given** a nested `describe("Auth", () => { it.todo("pending test") })` block
**When** test items are emitted
**Then** metadata validates against `TestFunctionMeta` with `class_name="Auth"`, `call_style="it"`, and `has_todo=True`.

**Scenario:** As a pipeline operator, I need resilient parse handling.
**Given** one malformed TypeScript/JavaScript test file and one valid file
**When** `TypeScriptTestMiner` executes
**Then** it reports `MinerErrorKind.PARSE_ERROR` for parse failures and still returns items from valid files.

### Story 10: Python API route mining
**Scenario:** As a discovery pipeline, I need to extract Python API routes across major frameworks.
**Given** Python files selected from `ctx.file_index.files_by_language(SupportedLanguage.PYTHON)`
**When** `PythonRouteMiner` runs with `ctx.frameworks[SupportedLanguage.PYTHON] = ["fastapi"]`
**Then** it emits `DiscoveredItem(kind=API_ROUTE)` entries for decorated handlers with methods and paths.
**And** FastAPI `response_model` is captured in `ApiRouteMeta`.

**Scenario:** As a miner maintainer, I need Flask metadata fidelity.
**Given** a Flask route `@bp.route("/items", methods=["GET", "POST"])` and `@app.route("/health")`
**When** `PythonRouteMiner` emits items
**Then** metadata validates against `ApiRouteMeta` with `http_method=["GET", "POST"]` for the first route
**And** missing `methods` defaults to `["GET"]`.

**Scenario:** As a discovery pipeline, I need Django URL pattern support.
**Given** a module with `urlpatterns = [path(...), re_path(...)]`
**When** `PythonRouteMiner` runs with framework `django`
**Then** both `path()` and `re_path()` entries are emitted as API route items.

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
- `PythonTestMiner` reads candidate files from `ctx.file_index.files_matching("test_*.py", "*_test.py")` and does not walk the filesystem directly.
- `PythonTestMiner` uses precomputed frameworks from `ctx.frameworks[SupportedLanguage.PYTHON]` rather than re-detecting frameworks.
- Python test metadata validates against `TestFunctionMeta`, including `is_parametrized` and `class_name` values.
- Parse failures in individual test files set `MinerResult.error_kind=PARSE_ERROR` without aborting extraction from remaining files.
- `TypeScriptTestMiner` reads candidate files from `ctx.file_index.files_matching("*.test.ts", "*.spec.ts", "*.test.js", "*.spec.js", "*.test.tsx", "*.spec.tsx")` and does not walk the filesystem directly.
- `TypeScriptTestMiner` uses precomputed frameworks from `ctx.frameworks[SupportedLanguage.TYPESCRIPT]` / `ctx.frameworks[SupportedLanguage.JAVASCRIPT]` instead of re-detecting frameworks.
- TypeScript/JavaScript test metadata validates against `TestFunctionMeta`, including `call_style`, `has_todo`, and describe-block `class_name`.
- `.ts` test files emit `language=SupportedLanguage.TYPESCRIPT`; `.js` files emit `language=SupportedLanguage.JAVASCRIPT`.
- Confidence scoring is `0.9` for known framework + `.spec.` filename and `0.7` otherwise.
- `PythonRouteMiner` reads candidate files from `ctx.file_index.files_by_language(SupportedLanguage.PYTHON)` and does not walk the filesystem directly.
- `PythonRouteMiner` uses precomputed Python frameworks from `ctx.frameworks[SupportedLanguage.PYTHON]` and does not re-parse manifests.
- FastAPI fixtures with `GET`, `POST`, and `PATCH` decorators produce three API route items with correct methods and paths.
- Route metadata validates against `ApiRouteMeta`, including `response_model` for FastAPI and list-form `http_method` for Flask `methods=[...]`.
- Django `urlpatterns` entries using both `path()` and `re_path()` produce API route items.
- Missing Flask `methods` defaults to `["GET"]`.
