# SpecLeft Roadmap

## Current (v0.4.0 - Foundation)
- ✅ Spec-defined test decoration
- ✅ Step-by-step test tracing
- ✅ Skeleton test generation from JSON specs
- ✅ Basic HTML test reporting
- ✅ Pytest plugin integration
- 🪜 **Add Features and Scenarios Command** — Incrementally add features and scenarios via the CLI for quick enhancement of a plan
- 🔖 **Enhanced PRD parsing** - More flexible converting of prd.md in to feature units.
- 📜 **Logged Feature Changes** - Keep a historical trace of features and scenarios added to the project. Provides externalised memory to agents
- 📖 **Agent Guide** - Provide clarity and guidance for agents to know how to best proceed in scenarios such as: refactoring, cleanup, regression bugs, features and scenarios.
- 🔄 **Async test handling** - Async tests are now supported with @specleft decorator and step context manager
- 🧪 **Test Stubs** - Create empty test containers as an alternate to test skeletons.
- 👾 **MCP Server** - A SpecLeft MCP server to smoother integration with AI agents.
- ✍️ **Agent Skills** - Integrated agent skills for more autonomous planning and test generation.


## Future (v0.5.0 and beyond)
- 🎚️ **SpecLeft CLI Filters** — First-class test selection via `--specleft-tag/priority/feature/scenario` flags and pytest config defaults.
- 🤖 **AI-Generated Tests** — Let SpecLeft generate test implementations from your feature specs using LLMs. SpecLeft provides richer context and understanding for more robust behaviour testing capability. Reduce boilerplate even further.

## Community & Contributions

Have ideas? Found a use case we should support? Open an issue or start a discussion — it'd be great to hear from you!
