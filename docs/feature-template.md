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