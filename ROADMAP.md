# SpecLeft Roadmap

## Current (v0.1.0 - Foundation)
- ✅ Spec-defined test decoration
- ✅ Step-by-step test tracing
- ✅ Skeleton test generation from JSON specs
- ✅ Basic HTML test reporting
- ✅ Pytest plugin integration

## Planned (v0.2.0 - Workflow Optimisations)
- 🪜 **Add Features and Scenarios Command** — Incrementally add features and scenarios via the CLI for quick enhancement of a plan
- 🔖 **Enhanced PRD parsing** - More flexible converting of prd.md in to feature units.
- 📜 **Logged Feature Changes** - Keep a historical trace of features and scenarios added to the project.
- 📖 **Agent Guide** - Provide clarity and guidance for agents to know how to best proceed in scenarios such as: refactoring, cleanup, regression bugs, features and scenarios.
- 🔄 **Async test handling** - Async tests are now supported with @specleft decorator and step context manager
- 🧪 **Test Stubs** - Create empty test containers as an alternate to test skeletons.


## Future (v0.3.0+)
- 🎯 **Test Plan Orchestration** — Manage, chain and orchestrate test execution based on dependencies, priorities, and conditional logic. Build dynamic test workflows.
- 🤖 **AI-Generated Tests** — Let SpecLeft generate test implementations from your feature specs using LLMs. Reduce boilerplate even further.
- 🔗 **CI/CD Integration** — Native integrations with GitHub Actions, GitLab CI, Jenkins, and other CI platforms for seamless reporting and result tracking.
- 🌐 **Assisted Discovery** — Discover existing functionality from a project and turn them in to feature definitions.
- 🔌 **3rd Party Plugin for Syncing Features** - Sync feature specifications with external platforms like Jira and Azure DevOps to maintain alignment between requirements and automated tests.
- 🔔 **Notifications** - Get real-time updates on test execution and results via Slack, Microsoft Teams, Discord, and other messaging platforms.
- 📊 **Test Collector** — Aggregate and correlate test results across multiple runs, environments, and branches. Track trends, identify flaky tests, and spot patterns in failures.
- 📈 **Enhanced Reporting** — Interactive dashboards with drill-down capabilities, failure analysis, and historical trends.
- 🎚️ **SpecLeft CLI Filters** — First-class test selection via `--specleft-tag/priority/feature/scenario` flags and pytest config defaults.

## Community & Contributions

Have ideas? Found a use case we should support? Open an issue or start a discussion—we'd love to hear from you!
