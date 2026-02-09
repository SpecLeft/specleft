# Feature: Feature 7: Autonomous Agent Test Execution
priority: high

## Scenarios

### Scenario: Identify the next required scenario to implement
- Given feature scenarios exist under `.specleft/specs/`
- And some scenarios are unimplemented
- When `specleft next --format json` is executed
- Then the next unimplemented scenario is identified deterministically
- And the output includes: 'feature_id', 'scenario_id', 'priority', 'current_status'


### Scenario: Generate test skeleton for a scenario
- Given an unimplemented scenario exists
- When `specleft test skeleton -o ./tmp/` is executed
- Then a test stub is generated in to `./tmp` directory
- And the test contains placeholders for Given / When / Then
- And no application logic is implemented automatically

### Scenario: Agent implements behaviour to satisfy the test
- Given a generated test skeleton exists
- When an agent implements application code
- And the test passes locally
- Then `specleft status --implemented --format json` the scenario status as implemented

### Scenario: Coverage reflects scenario implementation
- Given some scenarios are implemented and others are not
- When `specleft coverage --format json` is executed
- Then coverage is reported per feature and per scenario
- And implemented vs unimplemented scenarios are clearly distinguished
