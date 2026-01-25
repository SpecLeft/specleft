# Feature: Feature 1: Planning Mode

priority: critical

## Scenarios

### Scenario: Generate feature files from PRD
priority: critical
- Given a repository contains a `prd.md`
- When `specleft plan` is executed
- Then feature files are created under `features/`
- And each feature maps to a user-visible capability
- And no code or test files are modified

### Scenario: Derive feature filenames from PRD headings
priority: critical
- Given the PRD contains multiple feature sections
- When feature files are generated
- Then filenames are derived as slugs from feature titles
- And existing feature files are not overwritten

### Scenario: Handle missing PRD gracefully

- Given no PRD file exists in the repository
- When `specleft plan` is executed
- Then a clear warning is emitted
- And no feature files are created
