# Import and query

1. Import the reviewed `.tar.gz` package in Studio. Check its version and release notes.
2. Install and wait for database initialization, resource discovery, model import and verification to complete. This uses the standard managed installation flow.
3. Connect an independent external agent to the World Cup network through MCP. Inspect `get_kn_detail` and `get_object_types`, then use `query_object_instance` to read the required facts.
4. Query every required page. Use stable IDs for joins, convert numeric text values before comparisons, and aggregate facts at the requested grain. The agent may compute using ordinary Python or the standard sandbox capability.
5. Evaluate using the source-controlled question set without exposing reference queries or answers to the agent.

The sample uses database and network identity `worldcup_en`. Managed ownership governs cleanup. An existing unowned network with the same ID blocks installation and must be resolved before retrying.

The sample registers no SQL tool, custom functions, metrics or business Skills. It does not invoke a platform-internal agent. MCP requests use the caller’s authenticated connection; business questions do not contain account IDs, tokens or session credentials.

For local developers, `env.sample` documents configuration and `./run.sh --help` lists standalone preparation steps. Managed installation supplies resource bindings through standard hook input; platform hooks do not call kubectl.

Uninstall through Studio before replacing an installed version. Removing a cached offline package does not uninstall its resources. Refreshing the online list discovers only releases registered in the official catalog.
