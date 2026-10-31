# Install and query

1. Open **One-click onboarding** in Studio, refresh the official catalog and select **World Cup (EN)**. Check its version and release notes. If the catalog is unreachable, download its `package.tar.gz` from [Releases](https://github.com/openbkn-ai/bkn-samples/releases) and use **Import offline package**. The referenced data image must be reachable or preloaded in the target cluster.
2. Install and wait for database initialization, resource discovery, model import and verification to complete. This uses the standard managed installation flow.
3. Connect an external agent to the World Cup network through MCP. It reads the network description and the World Cup history analysis Skill, then queries with Cypher.
4. Use stable IDs for joins, convert numeric text values before comparisons, and aggregate facts at the requested grain.
5. Evaluate using the source-controlled question set without exposing reference queries or answers to the agent.

The sample uses database and network identity `worldcup_en`. Managed ownership governs cleanup. An existing unowned network with the same ID blocks installation and must be resolved before retrying.

The sample registers one business Skill and no SQL tool, custom functions or metrics. It does not invoke a platform-internal agent. MCP requests use the caller’s authenticated connection; business questions do not contain account IDs, tokens or session credentials.

For local developers, `env.sample` documents configuration. Managed installation supplies resource bindings through standard hook input and calls `run.sh` internally. Users do not run preparation scripts.

Uninstall through Studio before replacing an installed version. Removing a cached offline package does not uninstall its resources. Refreshing the online list discovers only releases registered in the official catalog.
