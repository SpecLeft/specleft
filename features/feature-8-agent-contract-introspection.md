# Feature: Feature 8: Agent Contract Introspection
priority: high

## Scenarios

### Scenario: Expose agent contract as structured JSON
- Given the repository is configured to use SpecLeft
- And an agent wants to understand how it is expected to interact with SpecLeft
- When `specleft contract --format json` is executed
- Then the command exits successfully
- And the output contains a single, canonical JSON object that includes contract clauses
- And the JSON schema is stable and machine-friendly

### Scenario: Verify repository complies with the agent contract
- Given the repository is configured according to the SpecLeft agent contract
- When `specleft contract test --format json` is executed
- Then the command exits with a zero status code
- And the output clearly states that the repository is compliant with the agent contract
- And no warnings or errors about missing required files or behaviours are reported

### Scenario: Clear failures when contract is violated
- Given the repository is missing one or more required elements of the agent contract
- When `specleft contract test` is executed
- Then the command exits with a non-zero status code
- And the output lists each failed check in a machine- and human-readable way:
- And no enforcement or CI behaviour is triggered beyond this explicit failure report
