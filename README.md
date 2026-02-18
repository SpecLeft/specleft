![SpecLeft social preview](https://raw.githubusercontent.com/SpecLeft/specleft/main/.github/assets/specleft-social-preview.png)

# SpecLeft: Planning-First Specs for pytest

![Spec coverage](https://raw.githubusercontent.com/SpecLeft/specleft/main/.github/assets/spec-coverage-badge.svg)

SpecLeft keeps feature intent and test coverage aligned by turning plans into version-controlled specs, then generating pytest test skeletons from those specs.

- Write feature specs in Markdown: `.specleft/specs/*.md`
- Validate specs and track coverage by feature/scenario
- Generate skeleton tests (once), then humans own the code
- Designed to be safe for AI agents and CI: no writes without confirmation, JSON output available

SpecLeft works with pytest. It does not replace your test runner or reinterpret existing tests.

Website: [specleft.dev](https://specleft.dev)

## Quick Start

Two paths, depending on how you want to start. See [docs/cli-reference.md](https://github.com/SpecLeft/specleft/blob/main/docs/cli-reference.md) for full command details.

### Setup (run once per repo)

```bash
pip install specleft
specleft init
```

### Path 1: Add one feature (and generate a test skeleton)

Create a feature, then add a scenario and generate a skeleton test for it:

```bash
# Create the feature spec
specleft features add --id AUTHENTICATION --title "Authentication" --format json

# Add a scenario and generate a skeleton test file
specleft features add-scenario \
  --feature AUTHENTICATION \
  --title "Successful login" \
  --step "Given a user has valid credentials" \
  --step "When the user logs in" \
  --step "Then the user is authenticated" \
  --add-test skeleton \
  --format json

# Show traceability / coverage status
specleft status
```

### Path 2: Bulk-generate feature specs from a PRD

Create `prd.md` describing intended behavior. 

**Recommended**: Update `.specleft/templates/prd-template.yml` to customize how your PRD sections map to features/scenarios.

Then run:

```bash

# Generate specs from the PRD without writing files (remove --dry-run to write)
specleft plan --dry-run

# Validate the generated specs
specleft features validate

# Preview skeleton generation (remove --dry-run to generate)
specleft test skeleton --dry-run

# Confirm and generate skeleton tests
specleft test skeleton

# Show traceability / coverage status
specleft status

# Run your tests with pytest as normal
pytest
```

That flow converts `prd.md` into `.specleft/specs/*.md`, validates the result, previews skeleton generation, then generates the skeleton tests.

## When to Use SpecLeft

- Use SpecLeft when you have acceptance criteria (features/scenarios) and want traceable coverage.
- Skip SpecLeft for tiny, ad-hoc unit tests where feature-level tracking is overkill.

## What It Is (and Is Not)

- It is a pytest plugin plus a CLI for planning, spec validation, TDD workflows, .
- It is not a BDD framework, a separate test runner, or a SaaS test management product.

## Why Not Conventional BDD

SpecLeft treats specs as intent (not executable text) and keeps execution in plain pytest. For the longer comparison, see [docs/why-not-bdd.md](https://github.com/SpecLeft/specleft/blob/main/docs/why-not-bdd.md).

## AI Agents

If you are integrating SpecLeft into an agent loop, start here:

```bash
specleft doctor --format json
specleft contract --format json
specleft features stats --format json
```

- Integration guidance: [AI_AGENTS.md](https://github.com/SpecLeft/specleft/blob/main/AI_AGENTS.md)
- Safety and invariants: [docs/agent-contract.md](https://github.com/SpecLeft/specleft/blob/main/docs/agent-contract.md)
- CLI reference: [docs/cli-reference.md](https://github.com/SpecLeft/specleft/blob/main/docs/cli-reference.md)

## MCP Server Setup

SpecLeft includes an MCP server so agents can read specs, track status, and generate test scaffolding without leaving the conversation.

See [GET_STARTED.md](https://github.com/SpecLeft/specleft/blob/main/GET_STARTED.md) for setup details.

## Docs

- Getting started: [GET_STARTED.md](https://github.com/SpecLeft/specleft/blob/main/GET_STARTED.md)
- Workflow notes: [WORKFLOW.md](https://github.com/SpecLeft/specleft/blob/main/WORKFLOW.md)
- Roadmap: [ROADMAP.md](https://github.com/SpecLeft/specleft/blob/main/ROADMAP.md)

---

## License

SpecLeft is **dual-licensed**:

- **Open Core (Apache 2.0)** for the core engine and non-commercial modules
- **Commercial License** for enforcement, signing, and license logic

Open-source terms are in [LICENSE-OPEN](https://github.com/SpecLeft/specleft/blob/main/LICENSE-OPEN).
Commercial terms are in [LICENSE-COMMERCIAL](https://github.com/SpecLeft/specleft/blob/main/LICENSE-COMMERCIAL).

Commercial features (e.g., `specleft enforce`) require a valid license policy file.
See [NOTICE.md](https://github.com/SpecLeft/specleft/blob/main/NOTICE.md) for licensing scope details.
