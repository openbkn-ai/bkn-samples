# Standard object-query path

This sample publishes no custom function tools. External agents use the standard network-scoped MCP tools: `query_object_instance` for object instances and `run_cypher` for joins and aggregation across relations. Both run under the caller's own identity and the model's object permissions.

No runtime SQL endpoint, internal Vega query interface or platform-internal agent is part of the sample.
