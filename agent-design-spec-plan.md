# SpecLeft — Agent-Oriented Design Specification Plan

This document defines a **clear, phased design and implementation plan** intended to be used as a **prompt reference for an LLM coding agent**.

The goal is to optimise SpecLeft for **organic agent adoption**, particularly around **PRD → feature planning**, while remaining compatible with existing SpecLeft concepts (scenarios, priorities, enforcement).

---

## Design Goals

1. Make **feature files (`features/<feature>.md`)** the default and lowest-friction planning unit.
2. Allow agents to externalise intent **before code or tests exist**.
3. Keep all enforcement and execution downstream of planning.
4. Avoid forcing governance or taxonomy decisions early.
5. Ensure all metadata is:
   - optional in markdown
   - always represented (nullable) in CLI JSON output

---

## Conceptual Model (Simplified)

```text
PRD
  ↓
features/
  feature-a.md
  feature-b.md
    (scenarios live here)
  ↓
tests (optional, later)
  ↓
CI enforcement (optional, later)
```

Stories are treated as **optional semantic groupings** (headings only), not structural units.

---

## Phase 1 — Planning Mode Foundations

### Purpose

Introduce a **planning-only workflow** that allows agents to safely convert PRDs into feature specifications without triggering tests, enforcement, or CI failures.

---

### New CLI Command

```bash
specleft plan
specleft plan --from <prd.md>
```

#### Behaviour

- Default: reads `prd.md` from the repository root.
- If `--from` is provided, reads the specified file.
- If no PRD is found:
  - emits a clear warning
  - suggests expected locations (e.g. `prd.md`, `docs/prd.md`)
- Never generates tests or modifies code.
- Only creates or updates files under `features/`.

---

### Agent Heuristics (Non-Executable Guidance)

An LLM agent using this command should:

- Treat the PRD as **incomplete intent**
- Surface assumptions explicitly
- Prefer fewer, clearer features over exhaustive breakdowns
- Stop after feature generation and await review

---

## Phase 2 — Feature File Generation

### Default Mapping Rule

> **One feature = one markdown file**  
> **Scenarios live inside the feature file**

This is the **canonical and recommended mapping**, optimised for agent behaviour.

---

### Canonical Feature Template (Docs + CLI Help)

```markdown
# Feature: User Authentication

## Scenarios

### Scenario: Valid credentials
priority: critical

- Given …
- When …
- Then …

### Scenario: Invalid password
priority: high

- Given …
- When …
- Then …

---
confidence: low
source: prd.md
assumptions:
  - email/password login
open_questions:
  - password complexity rules?
tags:
  - auth
  - security
owner: dev-team
component: identity
---
```

---

### Template Design Rules

- **Required**
  - Feature title
  - At least one scenario
  - `priority` per scenario
- **Optional**
  - Metadata block (`---`)
  - All metadata fields within it
- Metadata appears **after scenarios** to reduce friction.
- Stories may appear as headings but are not required.

---

## Phase 3 — CLI Parsing & JSON Representation

### Lenient Parsing Rules

- Absence of metadata is valid.
- Missing optional fields are interpreted as `null`.
- Feature identity is inferred from filename unless explicitly overridden later.

---

### Canonical JSON Output Shape

All CLI commands that emit JSON (`plan`, `status`, `coverage`, etc.) must include the following fields, even if null:

```json
{
  "feature_id": "user-authentication",
  "title": "User Authentication",
  "confidence": null,
  "source": null,
  "assumptions": null,
  "open_questions": null,
  "tags": null,
  "owner": null,
  "component": null,
  "scenarios": [
    {
      "id": "valid-credentials",
      "priority": "critical",
      "status": "unimplemented"
    }
  ]
}
```

This ensures:
- schema stability for agents
- predictable downstream tooling
- no pressure to invent metadata

---

## Phase 4 — CLI Nudging (Non-Enforcing)

### Examples of Nudges

- `specleft init` scaffolds:
  ```text
  features/
    example-feature.md
  ```

- `specleft status` groups output by feature file.
- `specleft test skeleton` generates one test module per feature file.
- Gentle warnings when deeply nested feature structures are detected.

No command should fail due to structure alone.

---

## Phase 5 — Transition to Execution (Out of Scope for Plan Mode)

After planning is complete and reviewed:

- Agents may generate skeleton tests from scenarios.
- Implementation proceeds incrementally.
- Enforcement (if enabled) relies on priorities already declared.

Plan mode itself **never enforces**.

---

## Explicit Non-Goals

This plan intentionally does NOT include:

- Story-level files or directories
- Mandatory schemas for metadata
- Automatic test or code generation in plan mode
- Enforcement during planning
- Opinionated PRD formats

---

## Summary for LLM Coding Agents

When using SpecLeft:

1. Read the PRD.
2. Run `specleft plan`.
3. Create `features/<feature>.md` files using the canonical template.
4. Surface assumptions and open questions.
5. Stop and request review before implementing.

> **Specs are a planning buffer, not a contract.**

---

## End of Specification
