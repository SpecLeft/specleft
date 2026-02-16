# Feature: MCP Server for Agent Discovery
priority: high

## Scenarios

### Scenario: Expose exactly three resources and one tool
- Given the SpecLeft MCP server is running
- When an MCP client lists server resources and tools
- Then the server exposes resources `specleft://contract`, `specleft://guide`, and `specleft://status`
- And the server exposes exactly one tool named `specleft_init`

### Scenario: Contract and guide resources return machine-readable JSON
- Given the SpecLeft MCP server is running
- When an MCP client reads `specleft://contract` and `specleft://guide`
- Then both resources return valid JSON payloads
- And the contract payload includes safety and determinism guarantees
- And the guide payload includes workflow steps and skill file guidance

### Scenario: Status resource signals uninitialised project
- Given an empty workspace with no SpecLeft setup
- When an MCP client reads `specleft://status`
- Then the payload includes `initialised: false`
- And feature and scenario counts are zero

### Scenario: specleft_init bootstraps project safely
- Given an empty workspace with write permissions
- When an MCP client calls the `specleft_init` tool
- Then the tool runs health checks before writing files
- And it creates `.specleft/specs`, `.specleft/policies`, and `.specleft/SKILL.md`
- And repeated calls are idempotent

### Scenario: Agent discovery flow uses resources and init tool
- Given an agent connects to the MCP server
- When the agent reads contract, guide, and status resources
- And status reports `initialised: false`
- And the agent calls `specleft_init`
- Then the workspace is initialised
- And a subsequent status read reports `initialised: true`
